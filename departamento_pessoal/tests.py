
# tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from .models import Funcionarios, Admissao, Documentos

class FuncionarioViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        
        # Adiciona permissões
        add_perm = Permission.objects.get(codename='add_funcionarios')
        self.user.user_permissions.add(add_perm)
        self.client.login(username='testuser', password='12345')
        
        # Cria dados de teste
        self.documento = Documentos.objects.create(
            cpf='12345678909',
            pis='12345678901',
            ctps='12345',
            serie='123456',
            rg='1234567'
        )
        
        self.funcionario = Funcionarios.objects.create(
            nome='João Silva',
            data_nascimento='1990-01-01',
            telefone='11999999999',
            email='joao@test.com',
            sexo='M',
            estatus=1,
            documentos=self.documento
        )

    def test_cadastrar_funcionario_view(self):
        response = self.client.get(reverse('departamento_pessoal:cadastrar_funcionario'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'departamento_pessoal/cadastrar_funcionario.html')
        
        data = {
            'nome': 'Maria Souza',
            'data_nascimento': '1995-05-15',
            'telefone': '11988888888',
            'email': 'maria@test.com',
            'sexo': 'F',
            'estatus': 1
        }
        
        response = self.client.post(reverse('departamento_pessoal:cadastrar_funcionario'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Funcionarios.objects.filter(email='maria@test.com').exists())

    def test_detalhes_funcionario_view(self):
        response = self.client.get(reverse('departamento_pessoal:detalhes_funcionario', args=[self.funcionario.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'João Silva')

    # Adicione mais testes para outras views...