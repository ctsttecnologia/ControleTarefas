
# criar_grupos_tributacao.py

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from tributacao.models import NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual


class Command(BaseCommand):
    help = 'Cria os grupos de permissão do app Tributação'

    def handle(self, *args, **options):
        # ── 1. VISUALIZADOR ──────────────────────────────────────────
        visualizador, _ = Group.objects.get_or_create(name='TRIBUTACAO_VISUALIZADOR')
        perms_view = []
        for model in [NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual]:
            ct = ContentType.objects.get_for_model(model)
            perms_view.append(Permission.objects.get(
                content_type=ct,
                codename=f'view_{model._meta.model_name}'
            ))
        visualizador.permissions.set(perms_view)
        self.stdout.write(self.style.SUCCESS(
            f'✅ TRIBUTACAO_VISUALIZADOR: {len(perms_view)} permissões'
        ))

        # ── 2. OPERADOR (cria grupos tributários da sua filial) ──────
        operador, _ = Group.objects.get_or_create(name='TRIBUTACAO_OPERADOR')
        perms_operador = list(perms_view)  # inclui todas as view
        for model in [GrupoTributario, TributacaoFederal, TributacaoEstadual]:
            ct = ContentType.objects.get_for_model(model)
            for action in ['add', 'change', 'delete']:
                perms_operador.append(Permission.objects.get(
                    content_type=ct,
                    codename=f'{action}_{model._meta.model_name}'
                ))
        operador.permissions.set(perms_operador)
        self.stdout.write(self.style.SUCCESS(
            f'✅ TRIBUTACAO_OPERADOR: {len(perms_operador)} permissões'
        ))

        # ── 3. GESTOR GLOBAL (tudo + bypass filial + tabelas fiscais) ─
        gestor, _ = Group.objects.get_or_create(name='TRIBUTACAO_GESTOR_GLOBAL')
        perms_gestor = list(perms_operador)

        # CRUD completo em NCM/CFOP/CST
        for model in [NCM, CFOP, CST]:
            ct = ContentType.objects.get_for_model(model)
            for action in ['add', 'change', 'delete']:
                perms_gestor.append(Permission.objects.get(
                    content_type=ct,
                    codename=f'{action}_{model._meta.model_name}'
                ))

        # Custom permissions
        ct_ncm = ContentType.objects.get_for_model(NCM)
        perms_gestor.append(Permission.objects.get(
            content_type=ct_ncm,
            codename='pode_gerenciar_tabelas_fiscais'
        ))

        ct_grupo = ContentType.objects.get_for_model(GrupoTributario)
        perms_gestor.append(Permission.objects.get(
            content_type=ct_grupo,
            codename='pode_gerenciar_todas_filiais'
        ))

        gestor.permissions.set(perms_gestor)
        self.stdout.write(self.style.SUCCESS(
            f'✅ TRIBUTACAO_GESTOR_GLOBAL: {len(perms_gestor)} permissões'
        ))

        self.stdout.write(self.style.HTTP_INFO('\n🎉 Grupos criados com sucesso!'))

