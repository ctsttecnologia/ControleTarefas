
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Retorna o valor de uma chave de dicionário.
    Uso: {{ dicionario|get_item:chave }}
    """
    return dictionary.get(key)
