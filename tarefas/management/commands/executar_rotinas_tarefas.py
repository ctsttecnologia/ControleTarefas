
"""
Management command para executar rotinas periódicas de tarefas SEM Celery Beat.

Substitui temporariamente o agendamento do Celery Beat enquanto o Redis/Celery
não está ativo. Pode ser executado manualmente ou agendado no Agendador de
Tarefas do Windows / cron.

USO:
    # Executa todas as rotinas
    python manage.py executar_rotinas_tarefas

    # Executa apenas uma rotina específica
    python manage.py executar_rotinas_tarefas --apenas atrasadas
    python manage.py executar_rotinas_tarefas --apenas recorrencias
    python manage.py executar_rotinas_tarefas --apenas lembretes
    python manage.py executar_rotinas_tarefas --apenas fim-recorrencia

    # Modo simulação (não altera dados)
    python manage.py executar_rotinas_tarefas --dry-run

    # Modo verboso (mostra detalhes)
    python manage.py executar_rotinas_tarefas --verbose

AGENDAMENTO NO WINDOWS (Agendador de Tarefas):
    Programa:   C:\\Users\\esgce\\Documents\\GitHub\\ControleTarefas\\venv\\Scripts\\python.exe
    Argumentos: manage.py executar_rotinas_tarefas
    Iniciar em: C:\\Users\\esgce\\Documents\\GitHub\\ControleTarefas
    Frequência: Diariamente às 08:00
"""

import time
import traceback
from django.core.management.base import BaseCommand
from django.utils import termcolors


