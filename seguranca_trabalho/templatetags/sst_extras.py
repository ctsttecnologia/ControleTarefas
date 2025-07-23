
from django.template import Library

register = Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite aceder a um valor de dicionário usando uma variável como chave no template.
    Uso: {{ meu_dicionario|get_item:minha_variavel_chave }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

