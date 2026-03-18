
# ltcat/templatetags/ltcat_tags.py

from django import template

register = template.Library()


@register.filter
def status_badge(status):
    """Retorna classe CSS do badge conforme status do LTCAT."""
    badges = {
        "RASCUNHO": "bg-secondary",
        "EM_ELABORACAO": "bg-info",
        "REVISAO": "bg-warning text-dark",
        "APROVADO": "bg-primary",
        "VIGENTE": "bg-success",
        "VENCIDO": "bg-danger",
        "CANCELADO": "bg-dark",
    }
    return badges.get(status, "bg-secondary")


@register.filter
def prioridade_badge(prioridade):
    badges = {
        "ALTA": "bg-danger",
        "MEDIA": "bg-warning text-dark",
        "BAIXA": "bg-info",
    }
    return badges.get(prioridade, "bg-secondary")


@register.filter
def tipo_risco_color(tipo):
    colors = {
        "FISICO": "#28a745",
        "QUIMICO": "#dc3545",
        "BIOLOGICO": "#6f42c1",
        "ERGONOMICO": "#fd7e14",
        "ACIDENTE": "#007bff",
    }
    return colors.get(tipo, "#6c757d")


@register.filter
def tipo_risco_icon(tipo):
    icons = {
        "FISICO": "bi-soundwave",
        "QUIMICO": "bi-droplet-half",
        "BIOLOGICO": "bi-bug",
        "ERGONOMICO": "bi-person-arms-up",
        "ACIDENTE": "bi-exclamation-triangle",
    }
    return icons.get(tipo, "bi-question-circle")

