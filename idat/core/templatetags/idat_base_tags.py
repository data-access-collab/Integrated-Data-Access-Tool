import re
from typing import Any

from django import template
from django.template.loader import get_template
from django.utils.safestring import SafeString, mark_safe

register = template.Library()

_SVG_CONTENT = re.compile(r"<svg\b[^>]*>(?P<content>.*)</svg>", re.DOTALL)
_XML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@register.simple_tag
def define(value: Any) -> Any:  # noqa: ANN401
    """Store a value in a variable for later use

    Example:
        {% define 'some-value' as my_var %}
        <p>This is {{ my_var }}</p>
    """
    return value


@register.simple_tag
def icon_content(name: str) -> SafeString:
    """Return the shapes inside idat/templates/icons/<name>.svg, without the <svg> root

    The files are complete SVG documents (previewable, valid XML). <c-icon> renders
    its own <svg> root (size, stroke, aria attributes) and puts these shapes in it.
    Comments are dropped. An unknown name raises TemplateDoesNotExist.

    Example:
        <svg viewBox="0 0 24 24" …>{% icon_content "check" %}</svg>
    """
    source = get_template(f"icons/{name}.svg").template.source
    match = _SVG_CONTENT.search(source)
    if match is None:
        msg = f"icons/{name}.svg has no <svg> root element"
        raise ValueError(msg)
    return mark_safe(_XML_COMMENT.sub("", match["content"]).strip())  # noqa: S308 (trusted project file)
