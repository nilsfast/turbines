import logging

import yaml
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)  # noqa: F821


class RobotsTxtConfig(BaseModel):
    enable: bool = False
    content: str | None = None


class SitemapConfig(BaseModel):
    enable: bool = False
    use_index: bool = False


class SiteConfig(BaseModel):
    url: str = "http://localhost:8000"
    title: str | None = None
    output_dir: str = "dist"
    pages_dir: str = "pages"
    static_dir: str = "static"
    templates_dir: str = "templates"
    robots_txt: RobotsTxtConfig = RobotsTxtConfig()
    sitemap: SitemapConfig = SitemapConfig()
    extensionless_urls: bool = False


class AppConfig(BaseModel):
    site: SiteConfig = SiteConfig()
    context: dict[str, Any] = {}


class ConfigLoader:
    @staticmethod
    def load(path: str | Path) -> AppConfig:
        data: dict[str, Any] = {}
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                log.info("Loading config…")
        except FileNotFoundError:
            raise RuntimeError(f"Configuration file not found at {path}")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error parsing configuration file: {e}")

        try:
            return AppConfig(**data)
        except ValidationError as e:
            raise RuntimeError(f"Invalid configuration: {e}")
