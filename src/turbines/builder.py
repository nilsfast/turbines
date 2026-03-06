import os
import shutil
import logging
from datetime import datetime
import time
from typing import Type
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2_simple_tags import StandaloneTag
from pydantic.dataclasses import dataclass

from turbines.config_loader import AppConfig, ConfigLoader
from turbines.index_tools import SitemapGenerator
from turbines.reader import BaseReader, HTMLReader, MarkdownReader

log = logging.getLogger(__name__)


class NowExtension(StandaloneTag):
    tags = {"now"}

    def render(self, format="%Y-%m-%d %H:%I:%S"):
        return datetime.now().strftime(format)


class StaticFileExtension(StandaloneTag):
    tags = {"static"}

    def render(self, filename):
        return f"/static/{filename}"


class URLExtension(StandaloneTag):
    tags = {"url"}

    def render(self, path):
        return self.environment.globals["_turbines_url_map"][path]


@dataclass
class Page:
    file_path: str
    rel_file_path: str
    metadata: dict
    content: str
    output_path: str
    url: str


def initialize_project(path):
    # make a diretory in the specified path if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        log.info(f"Directory already exists at {path}")

    # copy ./scaffold to the specified path
    scaffold_src = os.path.join(os.path.dirname(__file__), "scaffold")
    scaffold_dst = os.path.join(path)

    # copy the data from scaffold_src to scaffold_dst

    shutil.copytree(scaffold_src, scaffold_dst, dirs_exist_ok=True)
    log.info(f"Initialized site at {path}")


READERS: dict[str, Type[BaseReader]] = {
    ".html": HTMLReader,
    ".htm": HTMLReader,
    ".md": MarkdownReader,
}


