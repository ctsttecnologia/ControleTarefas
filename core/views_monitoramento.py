# core/views_monitoramento.py

import psutil
import os
import shutil
from datetime import datetime
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.conf import settings
import redis
import time
from django.core.cache import cache
from django.db import connection

from core.mixins import MonitoramentoAccessMixin

_mysql_anterior = {}

def pode_monitorar(user):
    """Wrapper para usar com decorator user_passes_test."""
    return MonitoramentoAccessMixin.user_can_monitor(user)


def _get_disco_path():
    """Retorna o path correto para análise de disco em qualquer ambiente."""
    paths_candidatos = [
        '/home/application/app',           # Produção (container Linux)
        str(settings.BASE_DIR),            # Local (Windows/Linux/Mac)
    ]
    for p in paths_candidatos:
        if p and os.path.exists(p):
            return p
    # Último recurso: raiz do drive
    return os.path.abspath(os.sep)

def _coletar_mysql():
    """Métricas do MySQL/MariaDB. Não levanta exceção."""
    if connection.vendor != 'mysql':
        return {'conectado': False, 'erro': f'Banco "{connection.vendor}" não suportado'}
    try:
        with connection.cursor() as c:
            t0 = time.perf_counter()
            c.execute('SELECT 1')
            c.fetchone()
            latencia_ms = round((time.perf_counter() - t0) * 1000, 1)

            c.execute(
                "SHOW GLOBAL STATUS WHERE Variable_name IN ("
                "'Threads_connected','Threads_running','Max_used_connections',"
                "'Aborted_connects','Aborted_clients','Connections','Questions',"
                "'Slow_queries','Uptime','Innodb_buffer_pool_reads',"
                "'Innodb_buffer_pool_read_requests')"
            )
            st = dict(c.fetchall())

            c.execute(
                "SHOW GLOBAL VARIABLES WHERE Variable_name IN "
                "('max_connections','wait_timeout','version')"
            )
            var = dict(c.fetchall())

            # Consulta cara em bancos grandes: cache de 60s
            tamanho = cache.get('mon:mysql_tamanho')
            if tamanho is None:
                c.execute(
                    "SELECT COALESCE(SUM(data_length + index_length), 0) "
                    "FROM information_schema.tables WHERE table_schema = DATABASE()"
                )
                tamanho = float(c.fetchone()[0] or 0)
                cache.set('mon:mysql_tamanho', tamanho, 60)

            lentas = []
            try:
                c.execute(
                    "SELECT ID, USER, TIME, COALESCE(STATE,''), LEFT(COALESCE(INFO,''), 80) "
                    "FROM information_schema.processlist "
                    "WHERE COMMAND <> 'Sleep' AND ID <> CONNECTION_ID() AND TIME >= 1 "
                    "ORDER BY TIME DESC LIMIT 5"
                )
                lentas = [
                    {'id': r[0], 'user': r[1], 'tempo': r[2], 'estado': r[3], 'sql': r[4]}
                    for r in c.fetchall()
                ]
            except Exception:
                pass  # sem privilégio PROCESS: mostra só as próprias

        n = lambda k: int(float(st.get(k, 0) or 0))
        max_conn = int(var.get('max_connections', 0) or 0)

        # QPS = variação de Questions entre duas chamadas
        agora, q = time.time(), n('Questions')
        ant = _mysql_anterior.get('v')
        qps = None
        if ant and agora > ant[0]:
            qps = round(max(q - ant[1], 0) / (agora - ant[0]), 1)
        _mysql_anterior['v'] = (agora, q)

        reqs = n('Innodb_buffer_pool_read_requests')
        hit = round((1 - n('Innodb_buffer_pool_reads') / reqs) * 100, 2) if reqs else None

        return {
            'conectado': True,
            'versao': var.get('version'),
            'latencia_ms': latencia_ms,
            'conexoes': n('Threads_connected'),
            'max_conexoes': max_conn,
            'conexoes_percent': round(n('Threads_connected') / max_conn * 100, 1) if max_conn else 0,
            'pico_conexoes': n('Max_used_connections'),
            'threads_ativas': n('Threads_running'),
            'qps': qps,
            'buffer_hit': hit,
            'tamanho_mb': round(tamanho / 1024 / 1024, 1),
            'conexoes_abortadas': n('Aborted_connects'),
            'clientes_abortados': n('Aborted_clients'),
            'queries_lentas': n('Slow_queries'),
            'wait_timeout': var.get('wait_timeout'),
            'uptime_horas': round(n('Uptime') / 3600, 1),
            'consultas_lentas': lentas,
        }
    except Exception as e:
        return {'conectado': False, 'erro': str(e)[:150]}


