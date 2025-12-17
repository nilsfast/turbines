import yaml
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ValidationError


class SiteConfig(BaseModel):
    url: str
    title: str | None = None
    output_dir: str = "dist"
    pages_dir: str = "pages"
    static_dir: str = "static"
    templates_dir: str = "templates"


class AppConfig(BaseModel):
    site: SiteConfig
    context: dict[str, Any] = {}


class ConfigLoader:
    @staticmethod
    def load(path: str | Path) -> AppConfig:
        with open(path, "r") as f:
            data: dict[str, Any] = yaml.safe_load(f)
            print(f"Loaded configuration from {path}")
            print(data)

        if data is None:
            data = {}

        try:
            return AppConfig(**data)
        except ValidationError as e:
            raise RuntimeError(f"Invalid configuration: {e}")
