# core/templatetags/secure_url.py

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def secure_url(obj, field_name):
    """
    Gera URL segura de download para qualquer FileField/ImageField.
    
    Uso no template:
        {% load secure_url %}
        {% secure_url funcionario 'foto_3x4' as foto_url %}
        <img src="{{ foto_url }}">
        
        {% secure_url doc 'anexo' as doc_url %}
        <a href="{{ doc_url }}">Download</a>
    """
    if not obj or not hasattr(obj, field_name):
        return ''

    file_field = getattr(obj, field_name, None)
    if not file_field:
        return ''

    app_label = obj._meta.app_label
    model_name = obj._meta.model_name
    pk = obj.pk

    return reverse('core:secure_download', kwargs={
        'app': app_label,
        'model': model_name,
        'pk': pk,
        'field': field_name,
    })
