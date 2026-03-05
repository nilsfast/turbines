from abc import ABC, abstractmethod
import markdown
import yaml


class BaseReader(ABC):
    @abstractmethod
    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            return {}, f.read()


class HTMLReader(BaseReader):
    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            metadata: dict = {}
            first_line = f.readline()
            if first_line.strip() == "---":
                front_matter_lines = []
                for line in f:
                    if line.strip() == "---":
                        break
                    front_matter_lines.append(line)
                front_matter = "".join(front_matter_lines)
                metadata = yaml.safe_load(front_matter) or {}
            else:
                f.seek(0)
            content = f.read()
            return metadata, content


class MarkdownReader(BaseReader):
    def read(self, filepath) -> tuple[dict, str]:
        with open(filepath, "r", encoding="utf-8") as f:
            md_content = f.read()
        md = markdown.Markdown(extensions=["meta", "extra", "toc"])
        html_content = md.convert(md_content)

        metadata = {}
        for key, value in getattr(md, "Meta", {}).items():
            if isinstance(value, list) and len(value) == 1:
                metadata[key] = value[0]
            else:
                metadata[key] = value

        if "template" in metadata:
            template_name = metadata["template"]
            html_content = (
                f"{{% extends '{template_name}' %}}\n"
                "{% block content %}\n"
                f"{html_content}\n"
                "{% endblock %}"
            )

        return metadata, html_content
