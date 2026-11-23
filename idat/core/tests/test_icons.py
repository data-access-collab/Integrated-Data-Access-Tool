from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template import Context, Template
from django_cotton.compiler_regex import CottonCompiler

from idat.core.icons import UnknownIconError, get_icon, icons
from idat.core.templatetags.idat_base_tags import has_icon
from idat.dsa40_wizard.sections import SECTION_META

TEMPLATES_DIR = Path(settings.APPS_DIR) / "templates"
# <c-icon>'s <svg> root for filled icons (logo-*), never for Lucide icons (stroked)
_FILLED_ROOT = re.compile(r'<svg\b[^>]*\sfill="currentColor"')

# Literal icon names in templates: <c-icon name="…">, icon props of other components,
# logos, and {% define "…" as …icon… %} defaults.
_TEMPLATE_ICON_NAMES = [
    re.compile(r'<c-icon\b[^>]*?\sname="([^"{]*)"'),
    re.compile(r'\s(?:icon|leading-icon|action-icon|logo)="([^"{]*)"'),
    re.compile(r'{% define "([^"]*)" as (?:default_icon|icon_name) %}'),
]


@pytest.mark.parametrize("name", sorted(icons()))
def test_icon_renders(name: str):
    """Logos are filled, everything else is a stroked Lucide icon."""
    html = _render(f'<c-icon name="{name}" />')
    assert get_icon(name).body in html
    assert bool(_FILLED_ROOT.search(html)) == name.startswith("logo-")


def test_unknown_icon_raises():
    with pytest.raises(UnknownIconError):
        get_icon("no-such-icon")


def test_icon_names_in_templates_are_allowlisted():
    used = {}
    for path in TEMPLATES_DIR.rglob("*.html"):
        source = path.read_text(encoding="utf-8")
        for pattern in _TEMPLATE_ICON_NAMES:
            for name in pattern.findall(source):
                if name:
                    used.setdefault(name, path.relative_to(TEMPLATES_DIR))
    unknown = {name: str(path) for name, path in used.items() if name not in icons()}
    assert not unknown, "not in idat/assets/icons/allowlist.json"
    assert used  # the patterns still match something


def test_section_icons_are_allowlisted():
    assert {meta.icon for meta in SECTION_META.values()} <= icons().keys()


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
    """A Vlopse.logo whose icon was removed from the allowlist shows the letter tile
    instead of breaking the page."""
    html = _render(tag)
    assert ">T</span>" in html
    assert not _FILLED_ROOT.search(html)


def test_platform_logo_renders_icon():
    html = _render('<c-platform-chip name="TikTok" logo="logo-tiktok" />')
    assert _FILLED_ROOT.search(html)
    assert ">T</span>" not in html
