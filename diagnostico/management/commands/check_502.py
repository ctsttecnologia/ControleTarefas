# diagnostico/management/commands/check_502.py
import os
import sys
import requests
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
import logging

class Command(BaseCommand):
    help = 'Diagnóstica erros 502 em hospedagem elástica'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--monitorar',
            action='store_true',
            help='Monitora continuamente por erros 502'
        )
        
        parser.add_argument(
            '--url',
            type=str,
            help='URL específica para testar',
            default=None
        )
    
    def handle(self, *args, **options):
        self.stdout.write("=== DIAGNÓSTICO 502 - HOSPEDAGEM ELÁSTICA ===")
        
        if options['monitorar']:
            self.monitorar_continuamente(options.get('url'))
        else:
            self.diagnostico_completo(options.get('url'))
    
    def diagnostico_completo(self, url_custom=None):
        """Diagnóstico completo do sistema"""
        
        # 1. Informações do ambiente
        self.verificar_ambiente()
        
        # 2. Verificar banco de dados
        self.verificar_banco()
        
        # 3. Verificar memória e recursos (limitado)
        self.verificar_recursos()
        
        # 4. Testar URLs
        self.testar_urls(url_custom)
        
        # 5. Verificar middlewares e apps
        self.verificar_configuracao()
    
    def verificar_ambiente(self):
        self.stdout.write("\n1. INFORMAÇÕES DO AMBIENTE:")
        self.stdout.write(f"Python: {sys.version}")
        self.stdout.write(f"Django: {settings.DJANGO_VERSION if hasattr(settings, 'DJANGO_VERSION') else 'N/A'}")
        self.stdout.write(f"Debug Mode: {settings.DEBUG}")
        self.stdout.write(f"Timezone: {settings.TIME_ZONE}")
        
        # Verificar variáveis de ambiente importantes
        env_vars = ['DATABASE_URL', 'REDIS_URL', 'STATIC_URL', 'MEDIA_URL']
        for var in env_vars:
            value = os.environ.get(var, 'N/A')
            # Mascarar dados sensíveis
            if 'URL' in var and '://' in str(value):
                value = value.split('://')[0] + '://***MASKED***'
            self.stdout.write(f"{var}: {value}")
    
    def verificar_banco(self):
        self.stdout.write("\n2. VERIFICAÇÃO DE BANCO DE DADOS:")
        
        try:
            # Testar conexão básica
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                resultado = cursor.fetchone()
                
            self.stdout.write("✅ Conexão com banco: OK")
            
            # Verificar configurações do banco
            db_config = settings.DATABASES['default']
            engine = db_config.get('ENGINE', '').split('.')[-1]
            self.stdout.write(f"Engine: {engine}")
            
            # Testar query mais complexa
            cursor.execute("SELECT COUNT(*) FROM django_session")
            sessions = cursor.fetchone()[0]
            self.stdout.write(f"Sessões ativas: {sessions}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro no banco: {e}")
            return False
        
        return True
    
    def verificar_recursos(self):
        self.stdout.write("\n3. VERIFICAÇÃO DE RECURSOS:")
        
        # Verificar uso de memória (aproximado)
        import sys
        import gc
        
        # Coletar estatísticas básicas
        gc.collect()
        objects = len(gc.get_objects())
        self.stdout.write(f"Objetos em memória: {objects}")
        
        # Verificar cache (se configurado)
        if hasattr(settings, 'CACHES'):
            try:
                from django.core.cache import cache
                cache.set('test_502', 'ok', 10)
                result = cache.get('test_502')
                if result:
                    self.stdout.write("✅ Cache: OK")
                else:
                    self.stdout.write("❌ Cache: Falha")
            except Exception as e:
                self.stdout.write(f"❌ Cache: {e}")
    
    def testar_urls(self, url_custom=None):
        self.stdout.write("\n4. TESTANDO URLs:")
        
        # URLs para testar
        urls = []
        
        if url_custom:
            urls.append(url_custom)
        else:
            # URLs padrão baseadas na configuração
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            urls = [
                f"{base_url}/",
                f"{base_url}/admin/",
                f"{base_url}/api/health/" if 'api' in settings.INSTALLED_APPS else None
            ]
            urls = [url for url in urls if url is not None]
        
        for url in urls:
            self.testar_url_individual(url)
    
    def testar_url_individual(self, url):
        """Testa uma URL específica"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=30, allow_redirects=True)
            response_time = time.time() - start_time
            
            status = "✅" if response.status_code < 400 else "❌"
            self.stdout.write(
                f"{status} {url}: {response.status_code} "
                f"({response_time:.2f}s)"
            )
            
            if response.status_code == 502:
                self.stdout.write(f"   🚨 ERROR 502 DETECTADO!")
                self.stdout.write(f"   Headers: {dict(response.headers)}")
            
            elif response_time > 15:
                self.stdout.write(f"   ⚠️  RESPOSTA LENTA: {response_time:.2f}s")
            
        except requests.exceptions.Timeout:
            self.stdout.write(f"❌ {url}: TIMEOUT (>30s)")
        except requests.exceptions.ConnectionError:
            self.stdout.write(f"❌ {url}: ERRO DE CONEXÃO")
        except Exception as e:
            self.stdout.write(f"❌ {url}: {e}")
    
    def verificar_configuracao(self):
        self.stdout.write("\n5. VERIFICAÇÃO DE CONFIGURAÇÃO:")
        
        # Middlewares críticos
        middlewares_criticos = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
        ]
        
        for middleware in middlewares_criticos:
            if middleware in settings.MIDDLEWARE:
                self.stdout.write(f"✅ {middleware}")
            else:
                self.stdout.write(f"❌ {middleware} - AUSENTE!")
        
        # Apps instalados
        apps_importantes = ['django.contrib.admin', 'django.contrib.auth']
        for app in apps_importantes:
            if app in settings.INSTALLED_APPS:
                self.stdout.write(f"✅ {app}")
    
    def monitorar_continuamente(self, url_custom=None):
        """Monitora continuamente por erros 502"""
        
        url = url_custom or getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        self.stdout.write(f"Monitorando {url} por erros 502...")
        self.stdout.write("Pressione Ctrl+C para parar")
        
        contador_502 = 0
        ultimo_status = None
        
        try:
            while True:
                try:
                    response = requests.get(url, timeout=15)
                    status = response.status_code
                    agora = datetime.now().strftime('%H:%M:%S')
                    
                    if status == 502:
                        contador_502 += 1
                        self.stdout.write(
                            f"🚨 [{agora}] ERROR 502 #{contador_502}"
                        )
                    elif ultimo_status == 502 and status == 200:
                        self.stdout.write(
                            f"✅ [{agora}] RECUPERADO! Status: {status}"
                        )
                    elif status != ultimo_status:
                        self.stdout.write(
                            f"ℹ️  [{agora}] Mudança de status: {ultimo_status} → {status}"
                        )
                    
                    ultimo_status = status
                    
                except Exception as e:
                    agora = datetime.now().strftime('%H:%M:%S')
                    self.stdout.write(f"❌ [{agora}] Erro: {e}")
                
                time.sleep(10)  # Verificar a cada 10 segundos
                
        except KeyboardInterrupt:
            self.stdout.write("\nMonitoramento interrompido.")
            self.stdout.write(f"Total de erros 502 detectados: {contador_502}")

