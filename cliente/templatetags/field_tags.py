
"""
Template filters para identificar o tipo de widget de um campo de formulário.

Uso no template:
    {% load field_tags %}
    {% if field|is_checkbox %}...{% endif %}
    {% if field|is_select %}...{% endif %}
    {% if field|is_textarea %}...{% endif %}
"""

from django import template

register = template.Library()


@register.filter(name="is_checkbox")
def is_checkbox(field):
    """Retorna True se o widget for CheckboxInput."""
    return getattr(field.field.widget, "input_type", None) == "checkbox"


@register.filter(name="is_select")
def is_select(field):
    """Retorna True se o widget for Select ou SelectMultiple."""
    widget_class = field.field.widget.__class__.__name__
    return widget_class in ("Select", "SelectMultiple", "RadioSelect")


@register.filter(name="is_textarea")
def is_textarea(field):
    """Retorna True se o widget for Textarea."""
    return field.field.widget.__class__.__name__ == "Textarea"