class Builder:
    def __init__(
        self, base_dir: str = os.getcwd(), force_files_overwrite: bool = False
    ):
        self.base_dir: str = base_dir
        self.static_files: dict[str, str] = {}
        self.tag_lists: dict[str, list] = {}
        # pages is a list of tuples of (file_path, metadata, content)
        self.pages: list[Page] | None = None
        # Load config first
        self.config: AppConfig = self.load_config()
        # build path is the output directory for the generated site, default is <base_dir>/dist
        self.build_path = os.path.join(self.base_dir, self.config.site.output_dir)

        # Check if build directory exists and is not empty
        if os.path.isdir(self.build_path) and force_files_overwrite:
            # log.info(
            #     f"Force overwrite enabled. Clearing existing files in build directory {self.build_path}"
            # )
            shutil.rmtree(self.build_path)

        # If not forcing overwrite, check if the build directory exists and is not empty, and raise an error if so
        if os.path.isdir(self.build_path) and not force_files_overwrite:
            raise RuntimeError(f"Build directory '{self.build_path}' is not empty.")

        # at this point the directory either doesn't exist or is empty, so we can safely create it
        os.makedirs(self.build_path, exist_ok=True)

        # static path is the directory for static files, default is <base_dir>/static
        self.static_path = os.path.join(self.base_dir, self.config.site.static_dir)
        # pages path is the directory for page source files, default is <base_dir>/pages
        self.pages_path = os.path.join(self.base_dir, self.config.site.pages_dir)
        # templates path is the directory for jinja2 templates, default is <base_dir>/templates
        self.templates_path = os.path.join(
            self.base_dir, self.config.site.templates_dir
        )
        # global context variables available in all templates via {{context.<var>}}
        self.global_context = self.config.context or {}

        # load plugins
        self.load_plugins()

    def load(self):
        self.load_static(self.static_path)
        self.load_templates(self.templates_path)
        self.load_pages(self.pages_path)

    def load_plugins(self):
        # TODO temporary sitemap plugin setup
        sitemap_plugin = SitemapGenerator(self.config)
        self.plugins = [sitemap_plugin]
        plugin_names = [plugin.name for plugin in self.plugins]
        log.info(f"Loaded plugins: {', '.join(plugin_names)}")

    def load_config(self):
        self.config_path = os.path.join(self.base_dir, "config.yaml")
        try:
            config = ConfigLoader.load(self.config_path)
        except RuntimeError as e:
            log.error(f"Error loading config: {e}")
            exit(1)
        return config

    def load_pages(self, pages_path):
        self.pages = []
        self.tag_lists = {}
        for root, _, files in os.walk(pages_path):
            # Get the relative path from the pages directory to preserve directory structure in output
            rel_root = os.path.relpath(root, self.pages_path)

            for filename in files:
                file_path = os.path.join(root, filename)
                name_without_ext = os.path.splitext(filename)[0]

                try:
                    reader = self._get_reader(filename)
                except ValueError as e:
                    log.warning(f"Skipping {filename}: {e}")
                    continue

                metadata, content = reader.read(file_path)

                # Preserve directory structure in output
                output_directory = os.path.join(self.build_path, rel_root)
                os.makedirs(output_directory, exist_ok=True)
                output_path = os.path.join(output_directory, name_without_ext + ".html")

                # Remove the build directory from output_path to get the query_path
                query_path = os.path.relpath(output_path, self.build_path)
                url = "/" + query_path.replace(os.sep, "/")
                metadata["url"] = url
                rel_file_path = os.path.relpath(file_path, self.pages_path).replace(
                    os.sep, "/"
                )

                page = Page(
                    file_path=file_path,
                    rel_file_path=rel_file_path,
                    metadata=metadata,
                    content=content,
                    output_path=output_path,
                    url=url,
                )

                self.pages.append(page)

        log.info(f"Loaded {len(self.pages)} pages")

        # Build lists of pages for the tag list feature
        # For each page, look for a "tags" field in the metadata.
        # If it exists, add the page metadata to the corresponding tag list in self.tag_lists
        for page in self.pages:
            tags = page.metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags:
                self.tag_lists.setdefault(tag, []).append(page.metadata)

    def load_static(self, static_path):
        # Copy static files to <build_path>/static
        output_static_path = os.path.join(self.build_path, "static")
        if os.path.isdir(static_path):
            shutil.copytree(static_path, output_static_path, dirs_exist_ok=True)
        log.debug(f"Copied static files from {static_path} to {output_static_path}")

    def load_templates(self, templates_path):
        pass

    def _get_reader(self, filename) -> BaseReader:
        file_ext = os.path.splitext(filename)[-1].lower()
        ReaderClass = READERS.get(file_ext)

        if not ReaderClass:
            raise ValueError(f"No reader found for file type: {file_ext}")

        reader = ReaderClass()
        return reader

    def render_pages(self):
        """
        Renders all site pages using Jinja2 templates, applies plugins, and writes the output files.
        XXX `load_pages` must be called before this to populate `self.pages`
        """

        start = time.time()

        if self.pages is None:
            raise RuntimeError("Pages not loaded. Call load() before build_site().")

        if self.config is None:
            raise RuntimeError("Config not loaded. Call load() before build_site().")

        # Run plugin before build hook
        for plugin in self.plugins:
            plugin.before_build()

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader([self.pages_path, self.templates_path]),
            autoescape=select_autoescape(["html", "xml"]),
        )

        env.globals["context"] = self.global_context
        env.globals["site"] = {
            "title": self.config.site.title,
            "url": self.config.site.url,
        }

        env.globals["_turbines_url_map"] = {
            page.rel_file_path: page.url for page in self.pages
        }

        env.globals["pages"] = {
            "tags": self.tag_lists,
            "all": [page.metadata for page in self.pages],
        }

        # add the now tag
        env.add_extension(NowExtension)
        env.add_extension(StaticFileExtension)
        env.add_extension(URLExtension)

        for page in self.pages:
            # create the rendered output using jinja from the content
            template = env.from_string(page.content)
            rendered = template.render(**page.metadata)

            for plugin in self.plugins:
                rendered = plugin.after_page_render(
                    page.file_path, page.url, page.metadata, rendered
                )

            with open(page.output_path, "w", encoding="utf-8") as out_f:
                out_f.write(rendered)

            log.debug(f"Rendered {page.file_path} to {page.output_path}")

        # Run plugin after build hook
        for plugin in self.plugins:
            plugin.after_build(self.build_path)

        end = time.time()
        log.info(f"Build completed in {end - start:.2f} seconds")
