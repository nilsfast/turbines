import yaml
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ValidationError


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
                print(f"Loaded configuration from {path}")
                print(data)
        except FileNotFoundError:
            print(f"Configuration file {path} not found. Using default configuration.")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error parsing configuration file: {e}")

        try:
            return AppConfig(**data)
        except ValidationError as e:
            raise RuntimeError(f"Invalid configuration: {e}")
