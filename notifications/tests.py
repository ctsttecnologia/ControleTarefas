# notifications/tests.py

"""
Suite completa de testes do sistema de notificações (sino do header).

Cobre: Model, Views, API de contagem, Context Processor, Lista com filtros,
       Integração HTML, Fluxo E2E e Segurança.

Executar:
    python manage.py test notifications -v 2
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notificacao
from notifications.context_processors import notification_processor, MAX_DROPDOWN

User = get_user_model()


# ═════════════════════════════════════════════════════════════════════════════
# URL NAMES — centralizados para fácil manutenção
# ═════════════════════════════════════════════════════════════════════════════

URL_LISTA = 'notifications:notificacao_list'
URL_MARCAR_LIDA = 'notifications:marcar_como_lida'
URL_MARCAR_TODAS = 'notifications:marcar_todas_como_lidas'
URL_API_CONTAGEM = 'notifications:api_contagem'

# Senha padrão para todos os usuários de teste
TEST_PASSWORD = 'TestPass123!'


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES BASE REUTILIZÁVEIS
# ═════════════════════════════════════════════════════════════════════════════

class NotificacaoTestBase(TestCase):
    """
    Classe base com fixtures compartilhadas por todos os testes.
    Cria 3 usuários e 5 notificações no setUp de cada teste.

    IMPORTANTE: O User model customizado usa USERNAME_FIELD = 'email',
    portanto o login é feito com email, não username.
    """

    @classmethod
    def setUpTestData(cls):
        """Dados imutáveis — criados UMA vez para toda a classe."""
        cls.usuario = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=TEST_PASSWORD,
        )
        cls.outro_usuario = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password=TEST_PASSWORD,
        )
        cls.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password=TEST_PASSWORD,
            is_staff=True,
        )

    def setUp(self):
        """Executado antes de CADA teste — cria notificações frescas."""
        self.client = Client()
        self.client.login(email='test@example.com', password=TEST_PASSWORD)

        # ── 3 Notificações NÃO LIDAS do usuario principal ──

        self.notif_critica = Notificacao.objects.create(
            usuario=self.usuario,
            tipo='tarefa_atrasada',
            categoria='tarefa',
            prioridade='critica',
            titulo='Tarefa vencida!',
            mensagem='A tarefa X venceu ontem.',
            icone='bi-exclamation-triangle-fill',
            url_destino='/tarefas/1/',
        )
        self.notif_alta = Notificacao.objects.create(
            usuario=self.usuario,
            tipo='tarefa_prazo_proximo',
            categoria='tarefa',
            prioridade='alta',
            titulo='Tarefa próxima do prazo',
            mensagem='A tarefa Y vence amanhã.',
            icone='bi-clock-fill',
            url_destino='/tarefas/2/',
        )
        self.notif_media = Notificacao.objects.create(
            usuario=self.usuario,
            tipo='tarefa_comentario',
            categoria='tarefa',
            prioridade='media',
            titulo='Novo comentário',
            mensagem='João comentou na tarefa Z.',
            icone='bi-chat-dots-fill',
        )

        # ── 1 Notificação JÁ LIDA do usuario principal ──

        self.notif_lida = Notificacao.objects.create(
            usuario=self.usuario,
            tipo='tarefa_concluida',
            categoria='tarefa',
            prioridade='baixa',
            titulo='Tarefa concluída',
            mensagem='A tarefa W foi concluída.',
            icone='bi-check-circle-fill',
            lida=True,
        )

        # ── 1 Notificação de OUTRO usuário (isolamento) ──

        self.notif_outro = Notificacao.objects.create(
            usuario=self.outro_usuario,
            tipo='sistema',
            categoria='sistema',
            prioridade='baixa',
            titulo='Notificação alheia',
            mensagem='Esta não pertence ao testuser.',
            icone='bi-info-circle-fill',
        )

    def _total_nao_lidas(self, user=None):
        """Helper: conta notificações não lidas de um usuário."""
        user = user or self.usuario
        return Notificacao.objects.filter(usuario=user, lida=False).count()

    def _login_as(self, email):
        """Helper: loga com um email específico."""
        self.client.logout()
        return self.client.login(email=email, password=TEST_PASSWORD)


# ═════════════════════════════════════════════════════════════════════════════
# 1. TESTES DO MODEL
# ═════════════════════════════════════════════════════════════════════════════

class NotificacaoModelTest(NotificacaoTestBase):
    """Testes unitários do model Notificacao."""

    # ── Criação e Defaults ──

    def test_criacao_com_campos_minimos(self):
        """Notificação é criada corretamente com campos mínimos."""
        notif = Notificacao.objects.create(
            usuario=self.usuario,
            titulo='Teste mínimo',
        )
        self.assertIsNotNone(notif.pk)
        self.assertEqual(notif.usuario, self.usuario)
        self.assertEqual(notif.titulo, 'Teste mínimo')

    def test_default_lida_false(self):
        """Notificação nasce como não lida."""
        self.assertFalse(self.notif_critica.lida)

    def test_default_tipo_sistema(self):
        """Tipo padrão é 'sistema'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Default tipo',
        )
        self.assertEqual(notif.tipo, 'sistema')

    def test_default_categoria_sistema(self):
        """Categoria padrão é 'sistema'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Default categoria',
        )
        self.assertEqual(notif.categoria, 'sistema')

    def test_default_prioridade_media(self):
        """Prioridade padrão é 'media'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Default prioridade',
        )
        self.assertEqual(notif.prioridade, 'media')

    def test_default_icone_bell(self):
        """Ícone padrão é 'bi-bell'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Default icone',
        )
        self.assertEqual(notif.icone, 'bi-bell')

    def test_default_enviada_email_false(self):
        """enviada_email nasce como False."""
        self.assertFalse(self.notif_critica.enviada_email)

    def test_default_data_leitura_none(self):
        """data_leitura é None quando não lida."""
        self.assertIsNone(self.notif_critica.data_leitura)

    # ── __str__ ──

    def test_str_nao_lida_contem_circulo(self):
        """__str__ de não lida contém ◉, título e username."""
        texto = str(self.notif_critica)
        self.assertIn('◉', texto)
        self.assertIn('Tarefa vencida!', texto)
        self.assertIn('testuser', texto)

    def test_str_lida_contem_check(self):
        """__str__ de lida contém ✔ e o título."""
        texto = str(self.notif_lida)
        self.assertIn('✔', texto)
        self.assertIn('Tarefa concluída', texto)

    # ── Timestamps ──

    def test_data_criacao_auto(self):
        """data_criacao é preenchida automaticamente."""
        self.assertIsNotNone(self.notif_critica.data_criacao)
        self.assertAlmostEqual(
            self.notif_critica.data_criacao,
            timezone.now(),
            delta=timedelta(seconds=10),
        )

    def test_criada_em_auto(self):
        """criada_em é preenchida automaticamente."""
        self.assertIsNotNone(self.notif_critica.criada_em)

    # ── Ordering ──

    def test_ordering_mais_recente_primeiro(self):
        """Ordering padrão: mais recente primeiro (-data_criacao)."""
        notifs = list(Notificacao.objects.filter(usuario=self.usuario))
        for i in range(len(notifs) - 1):
            self.assertGreaterEqual(
                notifs[i].data_criacao, notifs[i + 1].data_criacao,
            )

    # ── marcar_como_lida() ──

    def test_marcar_como_lida_seta_true_e_data(self):
        """marcar_como_lida() seta lida=True e preenche data_leitura."""
        self.assertFalse(self.notif_critica.lida)
        self.assertIsNone(self.notif_critica.data_leitura)

        self.notif_critica.marcar_como_lida()
        self.notif_critica.refresh_from_db()

        self.assertTrue(self.notif_critica.lida)
        self.assertIsNotNone(self.notif_critica.data_leitura)
        self.assertAlmostEqual(
            self.notif_critica.data_leitura,
            timezone.now(),
            delta=timedelta(seconds=5),
        )

    def test_marcar_como_lida_idempotente(self):
        """Chamar em notificação já lida não altera data_leitura."""
        self.notif_critica.marcar_como_lida()
        data_primeira = self.notif_critica.data_leitura

        self.notif_critica.marcar_como_lida()
        self.notif_critica.refresh_from_db()

        self.assertEqual(self.notif_critica.data_leitura, data_primeira)

    def test_marcar_como_lida_usa_update_fields(self):
        """marcar_como_lida() salva APENAS lida e data_leitura."""
        titulo_original = self.notif_critica.titulo
        self.notif_critica.titulo = 'MODIFICADO EM MEMÓRIA'

        self.notif_critica.marcar_como_lida()
        self.notif_critica.refresh_from_db()

        self.assertEqual(self.notif_critica.titulo, titulo_original)

    # ── badge_class ──

    def test_badge_class_critica(self):
        self.assertEqual(
            self.notif_critica.badge_class,
            'bg-danger-subtle text-danger-emphasis',
        )

    def test_badge_class_alta(self):
        self.assertEqual(
            self.notif_alta.badge_class,
            'bg-warning-subtle text-warning-emphasis',
        )

    def test_badge_class_media(self):
        self.assertEqual(
            self.notif_media.badge_class,
            'bg-info-subtle text-info-emphasis',
        )

    def test_badge_class_baixa(self):
        self.assertEqual(
            self.notif_lida.badge_class,
            'bg-secondary-subtle text-secondary-emphasis',
        )

    def test_badge_class_desconhecida_fallback(self):
        """Prioridade desconhecida retorna fallback 'bg-secondary'."""
        self.notif_critica.prioridade = 'inexistente'
        self.assertEqual(self.notif_critica.badge_class, 'bg-secondary')

    # ── tempo_relativo ──

    def test_tempo_relativo_agora(self):
        """Recém-criada retorna 'agora'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Agora',
        )
        self.assertEqual(notif.tempo_relativo, 'agora')

    def test_tempo_relativo_minutos(self):
        """5 min atrás retorna 'há 5 min'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='5min',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(minutes=5)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 5 min')

    def test_tempo_relativo_horas(self):
        """3h atrás retorna 'há 3h'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='3h',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(hours=3)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 3h')

    def test_tempo_relativo_dias(self):
        """7 dias atrás retorna 'há 7d'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='7d',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(days=7)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 7d')

    def test_tempo_relativo_limite_59_segundos(self):
        """59 segundos atrás ainda retorna 'agora'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='59s',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(seconds=59)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'agora')

    def test_tempo_relativo_limite_60_segundos(self):
        """60 segundos = 'há 1 min'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='60s',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(seconds=60)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 1 min')

    def test_tempo_relativo_limite_23h(self):
        """23h atrás retorna 'há 23h'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='23h',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(hours=23)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 23h')

    def test_tempo_relativo_limite_24h(self):
        """24h (1 dia) retorna 'há 1d'."""
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='24h',
        )
        Notificacao.objects.filter(pk=notif.pk).update(
            data_criacao=timezone.now() - timedelta(hours=24)
        )
        notif.refresh_from_db()
        self.assertEqual(notif.tempo_relativo, 'há 1d')

    # ── Choices ──

    def test_todas_prioridades_aceitas(self):
        for code, _ in Notificacao.PRIORIDADE_CHOICES:
            notif = Notificacao.objects.create(
                usuario=self.usuario, titulo=f'P-{code}', prioridade=code,
            )
            self.assertEqual(notif.prioridade, code)

    def test_todas_categorias_aceitas(self):
        for code, _ in Notificacao.CATEGORIA_CHOICES:
            notif = Notificacao.objects.create(
                usuario=self.usuario, titulo=f'C-{code}', categoria=code,
            )
            self.assertEqual(notif.categoria, code)

    def test_todos_tipos_aceitos(self):
        for code, _ in Notificacao.TIPO_CHOICES:
            notif = Notificacao.objects.create(
                usuario=self.usuario, titulo=f'T-{code}', tipo=code,
            )
            self.assertEqual(notif.tipo, code)

    # ── Isolamento e Cascade ──

    def test_isolamento_querysets(self):
        """Querysets filtrados não se misturam entre usuários."""
        qs1 = Notificacao.objects.filter(usuario=self.usuario)
        qs2 = Notificacao.objects.filter(usuario=self.outro_usuario)
        self.assertNotIn(self.notif_outro, qs1)
        self.assertNotIn(self.notif_critica, qs2)

    def test_cascade_delete_usuario(self):
        """Deletar o usuário remove todas as suas notificações."""
        user_temp = User.objects.create_user(
            username='tempuser', email='temp@example.com',
            password=TEST_PASSWORD,
        )
        Notificacao.objects.create(usuario=user_temp, titulo='Temp')
        user_temp_id = user_temp.pk
        user_temp.delete()
        self.assertEqual(
            Notificacao.objects.filter(usuario_id=user_temp_id).count(), 0,
        )

    # ── Campos opcionais ──

    def test_url_destino_nullable(self):
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Sem URL',
        )
        self.assertIsNone(notif.url_destino)

    def test_url_destino_preenchido(self):
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Com URL', url_destino='/tarefas/42/',
        )
        self.assertEqual(notif.url_destino, '/tarefas/42/')

    def test_mensagem_blank_default(self):
        notif = Notificacao.objects.create(
            usuario=self.usuario, titulo='Sem msg',
        )
        self.assertEqual(notif.mensagem, '')

    # ── Meta ──

    def test_meta_verbose_name(self):
        self.assertEqual(Notificacao._meta.verbose_name, 'Notificação')
        self.assertEqual(Notificacao._meta.verbose_name_plural, 'Notificações')

    def test_meta_ordering(self):
        self.assertEqual(Notificacao._meta.ordering, ['-data_criacao'])

    def test_related_name(self):
        """related_name 'notifications' funciona no User."""
        qs = self.usuario.notificacoes.all()
        self.assertEqual(qs.count(), 4)  # 3 não lidas + 1 lida


