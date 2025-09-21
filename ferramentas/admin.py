from django.contrib import admin
from django.utils.html import format_html
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from .models import Ferramenta, Movimentacao, Atividade
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

User = get_user_model()

class AtividadeInline(admin.TabularInline):
    model = Atividade
    extra = 0
    fields = ('timestamp', 'tipo_atividade', 'descricao', 'usuario')
    readonly_fields = fields # Corrigido para tornar todos os campos readonly
    can_delete = False
    verbose_name = "Registro de Atividade"
    verbose_name_plural = "Registros de Atividades"

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Ferramenta)
class FerramentaAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('nome', 'patrimonio', 'status', 'filial', 'qr_code_preview')
    list_filter = ('status', 'fabricante', 'filial')
    search_fields = ('nome', 'patrimonio', 'codigo_identificacao')
    readonly_fields = ('qr_code_preview', 'filial',)
    inlines = [AtividadeInline]
    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'filial', 'patrimonio', 'codigo_identificacao', 'fabricante', 'qr_code_preview')
        }),
        ('Status e Localização', {
            'fields': ('status', 'localizacao_padrao', 'data_aquisicao')
        }),
        ('Outras Informações', {
            'classes': ('collapse',),
            'fields': ('observacoes',)
        }),
    )

    @admin.display(description="QR Code")
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return "Será gerado ao salvar"

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve o método de salvamento para enviar uma notificação por e-mail
        na criação de uma nova ferramenta.
        """
        # Primeiro, salva o objeto no banco de dados como de costume.
        super().save_model(request, obj, form, change)

        # A lógica de notificação é executada apenas se for uma NOVA criação (change=False).
        if not change:
            # 1. Encontra todos os administradores (superusuários) para notificar
            admins = User.objects.filter(is_superuser=True, is_active=True)
            admin_emails = [admin.email for admin in admins if admin.email]

            if not admin_emails:
                return  # Não faz nada se nenhum admin com e-mail for encontrado

            # 2. Prepara o conteúdo do e-mail
            assunto = f"Nova Ferramenta Cadastrada: {obj.nome}"
            
            # Constrói a URL completa para a nova ferramenta no admin
            admin_url = request.build_absolute_uri(
                reverse('admin:ferramentas_ferramenta_change', args=[obj.pk])
            )

            mensagem = f"""
            Olá,
            
            Uma nova ferramenta foi cadastrada no sistema.

            Detalhes:
            - Nome: {obj.nome}
            - Patrimônio: {obj.patrimonio or 'N/A'}
            - Código de Identificação: {obj.codigo_identificacao}
            - Cadastrado por: {request.user.get_full_name() or request.user.username}
            - Filial: {obj.filial.nome if obj.filial else 'N/A'}

            Você pode visualizar e gerenciar a nova ferramenta no link abaixo:
            {admin_url}

            Atenciosamente,
            Sistema de Gerenciamento.
            """

            # 3. Envia o e-mail
            try:
                send_mail(
                    subject=assunto,
                    message=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,  # Garanta que esta variável esteja configurada em seu settings.py
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
            except Exception as e:
                # Adiciona uma mensagem de erro no admin caso o e-mail falhe
                self.message_user(request, f"A ferramenta foi salva, mas ocorreu um erro ao enviar a notificação por e-mail: {e}", level='WARNING')


@admin.register(Movimentacao)
class MovimentacaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('ferramenta', 'retirado_por', 'data_retirada', 'esta_ativa', 'filial')
    list_filter = ('data_retirada', 'filial', 'ferramenta__nome')
    search_fields = ('ferramenta__nome', 'retirado_por__username')
    readonly_fields = (
        'ferramenta', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista',
        'condicoes_retirada', 'assinatura_retirada_preview', 'recebido_por',
        'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview'
    )
    fieldsets = (
        ('Dados da Retirada', {
            'fields': ('ferramenta', 'filial', 'retirado_por', 'data_retirada', 'data_devolucao_prevista', 'condicoes_retirada', 'assinatura_retirada_preview')
        }),
        ('Dados da Devolução', {
            'fields': ('recebido_por', 'data_devolucao', 'condicoes_devolucao', 'assinatura_devolucao_preview')
        }),
    )

    @admin.display(description="Assinatura (Retirada)")
    def assinatura_retirada_preview(self, obj):
        if obj.assinatura_retirada:
            return format_html('<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />', obj.assinatura_retirada.url)
        return "Não fornecida"

    @admin.display(description="Assinatura (Devolução)")
    def assinatura_devolucao_preview(self, obj):
        if obj.assinatura_devolucao:
            return format_html('<img src="{}" width="150" height="50" style="border: 1px solid #ccc;" />', obj.assinatura_devolucao.url)
        return "Não fornecida"

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Atividade)
class AtividadeAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('timestamp', 'ferramenta', 'tipo_atividade', 'usuario', 'filial')
    list_filter = ('tipo_atividade', 'timestamp', 'filial')
    search_fields = ('ferramenta__nome', 'descricao', 'usuario__username')
    readonly_fields = ('timestamp', 'ferramenta', 'tipo_atividade', 'descricao', 'usuario', 'filial')

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
