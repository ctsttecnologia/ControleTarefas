# diagnostico_502.py
import os
import subprocess
import datetime
import requests
import psutil
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Diagnóstica problemas 502 em produção'
    
    def handle(self, *args, **options):
        print("=== DIAGNÓSTICO ERROR 502 - DJANGO ===")
        print(f"Timestamp: {datetime.datetime.now()}")
        print("-" * 50)
        
        # 1. Verificar processos do Gunicorn/uWSGI
        self.verificar_processos_app()
        
        # 2. Verificar uso de recursos
        self.verificar_recursos_sistema()
        
        # 3. Verificar conectividade de banco
        self.verificar_banco_dados()
        
        # 4. Verificar logs recentes
        self.verificar_logs_recentes()
        
        # 5. Testar endpoints internamente
        self.testar_endpoints()
    
    def verificar_processos_app(self):
        print("\n1. VERIFICANDO PROCESSOS DA APLICAÇÃO:")
        
        # Verificar Gunicorn
        try:
            result = subprocess.run(['pgrep', '-f', 'gunicorn'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Gunicorn rodando - PIDs: {result.stdout.strip()}")
                
                # Verificar quantos workers
                workers = result.stdout.strip().split('\n')
                print(f"   Workers ativos: {len(workers)}")
            else:
                print("❌ Gunicorn NÃO está rodando!")
                
        except Exception as e:
            print(f"❌ Erro ao verificar Gunicorn: {e}")
    
    def verificar_recursos_sistema(self):
        print("\n2. VERIFICANDO RECURSOS DO SISTEMA:")
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"CPU: {cpu_percent}%")
        
        # Memória
        memory = psutil.virtual_memory()
        print(f"Memória: {memory.percent}% usada ({memory.used/1024/1024:.1f}MB/{memory.total/1024/1024:.1f}MB)")
        
        # Disco
        disk = psutil.disk_usage('/')
        print(f"Disco: {disk.percent}% usado")
        
        # Conexões de rede
        connections = len(psutil.net_connections())
        print(f"Conexões de rede ativas: {connections}")
    
    def verificar_banco_dados(self):
        print("\n3. VERIFICANDO BANCO DE DADOS:")
        
        try:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            print("✅ Conexão com banco OK")
            
            # Verificar pool de conexões
            if hasattr(settings, 'DATABASES'):
                db_config = settings.DATABASES['default']
                print(f"   Engine: {db_config.get('ENGINE', 'N/A')}")
                print(f"   Host: {db_config.get('HOST', 'localhost')}")
                
        except Exception as e:
            print(f"❌ Erro no banco: {e}")
    
    def verificar_logs_recentes(self):
        print("\n4. VERIFICANDO LOGS RECENTES (últimos 50 erros):")
        
        log_paths = [
            '/var/log/nginx/error.log',
            '/var/log/gunicorn/error.log',
            'logs/django.log'
        ]
        
        for log_path in log_paths:
            if os.path.exists(log_path):
                print(f"\n--- {log_path} ---")
                try:
                    result = subprocess.run([
                        'tail', '-n', '10', log_path
                    ], capture_output=True, text=True)
                    
                    if result.stdout:
                        lines = result.stdout.split('\n')
                        for line in lines[-5:]:  # Últimas 5 linhas
                            if line.strip():
                                print(f"   {line}")
                except Exception as e:
                    print(f"   Erro ao ler log: {e}")
    
    def testar_endpoints(self):
        print("\n5. TESTANDO ENDPOINTS INTERNAMENTE:")
        
        endpoints = [
            'http://127.0.0.1:8000/',  # Django direto
            'http://127.0.0.1/',       # Via Nginx
        ]
        
        for url in endpoints:
            try:
                response = requests.get(url, timeout=5)
                print(f"✅ {url}: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ {url}: {e}")
