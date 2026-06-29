from django import template
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe

from common.text_utils import normalize_multiline_text

register = template.Library()


@register.filter
def display_text(value):
    return normalize_multiline_text(value)


@register.filter
def display_text_br(value):
    normalized = normalize_multiline_text(value)
    if not normalized:
        return ""
    return mark_safe(linebreaks(normalized))