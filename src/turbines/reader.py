from abc import ABC, abstractmethod

import yaml


class BaseReader(ABC):
    @abstractmethod
    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            return {}, f.read()


class HTMLReader(BaseReader):

    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            metadata = {}
            # if the start of the file is a yaml front matter, parse it
            first_line = f.readline()
            if first_line.strip() == "---":
                # read until the next ---
                front_matter_lines = []
                for line in f:
                    if line.strip() == "---":
                        break
                    front_matter_lines.append(line)
                front_matter = "".join(front_matter_lines)
                metadata = yaml.safe_load(front_matter) or {}
            else:
                f.seek(0)  # reset to start if no front matter
            content = f.read()
            return metadata, content


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
