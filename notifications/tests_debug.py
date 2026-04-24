
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class DebugRoutingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='debug', password='123', email='d@d.com'
        )
        self.client.force_login(self.user)
    
    def test_descobrir_problema(self):
        # 1) URL via reverse
        url_reverse = reverse('notifications:api_contagem')
        print(f"\n{'='*70}")
        print(f"🔍 URL via reverse(): '{url_reverse}'")
        
        # 2) Requisição SEM follow
        r = self.client.get(url_reverse)
        print(f"🔍 Status code: {r.status_code}")
        print(f"🔍 Content-Type: {r.get('Content-Type')}")
        print(f"🔍 Location header: {r.get('Location', 'NENHUM')}")
        
        # 3) URL sem barra final (o caso suspeito)
        r2 = self.client.get('/notifications/api/contagem')
        print(f"\n🔍 URL SEM barra '/notifications/api/contagem':")
        print(f"   Status: {r2.status_code}")
        print(f"   Location: {r2.get('Location', 'NENHUM')}")
        
        # 4) URL com barra final
        r3 = self.client.get('/notifications/api/contagem/')
        print(f"\n🔍 URL COM barra '/notifications/api/contagem/':")
        print(f"   Status: {r3.status_code}")
        print(f"   Content-Type: {r3.get('Content-Type')}")
        print(f"{'='*70}\n")
