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

from core.mixins import MonitoramentoAccessMixin


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

    # Celery (fila)
    try:
        r = redis.from_url('redis://localhost:6379/0', socket_connect_timeout=2)
        celery_info = {'fila_celery': r.llen('celery')}
    except Exception:
        celery_info = {'fila_celery': 'N/A'}

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
        'celery': celery_info,
        'uptime_horas': uptime_horas,
    }

    return JsonResponse(data)
