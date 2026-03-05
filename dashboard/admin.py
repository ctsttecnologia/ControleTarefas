
# dashboard/admin.py

"""
Admin Dashboard — refatorado para usar services.py.
Usa filial=None para métricas globais (admin vê tudo).
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render

from .services import (
    get_metricas_geral,
    get_metricas_treinamentos,
    get_metricas_tarefas,
    get_metricas_epi,
    get_metricas_documentos,
)


class DashboardAdminSite(admin.AdminSite):
    site_header = "Sistema de Gestão Integrada - Dashboard"
    site_title = "Dashboard"
    index_title = "Painel de Controle Principal"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.dashboard_geral), name='index'),
            path('dashboard-geral/', self.admin_view(self.dashboard_geral), name='dashboard_geral'),
            path('dashboard-treinamentos/', self.admin_view(self.dashboard_treinamentos), name='dashboard_treinamentos'),
            path('dashboard-tarefas/', self.admin_view(self.dashboard_tarefas), name='dashboard_tarefas'),
            path('dashboard-epi/', self.admin_view(self.dashboard_epi), name='dashboard_epi'),
            path('dashboard-documentos/', self.admin_view(self.dashboard_documentos), name='dashboard_documentos'),
        ]
        return custom_urls + urls

    def dashboard_geral(self, request):
        """Dashboard consolidado — admin vê TODAS as filiais."""
        context = {
            **self.each_context(request),
            'title': 'Dashboard Geral — Visão Consolidada',
            **get_metricas_geral(filial=None),
        }
        return render(request, 'admin/dashboard_geral.html', context)

    def dashboard_treinamentos(self, request):
        """Dashboard de Treinamentos — admin global."""
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Treinamentos',
            **get_metricas_treinamentos(filial=None, dias_alerta=15),
        }
        return render(request, 'admin/dashboard_treinamentos.html', context)

    def dashboard_tarefas(self, request):
        """Dashboard de Tarefas — admin global."""
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Tarefas',
            **get_metricas_tarefas(filial=None),
        }
        return render(request, 'admin/dashboard_tarefas.html', context)

    def dashboard_epi(self, request):
        """Dashboard de EPI — admin global."""
        context = {
            **self.each_context(request),
            'title': 'Dashboard de EPI',
            **get_metricas_epi(filial=None),
        }
        return render(request, 'admin/dashboard_epi.html', context)

    def dashboard_documentos(self, request):
        """Dashboard de Documentos — admin global."""
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Documentos',
            **get_metricas_documentos(filial=None, dias_alerta=30),
        }
        return render(request, 'admin/dashboard_documentos.html', context)


# ✅ Instância do dashboard
dashboard_site = DashboardAdminSite(name='dashboard_admin')

