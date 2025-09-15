import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _

# =============================================================================
# == VALIDADORES DE DOCUMENTOS BRASILEIROS
# =============================================================================

def validate_cpf(value):
    """
    Valida um CPF brasileiro. Verifica o formato, dígitos repetidos e os dígitos verificadores.
    Levanta um ValidationError se o CPF for inválido.
    """
    cpf = ''.join(re.findall(r'\d', str(value)))

    if not cpf or len(cpf) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.", code='invalid_cpf')

    if cpf in [s * 11 for s in "0123456789"]:
        raise ValidationError("CPF inválido (todos os dígitos são iguais).", code='invalid_cpf')

    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = 11 - (soma % 11)
    digito_verificador_1 = resto if resto < 10 else 0
    if digito_verificador_1 != int(cpf[9]):
        raise ValidationError("CPF inválido (dígito verificador 1 incorreto).", code='invalid_cpf')

    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = 11 - (soma % 11)
    digito_verificador_2 = resto if resto < 10 else 0
    if digito_verificador_2 != int(cpf[10]):
        raise ValidationError("CPF inválido (dígito verificador 2 incorreto).", code='invalid_cpf')


def validate_pis(value):
    """
    Valida um PIS/PASEP/NIT. Verifica o formato e o dígito verificador.
    Levanta um ValidationError se for inválido.
    """
    pis = ''.join(re.findall(r'\d', str(value)))

    if not pis or len(pis) != 11:
        raise ValidationError("PIS/PASEP/NIT deve conter 11 dígitos.", code='invalid_pis')

    # Validação do dígito verificador
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(pis[i]) * pesos[i] for i in range(10))
    resto = soma % 11
    digito_verificador = 0 if resto < 2 else 11 - resto

    if digito_verificador != int(pis[10]):
        raise ValidationError("PIS/PASEP/NIT inválido (dígito verificador incorreto).", code='invalid_pis')


def validate_cnpj(value):
    """
    Valida um CNPJ brasileiro. Verifica o formato, dígitos repetidos e os dígitos verificadores.
    Levanta um ValidationError se o CNPJ for inválido.
    """
    cnpj = ''.join(re.findall(r'\d', str(value)))

    if not cnpj or len(cnpj) != 14:
        raise ValidationError("CNPJ deve conter 14 dígitos.", code='invalid_cnpj')

    if cnpj in [s * 14 for s in "0123456789"]:
        raise ValidationError("CNPJ inválido (todos os dígitos são iguais).", code='invalid_cnpj')

    # Validação do primeiro dígito verificador
    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos_1[i] for i in range(12))
    resto = soma % 11
    digito_verificador_1 = 0 if resto < 2 else 11 - resto
    if digito_verificador_1 != int(cnpj[12]):
        raise ValidationError("CNPJ inválido (dígito verificador 1 incorreto).", code='invalid_cnpj')

    # Validação do segundo dígito verificador
    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos_2[i] for i in range(13))
    resto = soma % 11
    digito_verificador_2 = 0 if resto < 2 else 11 - resto
    if digito_verificador_2 != int(cnpj[13]):
        raise ValidationError("CNPJ inválido (dígito verificador 2 incorreto).", code='invalid_cnpj')


# =============================================================================
# == VALIDADORES DE CONTATO
# =============================================================================

validate_telefone = RegexValidator(
    regex=r'^\(\d{2}\) \d{4,5}-\d{4}$',
    message=_("O número de telefone deve estar no formato (00) 0000-0000 ou (00) 00000-0000.")
)

validate_email = EmailValidator(
    message=_('Informe um endereço de e-mail válido.')
)
