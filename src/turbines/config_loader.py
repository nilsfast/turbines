from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, ValidationError


class SiteConfig(BaseModel):
    url: str
    title: str | None = None
    output_dir: str = "dist"
    pages_dir: str = "pages"
    static_dir: str = "static"
    templates_dir: str = "templates"


class UrlsConfig(BaseModel):
    prettify: bool = False


class AssetsConfig(BaseModel):
    optimize_extensions: list[str] = []
    fingerprint_extensions: list[str] = []


class BlogConfig(BaseModel):
    content_path: str
    default_author: str
    date_format: str
    posts_per_page: int


class AppConfig(BaseModel):
    site: SiteConfig
    urls: UrlsConfig | None = None
    assets: AssetsConfig | None = None
    blog: BlogConfig | None = None
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
