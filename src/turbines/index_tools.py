import os
from turbines.config_loader import AppConfig

from abc import ABC, abstractmethod


class PluginBase:
    def __init__(self, config: AppConfig) -> None:
        self.config: AppConfig = config

    def before_build(self):
        pass

    def after_build(self):
        pass

    def after_page_render(
        self, page_path: str, query_path, metadata: dict, content: str
    ) -> str:

        return content

    def before_page_render(self, page_path: str, content: str) -> str:
        return content


class SitemapGenerator(PluginBase):

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)
        self._urls = []

    def set_config(self, config):
        self.config = config

    def after_page_render(
        self, page_path: str, query_path: str, metadata: dict, content: str
    ) -> str:

        if metadata.get("noindex", False):
            return content

        site_url = self.config.site.url.rstrip("/")

        page_url = f"{site_url}/{query_path.lstrip('/')}"
        if not self.config.site.sitemap.use_index:
            page_url = page_url.replace("/index.html", "/")
        self._urls.append(page_url)
        return content

    def after_build(self):
        if not self.config.site.sitemap.enable:
            return

        sitemap_path = os.path.join(
            os.getcwd(), self.config.site.output_dir, "sitemap.xml"
        )
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            )
            for url in self._urls:
                f.write(f"<url><loc>{url}</loc></url>\n")
            f.write("</urlset>\n")
        print(f"Sitemap generated at {sitemap_path}")

        # Generate Robots.txt with the content specified and the sitemap
        if self.config.site.robots_txt.enable:
            robots_path = os.path.join(
                os.getcwd(), self.config.site.output_dir, "robots.txt"
            )
            with open(robots_path, "w", encoding="utf-8") as f:
                if self.config.site.robots_txt.content:
                    f.write(self.config.site.robots_txt.content + "\n")
                f.write(f"Sitemap: {self.config.site.url}/sitemap.xml\n")
            print(f"Robots.txt generated at {robots_path}")