def _coletar_celery():
    """Fila (no MESMO broker do Celery) + workers online. Não levanta exceção."""
    broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
    fila_nome = getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', 'celery')

    fila, erro = None, None
    try:
        r = redis.from_url(broker_url, socket_connect_timeout=2)
        fila = r.llen(fila_nome)
    except Exception as e:
        erro = str(e)[:100]

    # inspect() bloqueia até o timeout: cache de 15s para não pesar no polling de 5s
    workers = cache.get('mon:celery_workers')
    if workers is None:
        try:
            from celery import current_app
            insp = current_app.control.inspect(timeout=1.0)
            ping = insp.ping() or {}
            ativas = insp.active() or {}
            workers = {
                'online': len(ping),
                'ativas': sum(len(v) for v in ativas.values()),
                'nomes': sorted(ping),
            }
        except Exception as e:
            workers = {'online': 0, 'ativas': 0, 'nomes': [], 'erro': str(e)[:100]}
        cache.set('mon:celery_workers', workers, 15)

    return {
        'fila_celery': fila,          # None = broker inacessível
        'fila_nome': fila_nome,
        'workers_online': workers['online'],
        'tarefas_ativas': workers['ativas'],
        'workers': workers['nomes'],
        'erro': erro or workers.get('erro'),
    }

@login_required
@user_passes_test(pode_monitorar)
@never_cache
def monitoramento_view(request):
    """Página HTML do dashboard de monitoramento."""
    return render(request, 'monitoramento/dashboard.html')


@login_required
@user_passes_test(pode_monitorar)
@never_cache
def monitoramento_api(request):
    """Endpoint JSON com métricas em tempo real."""

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    try:
        load_avg = os.getloadavg()  # Não funciona em Windows
    except (OSError, AttributeError):
        # Windows: usa CPU médio como aproximação
        load_avg = (cpu_percent / 100 * cpu_count, 0, 0)

    # Memória
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disco — path multi-plataforma
    try:
        disco_path = _get_disco_path()
        disco = shutil.disk_usage(disco_path)
        disco_data = {
            'path': disco_path,
            'total_gb': round(disco.total / 1024**3, 2),
            'usado_gb': round(disco.used / 1024**3, 2),
            'livre_gb': round(disco.free / 1024**3, 2),
            'percent': round(disco.used / disco.total * 100, 1),
        }
    except Exception as e:
        disco_data = {
            'path': 'erro',
            'total_gb': 0, 'usado_gb': 0, 'livre_gb': 0, 'percent': 0,
            'erro': str(e)[:100],
        }

    # Processos da aplicação
    processos = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
        try:
            cmd_list = p.info['cmdline'] or []
            cmd = ' '.join(cmd_list)
            nome_lower = (p.info['name'] or '').lower()
            cmd_lower = cmd.lower()
            
            # Filtra processos da app
            if any(x in cmd_lower or x in nome_lower for x in [
                'daphne', 'celery', 'redis', 'gunicorn', 'python', 'manage.py'
            ]):
                processos.append({
                    'pid': p.info['pid'],
                    'nome': p.info['name'],
                    'cmd': cmd[:80] if cmd else (p.info['name'] or '-'),
                    'mem_mb': round(p.info['memory_info'].rss / 1024 / 1024, 1),
                    'cpu': p.info['cpu_percent'] or 0,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processos.sort(key=lambda x: x['mem_mb'], reverse=True)
    processos = processos[:15]

    # Redis
    redis_info = {}
    try:
        broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(broker_url, socket_connect_timeout=2)
        info = r.info()
        redis_info = {
            'conectado': True,
            'versao': info.get('redis_version'),
            'mem_usada_mb': round(info.get('used_memory', 0) / 1024 / 1024, 2),
            'clientes': info.get('connected_clients'),
            'uptime_dias': round(info.get('uptime_in_seconds', 0) / 86400, 1),
            'total_keys': sum(
                v.get('keys', 0) for k, v in info.items()
                if k.startswith('db') and isinstance(v, dict)
            ),
        }
    except Exception as e:
        redis_info = {'conectado': False, 'erro': str(e)[:100]}

    # Uptime
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_horas = round((datetime.now() - boot_time).total_seconds() / 3600, 1)
    except Exception:
        uptime_horas = 0

    data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ambiente': 'Windows' if os.name == 'nt' else 'Linux/Unix',
        'cpu': {
            'percent': cpu_percent,
            'cores': cpu_count,
            'load_1min': round(load_avg[0], 2),
            'load_5min': round(load_avg[1], 2),
            'load_15min': round(load_avg[2], 2),
        },
        'memoria': {
            'total_mb': round(mem.total / 1024 / 1024, 0),
            'usada_mb': round(mem.used / 1024 / 1024, 0),
            'livre_mb': round(mem.available / 1024 / 1024, 0),
            'percent': mem.percent,
        },
        'swap': {
            'total_mb': round(swap.total / 1024 / 1024, 0),
            'usada_mb': round(swap.used / 1024 / 1024, 0),
            'percent': swap.percent,
        },
        'disco': disco_data,
        'processos': processos,
        'redis': redis_info,
        'celery': _coletar_celery(),
        'mysql': _coletar_mysql(),
        'uptime_horas': uptime_horas,
    }

    return JsonResponse(data)
