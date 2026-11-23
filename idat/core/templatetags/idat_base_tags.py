import logging
from typing import Any

from django import template

from idat.core.icons import get_icon, icons

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def define(value: Any) -> Any:  # noqa: ANN401
    """Store a value in a variable for later use

    Example:
        {% define 'some-value' as my_var %}
        <p>This is {{ my_var }}</p>
    """
    return value


# {% get_icon name as icon %}: icon.body (shapes), icon.filled. Used by <c-icon>.
register.simple_tag(get_icon)


@register.filter
def has_icon(name: str) -> bool:
    """Whether icon <name> is in the allowlist. For icon names that come from data
    (e.g. Vlopse.logo), which can outlive their icon: check before <c-icon>, which
    raises on unknown names, and fall back. A missing icon is logged as a warning.

    Example:
        {% if vlopse.logo|has_icon %}
          <c-icon :name="vlopse.logo" />
        {% else %}…{% endif %}
    """
    if not name:
        return False
    if name not in icons():
        logger.warning("Icon %r is not in idat/assets/icons/allowlist.json", name)
        return False
    return True