# ═════════════════════════════════════════════════════════════════════════════
# 2. TESTES DA VIEW: MARCAR UMA COMO LIDA
# ═════════════════════════════════════════════════════════════════════════════

class MarcarComoLidaViewTest(NotificacaoTestBase):
    """
    Testes da view marcar_como_lida.
    NOTA: Esta view aceita GET e POST (sem @require_POST).
    """

    def test_get_marca_como_lida_e_redireciona_para_url_destino(self):
        """GET marca como lida e redireciona para url_destino."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        response = self.client.get(url)

        self.notif_critica.refresh_from_db()
        self.assertTrue(self.notif_critica.lida)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/tarefas/1/')

    def test_get_sem_url_destino_redireciona_referer(self):
        """GET sem url_destino redireciona para HTTP_REFERER."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_media.pk])
        response = self.client.get(url, HTTP_REFERER='/dashboard/')

        self.notif_media.refresh_from_db()
        self.assertTrue(self.notif_media.lida)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')

    def test_get_sem_url_destino_sem_referer_redireciona_raiz(self):
        """GET sem url_destino e sem referer redireciona para /."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_media.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_post_marca_como_lida(self):
        """POST marca a notificação como lida."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        response = self.client.post(url)

        self.notif_critica.refresh_from_db()
        self.assertTrue(self.notif_critica.lida)
        self.assertIsNotNone(self.notif_critica.data_leitura)

    def test_ajax_retorna_json(self):
        """Requisição AJAX retorna JsonResponse com status e id."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        response = self.client.get(
            url, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['id'], self.notif_critica.pk)

        self.notif_critica.refresh_from_db()
        self.assertTrue(self.notif_critica.lida)

    def test_notificacao_alheia_404(self):
        """Acessar notificação de outro usuário retorna 404."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_outro.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.notif_outro.refresh_from_db()
        self.assertFalse(self.notif_outro.lida)

    def test_notificacao_inexistente_404(self):
        """PK inexistente retorna 404."""
        url = reverse(URL_MARCAR_LIDA, args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_ja_lida_nao_quebra(self):
        """Marcar notificação já lida novamente não causa erro."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_lida.pk])
        response = self.client.get(url)

        self.notif_lida.refresh_from_db()
        self.assertTrue(self.notif_lida.lida)
        self.assertEqual(response.status_code, 302)

    def test_usuario_anonimo_redirecionado_login(self):
        """Anônimo é redirecionado para login."""
        self.client.logout()
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())

    def test_contagem_diminui_apos_marcar(self):
        """Contagem cai de 3 para 2 após marcar uma."""
        self.assertEqual(self._total_nao_lidas(), 3)

        url = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        self.client.get(url)

        self.assertEqual(self._total_nao_lidas(), 2)


# ═════════════════════════════════════════════════════════════════════════════
# 3. TESTES DA VIEW: MARCAR TODAS COMO LIDAS
# ═════════════════════════════════════════════════════════════════════════════

class MarcarTodasComoLidasViewTest(NotificacaoTestBase):
    """
    Testes da view marcar_todas_como_lidas.
    NOTA: Esta view usa @require_POST.
    """

    def test_post_marca_todas(self):
        """POST marca todas as não lidas como lidas."""
        self.assertEqual(self._total_nao_lidas(), 3)

        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(url)

        self.assertEqual(self._total_nao_lidas(), 0)
        self.assertEqual(response.status_code, 302)

    def test_get_retorna_405(self):
        """GET retorna 405 Method Not Allowed (@require_POST)."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_nao_afeta_outro_usuario(self):
        """Marcar todas NÃO afeta notificações de outros."""
        url = reverse(URL_MARCAR_TODAS)
        self.client.post(url)

        self.notif_outro.refresh_from_db()
        self.assertFalse(self.notif_outro.lida)

    def test_sem_pendentes_nao_quebra(self):
        """Chamar sem pendentes não causa erro."""
        Notificacao.objects.filter(usuario=self.usuario).update(lida=True)

        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_usuario_anonimo_redirecionado_login(self):
        """Anônimo é redirecionado para login."""
        self.client.logout()
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())

    def test_data_leitura_preenchida_via_update(self):
        """Bulk update preenche data_leitura nas 3 não lidas."""
        url = reverse(URL_MARCAR_TODAS)
        self.client.post(url)

        recem_marcadas = Notificacao.objects.filter(
            usuario=self.usuario,
            lida=True,
            data_leitura__isnull=False,
        ).exclude(pk=self.notif_lida.pk)
        self.assertEqual(recem_marcadas.count(), 3)

    def test_ajax_retorna_json_com_count(self):
        """AJAX retorna JSON com status e quantidade atualizada."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(
            url, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 3)

    def test_ajax_sem_pendentes_retorna_zero(self):
        """AJAX sem pendentes retorna count=0."""
        Notificacao.objects.filter(usuario=self.usuario).update(lida=True)

        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(
            url, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = response.json()
        self.assertEqual(data['count'], 0)

    def test_redireciona_para_referer(self):
        """Após POST (não-AJAX), redireciona para HTTP_REFERER."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(url, HTTP_REFERER='/notifications/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/notifications/')

    def test_sem_referer_redireciona_raiz(self):
        """Sem HTTP_REFERER, redireciona para /."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


# ═════════════════════════════════════════════════════════════════════════════
# 4. TESTES DA API DE CONTAGEM (Polling do sino)
# ═════════════════════════════════════════════════════════════════════════════

class APIContagemViewTest(NotificacaoTestBase):
    """Testes do endpoint api_contagem (polling JS do sino)."""

    def _get_contagem(self, client=None):
        """Helper: GET na API e retorna a response."""
        client = client or self.client
        return client.get(reverse(URL_API_CONTAGEM))

    def test_retorna_json_200(self):
        """Endpoint retorna JSON com status 200."""
        response = self._get_contagem()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_contagem_valor_correto(self):
        """Contagem retorna 3 (não lidas do setUp)."""
        data = self._get_contagem().json()
        self.assertEqual(data['count'], 3)

    def test_contagem_apos_marcar_uma(self):
        """Contagem cai para 2 após marcar uma."""
        self.notif_critica.marcar_como_lida()
        data = self._get_contagem().json()
        self.assertEqual(data['count'], 2)

    def test_contagem_zero(self):
        """Retorna 0 quando todas estão lidas."""
        Notificacao.objects.filter(usuario=self.usuario).update(lida=True)
        data = self._get_contagem().json()
        self.assertEqual(data['count'], 0)

    def test_nao_inclui_outro_usuario(self):
        """Contagem não inclui notificações de outros."""
        for i in range(5):
            Notificacao.objects.create(
                usuario=self.outro_usuario, titulo=f'Extra {i}',
            )
        data = self._get_contagem().json()
        self.assertEqual(data['count'], 3)

    def test_incrementa_com_nova(self):
        """Criar nova notificação incrementa a contagem."""
        count_antes = self._get_contagem().json()['count']
        Notificacao.objects.create(
            usuario=self.usuario, titulo='Nova!',
            tipo='tarefa_atribuida', prioridade='alta',
        )
        count_depois = self._get_contagem().json()['count']
        self.assertEqual(count_depois, count_antes + 1)

    def test_anonimo_redirecionado(self):
        """Anônimo é redirecionado para login."""
        self.client.logout()
        response = self._get_contagem()
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())

    def test_aceita_get_sem_header_ajax(self):
        """Endpoint funciona sem header X-Requested-With."""
        response = self.client.get(reverse(URL_API_CONTAGEM))
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.json())


# ═════════════════════════════════════════════════════════════════════════════
# 5. TESTES DO CONTEXT PROCESSOR
# ═════════════════════════════════════════════════════════════════════════════

class NotificationProcessorTest(NotificacaoTestBase):
    """Testes do context processor notification_processor."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def _make_request(self, user):
        """Helper: cria request fake autenticado."""
        request = self.factory.get('/')
        request.user = user
        return request

    def test_retorna_notification_count(self):
        """Retorna notification_count correto."""
        ctx = notification_processor(self._make_request(self.usuario))
        self.assertEqual(ctx['notification_count'], 3)

    def test_retorna_notification_list(self):
        """Retorna notification_list não vazia."""
        ctx = notification_processor(self._make_request(self.usuario))
        self.assertIn('notification_list', ctx)
        self.assertTrue(len(ctx['notification_list']) > 0)

    def test_lista_contem_apenas_nao_lidas(self):
        """notification_list só tem não lidas."""
        ctx = notification_processor(self._make_request(self.usuario))
        for notif in ctx['notification_list']:
            self.assertFalse(notif.lida)

    def test_lista_limitada_max_dropdown(self):
        """notification_list limitada a MAX_DROPDOWN (8) itens."""
        for i in range(15):
            Notificacao.objects.create(
                usuario=self.usuario, titulo=f'Extra {i}',
            )
        ctx = notification_processor(self._make_request(self.usuario))

        self.assertLessEqual(len(ctx['notification_list']), MAX_DROPDOWN)
        self.assertEqual(len(ctx['notification_list']), MAX_DROPDOWN)
        self.assertEqual(ctx['notification_count'], 18)  # 3 + 15

    def test_usuario_anonimo_retorna_vazio(self):
        """Anônimo recebe dict vazio."""
        ctx = notification_processor(self._make_request(AnonymousUser()))
        self.assertEqual(ctx, {})

    def test_isolamento_entre_usuarios(self):
        """Cada usuário só vê suas próprias."""
        ctx = notification_processor(self._make_request(self.outro_usuario))
        self.assertEqual(ctx['notification_count'], 1)
        for notif in ctx['notification_list']:
            self.assertEqual(notif.usuario, self.outro_usuario)

    def test_ordering_mais_recente_primeiro(self):
        """Lista ordenada da mais recente para mais antiga."""
        ctx = notification_processor(self._make_request(self.usuario))
        lista = list(ctx['notification_list'])
        for i in range(len(lista) - 1):
            self.assertGreaterEqual(
                lista[i].data_criacao, lista[i + 1].data_criacao,
            )

    def test_usuario_sem_notificacoes(self):
        """Usuário sem notificações recebe count=0 e lista vazia."""
        ctx = notification_processor(self._make_request(self.staff_user))
        self.assertEqual(ctx['notification_count'], 0)
        self.assertEqual(len(ctx['notification_list']), 0)


