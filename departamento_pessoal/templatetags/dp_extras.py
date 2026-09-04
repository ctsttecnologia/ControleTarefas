
# departamento_pessoal/templatetags/dp_extras.py
from django import template

register = template.Library()

@register.filter
def pode_ver_salario(user):
    return user.is_superuser or user.has_perm('departamento_pessoal.view_salario')

