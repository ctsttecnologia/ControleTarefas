
STATUS_COLORS = {
    'pendente':  {'bg': 'rgba(245,158,11,0.12)', 'fg': '#d97706', 'solid': '#f59e0b'},
    'andamento': {'bg': 'rgba(59,130,246,0.12)',  'fg': '#2563eb', 'solid': '#3b82f6'},
    'concluida': {'bg': 'rgba(34,197,94,0.12)',   'fg': '#16a34a', 'solid': '#22c55e'},
    'atrasada':  {'bg': 'rgba(239,68,68,0.12)',   'fg': '#dc2626', 'solid': '#ef4444'},
    'pausada':   {'bg': 'rgba(139,92,246,0.12)',  'fg': '#7c3aed', 'solid': '#8b5cf6'},
    'cancelada': {'bg': 'rgba(100,116,139,0.12)', 'fg': '#475569', 'solid': '#64748b'},
}

PRIORITY_COLORS = {
    'alta':  {'bg': 'rgba(239,68,68,0.12)', 'fg': '#dc2626', 'solid': '#ef4444'},
    'media': {'bg': 'rgba(245,158,11,0.12)','fg': '#d97706', 'solid': '#f59e0b'},
    'baixa': {'bg': 'rgba(34,197,94,0.12)', 'fg': '#16a34a', 'solid': '#22c55e'},
}

DEFAULT_COLOR = {'bg': 'rgba(100,116,139,0.12)', 'fg': '#475569', 'solid': '#9ca3af'}


def status_colors(request):
    """Disponibiliza as cores de status/prioridade em todos os templates."""
    return {
        'STATUS_COLORS': STATUS_COLORS,
        'PRIORITY_COLORS': PRIORITY_COLORS,
        'DEFAULT_COLOR': DEFAULT_COLOR,
    }

