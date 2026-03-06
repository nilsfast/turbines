from abc import ABC, abstractmethod
from turbines.config_loader import AppConfig


class PluginBase(ABC):
    def __init__(self, config: AppConfig) -> None:
        self.config: AppConfig = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for the plugin, used for configuration and logging."""
        pass

    def before_build(self):
        pass

    @abstractmethod
    def after_build(self, output_dir: str):
        pass

    @abstractmethod
    def after_page_render(
        self, page_path: str, query_path, metadata: dict, content: str
    ) -> str:
        pass

    def before_page_render(self, page_path: str, content: str) -> str:
        return content
