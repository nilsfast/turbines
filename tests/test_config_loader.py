import pytest
import yaml

from turbines.config_loader import (
    ConfigLoader,
    AppConfig,
)


VALID_CONFIG = """
site:
  url: http://example.com
  title: Example Site
"""


class TestConfigLoader:
    def test_load_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(VALID_CONFIG)

        config = ConfigLoader.load(config_file)
        assert config.site.url == "http://example.com"
        assert config.site.title == "Example Site"

    def test_load_file_not_found(self):
        with pytest.raises(RuntimeError, match="Configuration file not found"):
            ConfigLoader.load("/nonexistent/config.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: : yaml")

        with pytest.raises(RuntimeError, match="Error parsing configuration"):
            ConfigLoader.load(config_file)

    def test_load_invalid_config_data(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_data = {"site": {"url": 123}}  # url should be string
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(RuntimeError, match="Invalid configuration"):
            ConfigLoader.load(config_file)

    def test_load_empty_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config = ConfigLoader.load(config_file)
        assert isinstance(config, AppConfig)
        assert config == AppConfig()  # should be default config
