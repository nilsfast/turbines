import os
import shutil
from typing import Type
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml

from datetime import datetime
from jinja2_simple_tags import StandaloneTag
import hashlib

from turbines.config_loader import AppConfig, ConfigLoader
from turbines.reader import BaseReader, HTMLReader, MarkdownReader


class NowExtension(StandaloneTag):
    tags = {"now"}

    def render(self, format="%Y-%m-%d %H:%I:%S"):
        return datetime.now().strftime(format)


class StaticFileExtension(StandaloneTag):
    tags = {"static"}

    def render(self, filename):
        return f"/static/{filename}"


def scaffold(path):
    # make a diretory in the specified path if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory at {path}")
    else:
        print(f"Directory already exists at {path}")

    # copy ./scaffold to the specified path
    scaffold_src = os.path.join(os.path.dirname(__file__), "scaffold")
    scaffold_dst = os.path.join(path)

    # copy the data from scaffold_src to scaffold_dst

    shutil.copytree(scaffold_src, scaffold_dst, dirs_exist_ok=True)
    print(f"Copied scaffold to {path}")


class Builder:

    def __init__(self, inject_reload_script: bool = False):
        self.config: AppConfig | None = None
        self.static_files: dict[str, str] = {}
        self.inject_reload_script = inject_reload_script

    def load(self):
        self.config = self.load_config()

        self.build_path = os.path.join(os.getcwd(), self.config.site.output_dir)
        os.makedirs(self.build_path, exist_ok=True)

        self.load_static(self.config.site.static_dir)
        self.load_templates(self.config.site.templates_dir)
        self.load_pages(self.config.site.pages_dir)

        self.pages_path = os.path.join(os.getcwd(), self.config.site.pages_dir)
        self.templates_path = os.path.join(os.getcwd(), self.config.site.templates_dir)

        self.global_context = self.config.context or {}

    def load_config(self):
        config_path = os.path.join(os.getcwd(), "config.yaml")

        if os.path.isfile(config_path):
            print("Found config.yml")
        else:
            print("config.yml not found")

        try:
            config = ConfigLoader.load(config_path)
        except Exception as e:
            print(f"Error loading config: {e}")
            raise e

        return config

    def load_pages(self, pages_path):

        for root, _, files in os.walk(pages_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                # For now, just print the page paths
                print(f"Found page: {os.path.relpath(file_path, pages_path)}")

    def load_static(self, static_path):
        # Copy static files to <build_path>/static
        output_static_path = os.path.join(self.build_path, "static")
        if os.path.isdir(static_path):
            shutil.copytree(static_path, output_static_path, dirs_exist_ok=True)

    def load_templates(self, templates_path):
        pass

    def reload(self):
        print("Reloading configuration and rebuilding site...")
        self.build_site()

    def build_site(self):

        if self.config is None:
            raise RuntimeError("Config not loaded. Call load() before build_site().")

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader([self.pages_path, self.templates_path]),
            autoescape=select_autoescape(["html", "xml"]),
        )

        env.globals["context"] = self.global_context
        env.globals["site_title"] = self.config.site.title

        # add the now tag
        env.add_extension(NowExtension)
        env.add_extension(StaticFileExtension)

        READERS: dict[str, Type[BaseReader]] = {
            ".html": HTMLReader,
            ".htm": HTMLReader,
            ".md": MarkdownReader,
        }

        # Render each page in ./pages
        if not os.path.isdir(self.pages_path):
            print("No pages to render.")
            return

        for root, _, files in os.walk(self.pages_path):
            rel_root = os.path.relpath(root, self.pages_path)

            for filename in files:
                file_ext = os.path.splitext(filename)[-1].lower()
                reader_class = READERS.get(file_ext)

                if not reader_class:
                    print(f"Skipping unsupported file type: {filename}")
                    continue

                reader = reader_class()
                file_path = os.path.join(root, filename)
                metadata, content = reader.read(file_path)

                # create the rendered output using jinja from the content
                template = env.from_string(content)
                rendered = template.render(**metadata)

                name_without_ext = os.path.splitext(filename)[0]
                # Preserve directory structure in output
                output_dir = os.path.join(self.build_path, rel_root)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, name_without_ext + ".html")

                with open(output_path, "w", encoding="utf-8") as out_f:
                    out_f.write(rendered)
                print(f"Rendered {os.path.relpath(file_path, self.pages_path)}")