# ═════════════════════════════════════════════════════════════════════════════
# 6. TESTES DA LISTA DE NOTIFICAÇÕES (Página com filtros e paginação)
# ═════════════════════════════════════════════════════════════════════════════

class NotificacaoListViewTest(NotificacaoTestBase):
    """Testes da view notificacao_list (nome URL: 'lista')."""

    def test_acessivel_200(self):
        """Página retorna 200."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_context_contem_variaveis_esperadas(self):
        """Context contém as variáveis corretas."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        self.assertIn('notificacoes', response.context)
        self.assertIn('filtro', response.context)
        self.assertIn('categoria', response.context)
        self.assertIn('nao_lidas_count', response.context)
        self.assertIn('titulo_pagina', response.context)

    def test_filtro_padrao_todas(self):
        """Filtro padrão é 'todas' — mostra lidas e não lidas."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)

        self.assertEqual(response.context['filtro'], 'todas')
        titulos = [n.titulo for n in response.context['notificacoes']]
        self.assertIn('Tarefa vencida!', titulos)
        self.assertIn('Tarefa concluída', titulos)

    def test_filtro_nao_lidas(self):
        """Filtro 'nao_lidas' mostra apenas não lidas."""
        url = reverse(URL_LISTA) + '?filtro=nao_lidas'
        response = self.client.get(url)

        self.assertEqual(response.context['filtro'], 'nao_lidas')
        for notif in response.context['notificacoes']:
            self.assertFalse(notif.lida)

    def test_filtro_lidas(self):
        """Filtro 'lidas' mostra apenas lidas."""
        url = reverse(URL_LISTA) + '?filtro=lidas'
        response = self.client.get(url)

        self.assertEqual(response.context['filtro'], 'lidas')
        for notif in response.context['notificacoes']:
            self.assertTrue(notif.lida)

    def test_filtro_por_categoria(self):
        """Filtro por categoria funciona."""
        Notificacao.objects.create(
            usuario=self.usuario, titulo='PGR teste',
            tipo='pgr_vencimento', categoria='pgr',
        )
        url = reverse(URL_LISTA) + '?categoria=pgr'
        response = self.client.get(url)

        for notif in response.context['notificacoes']:
            self.assertEqual(notif.categoria, 'pgr')

    def test_filtro_categoria_e_status_combinados(self):
        """Filtros de categoria e status funcionam juntos."""
        url = reverse(URL_LISTA) + '?filtro=nao_lidas&categoria=tarefa'
        response = self.client.get(url)

        for notif in response.context['notificacoes']:
            self.assertFalse(notif.lida)
            self.assertEqual(notif.categoria, 'tarefa')

    def test_nao_lidas_count_no_context(self):
        """nao_lidas_count é sempre a contagem total de não lidas."""
        url = reverse(URL_LISTA) + '?filtro=lidas'
        response = self.client.get(url)
        self.assertEqual(response.context['nao_lidas_count'], 3)

    def test_nao_mostra_alheias(self):
        """NÃO mostra notificações de outros usuários."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        content = response.content.decode()
        self.assertNotIn('Notificação alheia', content)

    def test_paginacao_30_por_pagina(self):
        """Paginação de 30 itens por página."""
        for i in range(35):
            Notificacao.objects.create(
                usuario=self.usuario, titulo=f'Pag {i}',
            )
        url = reverse(URL_LISTA)
        response = self.client.get(url)

        paginator = response.context['notificacoes']
        self.assertEqual(paginator.paginator.per_page, 30)
        self.assertTrue(paginator.paginator.num_pages >= 2)

    def test_paginacao_pagina_2(self):
        """Acessar página 2 funciona."""
        for i in range(35):
            Notificacao.objects.create(
                usuario=self.usuario, titulo=f'Pag {i}',
            )
        url = reverse(URL_LISTA) + '?page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['notificacoes']) > 0)

    def test_ordering_mais_recente_primeiro(self):
        """Lista ordenada por -data_criacao."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        notifs = list(response.context['notificacoes'])
        for i in range(len(notifs) - 1):
            self.assertGreaterEqual(
                notifs[i].data_criacao, notifs[i + 1].data_criacao,
            )

    def test_anonimo_redirecionado_login(self):
        """Anônimo é redirecionado para login."""
        self.client.logout()
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())

    def test_titulo_pagina(self):
        """titulo_pagina é 'Notificações'."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)
        self.assertEqual(response.context['titulo_pagina'], 'Notificações')


