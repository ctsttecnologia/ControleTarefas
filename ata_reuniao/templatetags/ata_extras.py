
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Acessa um dicionário com chave variável no template.
    Uso: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return []
    return dictionary.get(key, [])

# ... outros filters ...


