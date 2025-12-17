import os
import shutil
from pathlib import Path

import pytest

from turbines.builder import Builder, scaffold


def copy_example_to(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    example_dir = repo_root / "example"
    assert example_dir.exists(), "example project directory is missing"
    dest = tmp_path / "site"
    shutil.copytree(example_dir, dest)
    return dest


def test_build_example_site(tmp_path: Path):
    site_dir = tmp_path

    cwd_before = Path.cwd()

    try:

        scaffold(site_dir)
        os.chdir(site_dir)

        builder = Builder()

        builder.load()
        builder.build_site()

        dist = site_dir / (builder.config.site.output_dir if builder.config else "dist")

        # core outputs exist
        assert (dist / "index.html").is_file(), "index.html was not generated"
        assert (
            dist / "test.html"
        ).is_file(), "Markdown page test.md not rendered to test.html"

        # static files copied
        assert (dist / "static").is_dir(), "static directory not copied"
        # example has these files (may be empty but should exist)
        assert (
            dist / "static" / "style.css"
        ).exists(), "style.css not found in output static"
        assert (
            dist / "static" / "script.js"
        ).exists(), "script.js not found in output static"

        # spot-check rendered content
        index_html = (dist / "index.html").read_text(encoding="utf-8")
        # inherited base template header present
        assert "Welcome to Turbines!" in index_html

        test_md_html = (dist / "test.html").read_text(encoding="utf-8")
        # template from metadata applied and title rendered
        assert "<h2>Example Markdown Page</h2>" in test_md_html

    finally:
        os.chdir(cwd_before)