# ═════════════════════════════════════════════════════════════════════════════
# 7. TESTES DE INTEGRAÇÃO (Header / Dropdown HTML)
# ═════════════════════════════════════════════════════════════════════════════

class HeaderNotificacaoIntegrationTest(NotificacaoTestBase):
    """Testes de integração: HTML renderizado com context processor."""

    def _get_page_content(self):
        """Helper: pega HTML da lista de notificações."""
        response = self.client.get(reverse(URL_LISTA))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_sino_presente_no_header(self):
        """Ícone do sino está presente no HTML."""
        content = self._get_page_content()
        self.assertTrue(
            'bi-bell' in content or 'notification' in content.lower(),
        )

    def test_titulos_no_html(self):
        """Títulos das notificações aparecem no HTML."""
        content = self._get_page_content()
        self.assertIn('Tarefa vencida!', content)

    def test_notificacao_alheia_ausente(self):
        """Notificação de outro usuário não aparece."""
        content = self._get_page_content()
        self.assertNotIn('Notificação alheia', content)


# ═════════════════════════════════════════════════════════════════════════════
# 8. TESTES DE FLUXO COMPLETO (End-to-End)
# ═════════════════════════════════════════════════════════════════════════════

class NotificacaoFluxoCompletoTest(NotificacaoTestBase):
    """Testes E2E simulando o fluxo real do usuário no sino."""

    def test_fluxo_completo_sino(self):
        """
        1. Badge mostra 3
        2. Clica numa notificação → marca como lida (GET)
        3. Badge mostra 2
        4. Marca todas como lidas (POST)
        5. Badge mostra 0
        """
        url_api = reverse(URL_API_CONTAGEM)

        # 1. Contagem = 3
        self.assertEqual(self.client.get(url_api).json()['count'], 3)

        # 2. Clica na notificação (GET simula clique no dropdown)
        url_click = reverse(URL_MARCAR_LIDA, args=[self.notif_critica.pk])
        response = self.client.get(url_click)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/tarefas/1/')

        # 3. Contagem = 2
        self.assertEqual(self.client.get(url_api).json()['count'], 2)

        # 4. Marca todas
        self.client.post(reverse(URL_MARCAR_TODAS))

        # 5. Contagem = 0
        self.assertEqual(self.client.get(url_api).json()['count'], 0)

    def test_fluxo_ajax_marcar_uma(self):
        """AJAX: marca uma → JSON ok → contagem atualiza."""
        url_api = reverse(URL_API_CONTAGEM)

        self.assertEqual(self.client.get(url_api).json()['count'], 3)

        url_marcar = reverse(URL_MARCAR_LIDA, args=[self.notif_alta.pk])
        resp = self.client.get(
            url_marcar, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.json()['status'], 'ok')
        self.assertEqual(resp.json()['id'], self.notif_alta.pk)

        self.assertEqual(self.client.get(url_api).json()['count'], 2)

    def test_fluxo_ajax_marcar_todas(self):
        """AJAX: marca todas → JSON com count → contagem zera."""
        url = reverse(URL_MARCAR_TODAS)
        resp = self.client.post(
            url, HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 3)

        url_api = reverse(URL_API_CONTAGEM)
        self.assertEqual(self.client.get(url_api).json()['count'], 0)

    def test_nova_notificacao_incrementa_contagem(self):
        """Criar nova notificação incrementa contagem na API."""
        url_api = reverse(URL_API_CONTAGEM)
        antes = self.client.get(url_api).json()['count']

        Notificacao.objects.create(
            usuario=self.usuario,
            tipo='tarefa_atribuida',
            titulo='Tarefa XYZ atribuída',
            categoria='tarefa',
            prioridade='alta',
        )

        depois = self.client.get(url_api).json()['count']
        self.assertEqual(depois, antes + 1)

    def test_multiplos_usuarios_simultaneos(self):
        """Dois usuários simultâneos: isolamento completo."""
        client1 = Client()
        client1.login(email='test@example.com', password=TEST_PASSWORD)

        client2 = Client()
        client2.login(email='other@example.com', password=TEST_PASSWORD)

        url_api = reverse(URL_API_CONTAGEM)

        self.assertEqual(client1.get(url_api).json()['count'], 3)
        self.assertEqual(client2.get(url_api).json()['count'], 1)

        client1.post(reverse(URL_MARCAR_TODAS))

        self.assertEqual(client1.get(url_api).json()['count'], 0)
        self.assertEqual(client2.get(url_api).json()['count'], 1)

    def test_volume_100_notificacoes(self):
        """100+ notificações: contagem, página e marcar todas funcionam."""
        Notificacao.objects.bulk_create([
            Notificacao(
                usuario=self.usuario, titulo=f'Vol {i}',
                tipo='sistema', categoria='sistema', prioridade='baixa',
            )
            for i in range(100)
        ])

        url_api = reverse(URL_API_CONTAGEM)
        self.assertEqual(self.client.get(url_api).json()['count'], 103)

        url_list = reverse(URL_LISTA)
        self.assertEqual(self.client.get(url_list).status_code, 200)

        self.client.post(reverse(URL_MARCAR_TODAS))
        self.assertEqual(self.client.get(url_api).json()['count'], 0)


