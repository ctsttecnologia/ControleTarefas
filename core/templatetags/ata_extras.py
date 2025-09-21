
# ata_reuniao/templatetags/ata_extras.py
from django import template

register = template.Library()

@register.simple_tag
def status_badge(status_text):
    """ Retorna a classe CSS do Bootstrap para um badge de status. """
    classes = {
        'Concluído': 'text-bg-success',
        'Andamento': 'text-bg-primary',
        'Pendente': 'text-bg-warning',
        'Cancelado': 'text-bg-danger',
    }
    return classes.get(status_text, 'text-bg-secondary')
