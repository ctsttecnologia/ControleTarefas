
from django.template import Library
from django import template
from django.forms import Select, SelectMultiple, CheckboxInput

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite aceder a um valor de dicionário usando uma variável como chave no template.
    Uso: {{ meu_dicionario|get_item:minha_variavel_chave }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.simple_tag
def is_select_field(field):
    return isinstance(field.field.widget, (Select, SelectMultiple))

@register.simple_tag
def is_checkbox_field(field):
    return isinstance(field.field.widget, CheckboxInput)
