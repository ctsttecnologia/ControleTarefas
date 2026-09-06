
# tarefas/templatetags/tarefas_extras.py
from django import template
from tarefas.context_processors import STATUS_COLORS, PRIORITY_COLORS, DEFAULT_COLOR

register = template.Library()

@register.simple_tag
def status_color(status, field='fg'):
    return STATUS_COLORS.get(status, DEFAULT_COLOR).get(field, DEFAULT_COLOR[field])

@register.simple_tag
def priority_color(prioridade, field='fg'):
    return PRIORITY_COLORS.get(prioridade, DEFAULT_COLOR).get(field, DEFAULT_COLOR[field])

@register.simple_tag(takes_context=True)
def querystring_replace(context, **kwargs):
    request = context['request']
    query_dict = request.GET.copy()
    for key, value in kwargs.items():
        query_dict[key] = value
    return query_dict.urlencode()


