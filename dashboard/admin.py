
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
import datetime

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
        """Dashboard consolidado de todos os sistemas"""
        hoje = timezone.now().date()
        
        # Métricas de Treinamentos
        from treinamentos.models import Treinamento
        treinamentos = Treinamento.objects.all()
        treinamentos_vencimento_proximo = treinamentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=15)
        ).count()
        
        # Métricas de Tarefas
        from tarefas.models import Tarefas
        tarefas = Tarefas.objects.all()
        tarefas_atrasadas = tarefas.filter(
            prazo__lt=timezone.now(),
            status__in=['pendente', 'andamento', 'pausada']
        ).count()
        
        # Métricas de EPI
        from seguranca_trabalho.models import EntregaEPI
        entregas_epi = EntregaEPI.objects.all()
        entregas_sem_assinatura = entregas_epi.filter(
            Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True),
            Q(assinatura_imagem__isnull=True)
        ).count()
        
        # Métricas de Documentos
        from documentos.models import Documento
        documentos = Documento.objects.all()
        documentos_a_vencer = documentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=30)
        ).count()
        
        # Alertas Críticos
        alertas_criticos = []
        if treinamentos_vencimento_proximo > 0:
            alertas_criticos.append({
                'tipo': 'danger',
                'mensagem': f'{treinamentos_vencimento_proximo} treinamentos próximos do vencimento',
                'icone': '⚠️'
            })
        if tarefas_atrasadas > 0:
            alertas_criticos.append({
                'tipo': 'danger', 
                'mensagem': f'{tarefas_atrasadas} tarefas em atraso',
                'icone': '⏰'
            })
        if entregas_sem_assinatura > 0:
            alertas_criticos.append({
                'tipo': 'warning',
                'mensagem': f'{entregas_sem_assinatura} entregas de EPI sem assinatura',
                'icone': '📝'
            })
        if documentos_a_vencer > 0:
            alertas_criticos.append({
                'tipo': 'warning',
                'mensagem': f'{documentos_a_vencer} documentos próximos do vencimento',
                'icone': '📄'
            })
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard Geral - Visão Consolidada',
            'total_treinamentos': treinamentos.count(),
            'total_tarefas': tarefas.count(),
            'total_entregas_epi': entregas_epi.count(),
            'total_documentos': documentos.count(),
            'treinamentos_vencimento_proximo': treinamentos_vencimento_proximo,
            'tarefas_atrasadas': tarefas_atrasadas,
            'entregas_sem_assinatura': entregas_sem_assinatura,
            'documentos_a_vencer': documentos_a_vencer,
            'alertas_criticos': alertas_criticos,
        }
        
        return render(request, 'admin/dashboard_geral.html', context)
    
    def dashboard_treinamentos(self, request):
        """Dashboard específico de Treinamentos"""
        hoje = timezone.now().date()
        
        from treinamentos.models import Treinamento, Participante
        treinamentos = Treinamento.objects.all()
        total_treinamentos = treinamentos.count()
        
        # Status dos treinamentos
        status_data = treinamentos.values('status').annotate(total=Count('id'))
        
        # Vencimentos
        vencimento_proximo = treinamentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=15)
        ).count()
        
        vencidos = treinamentos.filter(data_vencimento__lt=hoje).count()
        
        # Participantes
        total_participantes = Participante.objects.count()
        participantes_presentes = Participante.objects.filter(presente=True).count()
        taxa_presenca = (participantes_presentes / total_participantes * 100) if total_participantes > 0 else 0
        
        # Próximos treinamentos
        proximos_treinamentos = treinamentos.filter(
            data_inicio__gte=hoje
        ).order_by('data_inicio')[:5]
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Treinamentos',
            'total_treinamentos': total_treinamentos,
            'status_data': list(status_data),
            'vencimento_proximo': vencimento_proximo,
            'vencidos': vencidos,
            'total_participantes': total_participantes,
            'taxa_presenca': round(taxa_presenca, 2),
            'proximos_treinamentos': proximos_treinamentos,
        }
        
        return render(request, 'admin/dashboard_treinamentos.html', context)
    
    def dashboard_tarefas(self, request):
        """Dashboard específico de Tarefas"""
        from tarefas.models import Tarefas
        tarefas = Tarefas.objects.all()
        total_tarefas = tarefas.count()
        
        # Status das tarefas
        status_data = tarefas.values('status').annotate(total=Count('id'))
        
        # Prioridades
        prioridade_data = tarefas.values('prioridade').annotate(total=Count('id'))
        
        # Tarefas atrasadas
        tarefas_atrasadas = tarefas.filter(
            prazo__lt=timezone.now(),
            status__in=['pendente', 'andamento', 'pausada']
        ).count()
        
        # Progresso médio
        progresso_total = sum(tarefa.progresso for tarefa in tarefas)
        progresso_medio = (progresso_total / total_tarefas) if total_tarefas > 0 else 0
        
        # Próximas tarefas a vencer
        tarefas_proximas = tarefas.filter(
            prazo__gte=timezone.now(),
            status__in=['pendente', 'andamento']
        ).order_by('prazo')[:5]
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Tarefas',
            'total_tarefas': total_tarefas,
            'status_data': list(status_data),
            'prioridade_data': list(prioridade_data),
            'tarefas_atrasadas': tarefas_atrasadas,
            'progresso_medio': round(progresso_medio, 2),
            'tarefas_proximas': tarefas_proximas,
        }
        
        return render(request, 'admin/dashboard_tarefas.html', context)
    
    def dashboard_epi(self, request):
        """Dashboard específico de EPI"""
        hoje = timezone.now().date()
        
        from seguranca_trabalho.models import Equipamento, EntregaEPI, MovimentacaoEstoque
        
        # Métricas de EPI
        equipamentos = Equipamento.objects.all()
        total_equipamentos = equipamentos.count()
        
        entregas = EntregaEPI.objects.all()
        total_entregas = entregas.count()
        
        # Entregas sem assinatura
        entregas_sem_assinatura = entregas.filter(
            Q(assinatura_recebimento='') | Q(assinatura_recebimento__isnull=True),
            Q(assinatura_imagem__isnull=True)
        ).count()
        
        # EPIs próximos do vencimento
        entregas_vencimento_proximo = entregas.annotate(
            data_vencimento_calc=F('data_entrega') + datetime.timedelta(days=F('equipamento__vida_util_dias'))
        ).filter(
            data_vencimento_calc__gte=hoje,
            data_vencimento_calc__lte=hoje + datetime.timedelta(days=30)
        ).count()
        
        # Movimentação de estoque
        movimentacoes = MovimentacaoEstoque.objects.all()
        total_entradas = movimentacoes.filter(tipo='ENTRADA').count()
        total_saidas = movimentacoes.filter(tipo='SAIDA').count()
        
        # Equipamentos com estoque baixo
        equipamentos_estoque_baixo = []
        for equipamento in equipamentos:
            # Calcular estoque atual (entradas - saídas)
            entradas = movimentacoes.filter(equipamento=equipamento, tipo='ENTRADA').aggregate(total=Count('id'))['total'] or 0
            saidas = movimentacoes.filter(equipamento=equipamento, tipo='SAIDA').aggregate(total=Count('id'))['total'] or 0
            estoque_atual = entradas - saidas
            
            if estoque_atual <= equipamento.estoque_minimo:
                equipamentos_estoque_baixo.append({
                    'equipamento': equipamento,
                    'estoque_atual': estoque_atual,
                    'estoque_minimo': equipamento.estoque_minimo
                })
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard de EPI',
            'total_equipamentos': total_equipamentos,
            'total_entregas': total_entregas,
            'entregas_sem_assinatura': entregas_sem_assinatura,
            'entregas_vencimento_proximo': entregas_vencimento_proximo,
            'total_entradas': total_entradas,
            'total_saidas': total_saidas,
            'equipamentos_estoque_baixo': equipamentos_estoque_baixo,
        }
        
        return render(request, 'admin/dashboard_epi.html', context)
    
    def dashboard_documentos(self, request):
        """Dashboard específico de Documentos"""
        hoje = timezone.now().date()
        
        from documentos.models import Documento
        documentos = Documento.objects.all()
        total_documentos = documentos.count()
        
        # Status dos documentos
        status_data = documentos.values('status').annotate(total=Count('id'))
        
        # Documentos a vencer (30 dias)
        documentos_a_vencer = documentos.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + datetime.timedelta(days=30)
        ).count()
        
        # Documentos vencidos
        documentos_vencidos = documentos.filter(
            data_vencimento__lt=hoje
        ).count()
        
        # Próximos vencimentos
        proximos_vencimentos = documentos.filter(
            data_vencimento__gte=hoje
        ).order_by('data_vencimento')[:5]
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard de Documentos',
            'total_documentos': total_documentos,
            'status_data': list(status_data),
            'documentos_a_vencer': documentos_a_vencer,
            'documentos_vencidos': documentos_vencidos,
            'proximos_vencimentos': proximos_vencimentos,
        }
        
        return render(request, 'admin/dashboard_documentos.html', context)

# ✅ Instância do dashboard
dashboard_site = DashboardAdminSite(name='dashboard_admin')
