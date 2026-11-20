from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.template import Context, Template
from django_cotton.compiler_regex import CottonCompiler

from idat.core.templatetags.idat_base_tags import has_icon, icon_content

ICONS_DIR = Path(settings.APPS_DIR) / "templates" / "icons"
# set on the shapes of every logo-*.svg (filled), never on Lucide icons (stroked)
LOGO_SHAPE = 'fill="currentColor" stroke="none"'


@pytest.mark.parametrize("name", sorted(p.stem for p in ICONS_DIR.glob("*.svg")))
def test_icon_renders(name: str):
    """Every icon file loads as a template and has shapes. Text such as "<c-icon>" in
    an icon's XML comment is parsed as a cotton tag and breaks every page using it."""
    assert icon_content(name)


def test_has_icon():
    assert has_icon("logo-tiktok")
    assert not has_icon("")


def test_has_icon_logs_missing_icon(caplog: pytest.LogCaptureFixture):
    assert not has_icon("logo-removed")
    assert "logo-removed" in caplog.text


def _render(source: str) -> str:
    return Template(CottonCompiler().process(source)).render(Context())


@pytest.mark.parametrize(
    "tag",
    [
        '<c-platform-chip name="TikTok" logo="logo-removed" />',
        '<c-platform-row name="TikTok" logo="logo-removed" input-name="v" value="1" />',
    ],
)
def test_platform_logo_falls_back_to_letter_when_icon_is_gone(tag: str):
    """A Vlopse.logo whose icon file was removed or renamed shows the letter tile
    instead of breaking the page."""
    html = _render(tag)
    assert ">T</span>" in html
    assert LOGO_SHAPE not in html


def test_platform_logo_renders_icon():
    html = _render('<c-platform-chip name="TikTok" logo="logo-tiktok" />')
    assert LOGO_SHAPE in html
    assert ">T</span>" not in html
