
# departamento_pessoal/tests.py (Versão Corrigida)

# Em departamento_pessoal/tests.py

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from usuario.models import Filial
from seguranca_trabalho.models import Funcao
from .models import Funcionario, Documento

User = get_user_model()

@classmethod
def setUpTestData(cls):
    # Criar dependências
    cls.filial = Filial.objects.create(nome='Matriz')
    cls.funcao = Funcao.objects.create(filial=cls.filial, nome_funcao='Desenvolvedor')
    
    # CORREÇÃO: Removido o campo 'cpf' que não existe no modelo
    cls.funcionario = Funcionario.objects.create(
        filial=cls.filial,
        nome_completo='João da Silva Teste',
        funcao=cls.funcao,
        data_nascimento=date(1990, 1, 1),
        data_admissao=date.today()
    )

    def test_criacao_funcionario(self):
        """Testa se um funcionário é criado com os dados corretos."""
        self.assertEqual(self.funcionario.nome_completo, 'João da Silva Teste')
        self.assertEqual(self.funcionario.funcao.nome_funcao, 'Desenvolvedor')
    
    def test_idade_funcionario(self):
        """Testa o cálculo da idade do funcionário."""
        idade_esperada = date.today().year - 1990
        self.assertEqual(self.funcionario.idade, idade_esperada)

    def test_rg_numero_propriedade(self):
        """Testa a propriedade rg_numero do funcionário."""
        documento_rg = Documento.objects.create(
            funcionario=self.funcionario,
            tipo_documento='RG',
            numero='MG-12.345.678'
        )
        self.assertEqual(self.funcionario.rg_numero, 'MG-12.345.678')

        # Testa quando o funcionário não possui RG
        funcionario_sem_rg = Funcionario.objects.create(
            nome_completo='Maria Oliveira',
            data_nascimento=date(1985, 5, 15),
            funcao=self.funcao,
            data_admissao=date.today()
        )
        self.assertEqual(funcionario_sem_rg.rg_numero, 'N/A')   