
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica se um usuário pertence a um grupo.
    Permite passar múltiplos nomes de grupo separados por vírgula.
    Exemplo de uso no template: {% if request.user|has_group:"Administrador,Gerente" %}
    """
    if user.is_authenticated:
        # Divide a string de nomes de grupo em uma lista
        group_names = [name.strip() for name in group_name.split(',')]
        # Verifica se o usuário pertence a QUALQUER um dos grupos na lista
        return Group.objects.filter(user=user, name__in=group_names).exists()
    return False