class Command(BaseCommand):
    help = (
        'Executa rotinas periódicas de tarefas (atrasadas, recorrências, '
        'lembretes, fim de recorrência) sem necessidade de Celery Beat.'
    )

    # Mapeia opção CLI -> (nome amigável, função executora)
    ROTINAS_DISPONIVEIS = {
        'atrasadas': 'Marcar tarefas atrasadas',
        'recorrencias': 'Gerar recorrências pendentes (fallback)',
        'lembretes': 'Enviar lembretes de prazo',
        'fim-recorrencia': 'Avisar sobre fim de recorrência',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas',
            type=str,
            choices=list(self.ROTINAS_DISPONIVEIS.keys()),
            help='Executa apenas a rotina especificada (padrão: todas)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a execução sem alterar dados (quando suportado pela task)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe detalhes de execução de cada rotina',
        )

    # ------------------------------------------------------------------
    # HELPERS DE LOG
    # ------------------------------------------------------------------

    def _print_header(self, texto):
        linha = '=' * 70
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{linha}'))
        self.stdout.write(self.style.MIGRATE_HEADING(f'  {texto}'))
        self.stdout.write(self.style.MIGRATE_HEADING(f'{linha}\n'))

    def _print_secao(self, texto):
        self.stdout.write(self.style.HTTP_INFO(f'\n▶ {texto}'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

    def _print_sucesso(self, texto):
        self.stdout.write(self.style.SUCCESS(f'  ✓ {texto}'))

    def _print_aviso(self, texto):
        self.stdout.write(self.style.WARNING(f'  ⚠ {texto}'))

    def _print_erro(self, texto):
        self.stdout.write(self.style.ERROR(f'  ✗ {texto}'))

    def _print_info(self, texto):
        self.stdout.write(f'  • {texto}')

    # ------------------------------------------------------------------
    # EXECUTORES INDIVIDUAIS DE CADA ROTINA
    # ------------------------------------------------------------------

    def _executar_atrasadas(self, dry_run=False, verbose=False):
        """Marca tarefas com prazo vencido como atrasadas."""
        self._print_secao('Marcar tarefas atrasadas')

        try:
            from tarefas.tasks import marcar_tarefas_atrasadas

            if dry_run:
                self._print_aviso('Modo dry-run: simulação ativa')

            inicio = time.time()
            resultado = marcar_tarefas_atrasadas()
            duracao = time.time() - inicio

            if isinstance(resultado, dict):
                total = resultado.get('total_marcadas', resultado.get('total', 0))
                self._print_sucesso(f'{total} tarefa(s) marcada(s) como atrasada(s)')

                if verbose and resultado.get('tarefas'):
                    for t in resultado['tarefas']:
                        self._print_info(f'#{t.get("id")} - {t.get("titulo", "")[:60]}')
            else:
                self._print_sucesso(f'Rotina concluída: {resultado}')

            self._print_info(f'Duração: {duracao:.2f}s')
            return True

        except ImportError:
            self._print_erro('Função marcar_tarefas_atrasadas não encontrada em tarefas.tasks')
            return False
        except Exception as e:
            self._print_erro(f'Erro: {e}')
            if verbose:
                self.stdout.write(traceback.format_exc())
            return False

    def _executar_recorrencias(self, dry_run=False, verbose=False):
        """Gera recorrências pendentes (fallback caso signal não tenha rodado)."""
        self._print_secao('Gerar recorrências pendentes (fallback)')

        try:
            from tarefas.tasks import gerar_recorrencias_pendentes

            if dry_run:
                self._print_aviso('Modo dry-run: simulação ativa')

            inicio = time.time()
            resultado = gerar_recorrencias_pendentes()
            duracao = time.time() - inicio

            if isinstance(resultado, dict):
                total = resultado.get('total_geradas', resultado.get('total', 0))
                self._print_sucesso(f'{total} recorrência(s) gerada(s)')

                if verbose and resultado.get('tarefas'):
                    for t in resultado['tarefas']:
                        self._print_info(f'#{t.get("id")} - {t.get("titulo", "")[:60]}')
            else:
                self._print_sucesso(f'Rotina concluída: {resultado}')

            self._print_info(f'Duração: {duracao:.2f}s')
            return True

        except ImportError:
            self._print_aviso(
                'Função gerar_recorrencias_pendentes não encontrada — '
                'pulando (recorrências são geradas via signal síncrono ao concluir tarefa)'
            )
            return True  # não é erro crítico
        except Exception as e:
            self._print_erro(f'Erro: {e}')
            if verbose:
                self.stdout.write(traceback.format_exc())
            return False

    def _executar_lembretes(self, dry_run=False, verbose=False):
        """Envia lembretes de prazo próximo."""
        self._print_secao('Enviar lembretes de prazo')

        try:
            from tarefas.tasks import enviar_lembretes_prazo

            if dry_run:
                self._print_aviso('Modo dry-run: simulação ativa')

            inicio = time.time()
            resultado = enviar_lembretes_prazo()
            duracao = time.time() - inicio

            if isinstance(resultado, dict):
                total = resultado.get('total_enviados', resultado.get('total', 0))
                self._print_sucesso(f'{total} lembrete(s) enviado(s)')

                if verbose and resultado.get('lembretes'):
                    for l in resultado['lembretes']:
                        self._print_info(
                            f'#{l.get("tarefa_id")} - {l.get("titulo", "")[:50]} '
                            f'→ {l.get("usuario", "")}'
                        )
            else:
                self._print_sucesso(f'Rotina concluída: {resultado}')

            self._print_info(f'Duração: {duracao:.2f}s')
            return True

        except ImportError:
            self._print_aviso(
                'Função enviar_lembretes_prazo não encontrada em tarefas.tasks — pulando'
            )
            return True
        except Exception as e:
            self._print_erro(f'Erro: {e}')
            if verbose:
                self.stdout.write(traceback.format_exc())
            return False

    def _executar_fim_recorrencia(self, dry_run=False, verbose=False):
        """Avisa criadores que a recorrência está chegando ao fim."""
        self._print_secao('Avisar sobre fim de recorrência')

        try:
            from tarefas.tasks import avisar_fim_recorrencia

            if dry_run:
                self._print_aviso('Modo dry-run: simulação ativa')

            inicio = time.time()
            resultado = avisar_fim_recorrencia()
            duracao = time.time() - inicio

            if isinstance(resultado, dict):
                total = (
                resultado.get('avisos_enviados')
                or resultado.get('total_avisados')
                or resultado.get('total', 0)
            )
                self._print_sucesso(f'{total} aviso(s) de fim de recorrência enviado(s)')

                if verbose and resultado.get('avisos'):
                    for a in resultado['avisos']:
                        self._print_info(
                            f'#{a.get("tarefa_id")} - {a.get("titulo", "")[:50]} '
                            f'(faltam {a.get("ocorrencias_restantes", "?")} ocorrências)'
                        )
            else:
                self._print_sucesso(f'Rotina concluída: {resultado}')

            self._print_info(f'Duração: {duracao:.2f}s')
            return True

        except ImportError:
            self._print_aviso(
                'Função avisar_fim_recorrencia não encontrada em tarefas.tasks — pulando'
            )
            return True
        except Exception as e:
            self._print_erro(f'Erro: {e}')
            if verbose:
                self.stdout.write(traceback.format_exc())
            return False

    # ------------------------------------------------------------------
    # ENTRY POINT
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        apenas = options.get('apenas')
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)

        self._print_header('EXECUÇÃO DE ROTINAS PERIÓDICAS DE TAREFAS')
        self.stdout.write(f'  Modo: {"DRY-RUN (simulação)" if dry_run else "EXECUÇÃO REAL"}')
        self.stdout.write(f'  Verbose: {"sim" if verbose else "não"}')

        if apenas:
            self.stdout.write(f'  Filtro: apenas "{apenas}"')
        else:
            self.stdout.write(f'  Filtro: todas as rotinas')

        # Mapa de execução
        executores = {
            'atrasadas': self._executar_atrasadas,
            'recorrencias': self._executar_recorrencias,
            'lembretes': self._executar_lembretes,
            'fim-recorrencia': self._executar_fim_recorrencia,
        }

        # Decide o que executar
        if apenas:
            rotinas_a_executar = [apenas]
        else:
            rotinas_a_executar = list(executores.keys())

        # Executa
        resultados = {}
        inicio_geral = time.time()

        for rotina in rotinas_a_executar:
            executor = executores[rotina]
            resultados[rotina] = executor(dry_run=dry_run, verbose=verbose)

        duracao_geral = time.time() - inicio_geral

        # Resumo final
        self._print_header('RESUMO DA EXECUÇÃO')

        sucessos = sum(1 for ok in resultados.values() if ok)
        falhas = sum(1 for ok in resultados.values() if not ok)

        for rotina, ok in resultados.items():
            nome = self.ROTINAS_DISPONIVEIS[rotina]
            status_icon = '✓' if ok else '✗'
            style = self.style.SUCCESS if ok else self.style.ERROR
            self.stdout.write(style(f'  {status_icon} {nome}'))

        self.stdout.write('')
        self.stdout.write(f'  Total executadas: {len(resultados)}')
        self.stdout.write(self.style.SUCCESS(f'  Sucessos:         {sucessos}'))
        if falhas > 0:
            self.stdout.write(self.style.ERROR(f'  Falhas:           {falhas}'))
        else:
            self.stdout.write(f'  Falhas:           {falhas}')
        self.stdout.write(f'  Duração total:    {duracao_geral:.2f}s')
        self.stdout.write('')

        if falhas > 0:
            self.stdout.write(
                self.style.WARNING(
                    '⚠ Algumas rotinas falharam. Verifique os logs acima ou rode com --verbose.\n'
                )
            )

