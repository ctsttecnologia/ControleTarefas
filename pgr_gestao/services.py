
"""
Services do PGR - Lógica de negócio
"""
from pgr_gestao.models import PGRSecaoTexto, PGRSecaoTextoPadrao


def inicializar_secoes_pgr(pgr_documento):
    """
    Cria as seções de texto de um documento PGR a partir dos textos padrão.
    Só cria seções que ainda não existem no documento.
    Retorna o número de seções criadas.
    """
    textos_padrao = PGRSecaoTextoPadrao.objects.filter(ativo=True)
    criadas = 0
    
    for idx, tp in enumerate(textos_padrao):
        secao, created = PGRSecaoTexto.objects.get_or_create(
            pgr_documento=pgr_documento,
            secao=tp.secao,
            defaults={
                'titulo_customizado': '',
                'conteudo': tp.conteudo_padrao,
                'ordem': (idx + 1) * 10,
                'incluir_no_pdf': True,
            }
        )
        if created:
            criadas += 1
    
    return criadas


def get_texto_secao(pgr_documento, secao_key, nome_empresa=''):
    """
    Retorna o texto de uma seção do PGR.
    Prioridade:
    1. Texto customizado do documento (PGRSecaoTexto)
    2. Texto padrão global (PGRSecaoTextoPadrao)
    3. String vazia
    
    Substitui {empresa} pelo nome da empresa.
    """
    # Tenta buscar texto customizado do documento
    try:
        secao = PGRSecaoTexto.objects.get(
            pgr_documento=pgr_documento,
            secao=secao_key
        )
        if not secao.incluir_no_pdf:
            return None  # Seção desativada
        texto = secao.conteudo or ''
    except PGRSecaoTexto.DoesNotExist:
        # Fallback: texto padrão global
        try:
            padrao = PGRSecaoTextoPadrao.objects.get(secao=secao_key, ativo=True)
            texto = padrao.conteudo_padrao or ''
        except PGRSecaoTextoPadrao.DoesNotExist:
            return ''
    
    # Substitui variáveis
    if nome_empresa:
        texto = texto.replace('{empresa}', nome_empresa)
    
    return texto


def get_titulo_secao(pgr_documento, secao_key):
    """
    Retorna o título de uma seção.
    Prioridade: titulo_customizado > titulo padrão
    """
    try:
        secao = PGRSecaoTexto.objects.get(
            pgr_documento=pgr_documento,
            secao=secao_key
        )
        if secao.titulo_customizado:
            return secao.titulo_customizado
    except PGRSecaoTexto.DoesNotExist:
        pass
    
    try:
        padrao = PGRSecaoTextoPadrao.objects.get(secao=secao_key, ativo=True)
        return padrao.titulo
    except PGRSecaoTextoPadrao.DoesNotExist:
        return ''

