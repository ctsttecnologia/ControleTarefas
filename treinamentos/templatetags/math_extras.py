
from django import template

register = template.Library()

@register.filter
def absolute(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value  # ou return 0 se preferir
