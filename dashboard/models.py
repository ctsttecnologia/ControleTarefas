# dashboard/models.py
from django.db import models


class DashboardPermission(models.Model):
    """
    Model placeholder SEM TABELA no banco.
    Serve APENAS como container das permissões customizadas do app dashboard.

    As permissões declaradas aqui são criadas automaticamente pelo Django
    via comando `migrate` (através do post_migrate signal).
    """

    class Meta:
        managed = False          # ❌ Não cria tabela no banco
        default_permissions = () # ❌ Remove add/change/delete/view padrão
        permissions = [
            ('view_dashboard_geral',        'Pode visualizar o Dashboard Geral'),
            ('view_dashboard_treinamentos', 'Pode visualizar o Dashboard de Treinamentos'),
            ('view_dashboard_tarefas',      'Pode visualizar o Dashboard de Tarefas'),
            ('view_dashboard_epi',          'Pode visualizar o Dashboard de EPI'),
            ('view_dashboard_documentos',   'Pode visualizar o Dashboard de Documentos'),
            ('view_dashboard_pgr',          'Pode visualizar o Dashboard de PGR'),
        ]
        verbose_name = 'Permissão do Dashboard'
        verbose_name_plural = 'Permissões do Dashboard'



