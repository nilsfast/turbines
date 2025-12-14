from abc import ABC, abstractmethod
import os
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape

from datetime import datetime
from jinja2_simple_tags import StandaloneTag


class NowExtension(StandaloneTag):
    tags = {"now"}

    def render(self, format="%Y-%m-%d %H:%I:%S"):
        return datetime.now().strftime(format)


class StaticFileExtension(StandaloneTag):
    tags = {"static"}

    def render(self, filename):
        return f"/static/{filename}"


class BaseReader(ABC):

    @abstractmethod
    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            return {}, f.read()


class HTMLReader(BaseReader):

    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            return {}, f.read()


class MarkdownReader(BaseReader):
    def read(self, filepath) -> tuple[dict, str]:
        import markdown

        with open(filepath, "r", encoding="utf-8") as f:
            md_content = f.read()
        md = markdown.Markdown(extensions=["meta"])
        html_content = md.convert(md_content)

        metadata = {}
        for key, value in getattr(md, "Meta", {}).items():
            if isinstance(value, list) and len(value) == 1:
                metadata[key] = value[0]
            else:
                metadata[key] = value

        # Use Jinja2 template inheritance if 'template' is specified in metadata
        if "template" in metadata:
            template_name = metadata["template"]
            # Use Jinja2 block for content and extends for template
            html_content = (
                f"{{% extends '{template_name}' %}}\n"
                "{% block content %}\n"
                f"{html_content}\n"
                "{% endblock %}"
            )

        return metadata, html_content


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


def build_site():
    print("Building site... (placeholder implementation)")
    print("Current directory:", os.getcwd())
    config_path = os.path.join(os.getcwd(), "config.yaml")
    if os.path.isfile(config_path):
        print("Found config.yml")
    else:
        print("config.yml not found")

    pages_path = os.path.join(os.getcwd(), "pages")
    if os.path.isdir(pages_path):
        print("Found pages directory")
    else:
        print("pages directory not found")

    # load static files from ./static
    static_path = os.path.join(os.getcwd(), "static")
    if os.path.isdir(static_path):
        print("Found static directory")
    else:
        print("static directory not found")

    # load templates from ./templates
    templates_path = os.path.join(os.getcwd(), "templates")
    if os.path.isdir(templates_path):
        print("Found templates directory")
    else:
        print("templates directory not found")

    # output to ./site
    site_path = os.path.join(os.getcwd(), ".site")

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader([pages_path, templates_path]),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Copy static files to .site/static
    site_static_path = os.path.join(site_path, "static")
    if os.path.isdir(static_path):
        shutil.copytree(static_path, site_static_path, dirs_exist_ok=True)

    # add the now tag
    env.add_extension(NowExtension)
    env.add_extension(StaticFileExtension)

    READERS = {
        ".html": HTMLReader,
        ".htm": HTMLReader,
        ".md": MarkdownReader,
    }

    # Render each page in ./pages
    if not os.path.isdir(pages_path):
        print("No pages to render.")
        return

    for root, _, files in os.walk(pages_path):
        rel_root = os.path.relpath(root, pages_path)

        for filename in files:
            file_ext = os.path.splitext(filename)[1]
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
            output_dir = os.path.join(site_path, rel_root)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, name_without_ext + ".html")

            with open(output_path, "w", encoding="utf-8") as out_f:
                out_f.write(rendered)
            print(f"Rendered {os.path.relpath(file_path, pages_path)}")
