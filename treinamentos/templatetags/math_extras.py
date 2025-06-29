# treinamentos/templatetags/math_extras.py

from django import template

register = template.Library()

@register.filter(name='absolute')
def absolute(value):
    """Retorna o valor absoluto de um número."""
    try:
        # Tenta converter o valor para um inteiro e retorna o valor absoluto
        return abs(int(value))
    except (ValueError, TypeError):
        # Se a conversão falhar, retorna o valor original sem alterá-lo
        return value