# health_monitor.py
import time
import requests
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    filename='/var/log/django/health_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HealthMonitor:
    def __init__(self, urls, interval=30):
        self.urls = urls
        self.interval = interval
        self.status_anterior = {}
    
    def verificar_url(self, url):
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            response_time = time.time() - start_time
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'erro': None
            }
        except Exception as e:
            return {
                'status_code': None,
                'response_time': None,
                'erro': str(e)
            }
    
    def monitorar(self):
        print(f"Iniciando monitoramento às {datetime.now()}")
        
        while True:
            for url in self.urls:
                resultado = self.verificar_url(url)
                
                # Detectar mudanças de status
                status_atual = resultado['status_code']
                status_prev = self.status_anterior.get(url)
                
                if status_atual == 502:
                    logging.error(f"ERROR 502 detectado em {url}")
                    print(f"🚨 ERROR 502: {url} - {datetime.now()}")
                    
                elif status_prev == 502 and status_atual == 200:
                    logging.info(f"Recuperação de 502 em {url}")
                    print(f"✅ RECUPERADO: {url} - {datetime.now()}")
                
                elif status_atual is None:
                    logging.error(f"Falha de conexão em {url}: {resultado['erro']}")
                    print(f"❌ CONEXÃO: {url} - {resultado['erro']}")
                
                self.status_anterior[url] = status_atual
            
            time.sleep(self.interval)

# Uso do monitor
if __name__ == "__main__":
    urls_para_monitorar = [
        'https://seu-site.com',
        'https://seu-site.com/api/health',
        'https://seu-site.com/admin/'
    ]
    
    monitor = HealthMonitor(urls_para_monitorar, interval=15)
    monitor.monitorar()