# ═════════════════════════════════════════════════════════════════════════════
# 9. TESTES DE SEGURANÇA
# ═════════════════════════════════════════════════════════════════════════════

class NotificacaoSegurancaTest(NotificacaoTestBase):
    """Testes de segurança e proteção contra abusos."""

    def test_csrf_obrigatorio_marcar_todas(self):
        """POST sem CSRF em marcar_todas é rejeitado (403)."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(email='test@example.com', password=TEST_PASSWORD)

        url = reverse(URL_MARCAR_TODAS)
        response = csrf_client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_nao_pode_marcar_alheia(self):
        """Manipular PK não permite acessar notificação alheia."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_outro.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.notif_outro.refresh_from_db()
        self.assertFalse(self.notif_outro.lida)

    def test_staff_nao_ve_alheias(self):
        """Staff vê apenas suas próprias (count=0)."""
        staff_client = Client()
        staff_client.login(email='staff@example.com', password=TEST_PASSWORD)

        url_api = reverse(URL_API_CONTAGEM)
        data = staff_client.get(url_api).json()
        self.assertEqual(data['count'], 0)

    def test_pk_inexistente_404(self):
        """PK inexistente retorna 404."""
        url = reverse(URL_MARCAR_LIDA, args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_put_marcar_todas_405(self):
        """PUT em marcar_todas retorna 405."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.put(url)
        self.assertEqual(response.status_code, 405)

    def test_delete_marcar_todas_405(self):
        """DELETE em marcar_todas retorna 405."""
        url = reverse(URL_MARCAR_TODAS)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 405)

    def test_get_object_404_filtra_por_usuario(self):
        """get_object_or_404 filtra por usuario=request.user."""
        url = reverse(URL_MARCAR_LIDA, args=[self.notif_outro.pk])

        # testuser (não é dono) → 404
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # otheruser (é dono) → funciona
        other_client = Client()
        other_client.login(email='other@example.com', password=TEST_PASSWORD)
        response = other_client.get(url)
        self.assertIn(response.status_code, [200, 302])

    def test_lista_filtra_apenas_do_usuario(self):
        """notificacao_list filtra pelo usuario logado."""
        url = reverse(URL_LISTA)
        response = self.client.get(url)

        for notif in response.context['notificacoes']:
            self.assertEqual(notif.usuario_id, self.usuario.pk)

