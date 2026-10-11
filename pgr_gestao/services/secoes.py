
# pgr_gestao/services/secoes.py
from xml.sax.saxutils import escape
from pgr_gestao.models import PGRSecaoTexto, PGRSecaoTextoPadrao


def esc(valor):
    return escape(str(valor if valor is not None else ""))


class SecaoCache:
    """2 queries por PDF em vez de ~2 por seção."""
    def __init__(self, pgr, nome_empresa=""):
        self.nome = nome_empresa
        self.custom = {s.secao: s for s in PGRSecaoTexto.objects.filter(pgr_documento=pgr)}
        self.padrao = {p.secao: p for p in PGRSecaoTextoPadrao.objects.filter(ativo=True)}

    def texto(self, chave):
        s = self.custom.get(chave)
        if s:
            if not s.incluir_no_pdf:
                return None
            texto = s.conteudo or ""
        else:
            p = self.padrao.get(chave)
            texto = (p.conteudo_padrao or "") if p else ""
        return texto.replace("{empresa}", self.nome) if self.nome else texto

    def titulo(self, chave):
        s = self.custom.get(chave)
        if s and s.titulo_customizado:
            return s.titulo_customizado
        p = self.padrao.get(chave)
        return p.titulo if p else ""

