
# pgr_gestao/services/risco.py  — FONTE ÚNICA (Tabelas 4, 5 e 8)
SEVERIDADE = {
    (1, 1): "A", (1, 2): "A", (1, 3): "A", (1, 4): "B", (1, 5): "B",
    (2, 1): "A", (2, 2): "B", (2, 3): "B", (2, 4): "C", (2, 5): "D",
    (3, 1): "A", (3, 2): "B", (3, 3): "C", (3, 4): "D", (3, 5): "D",
    (4, 1): "B", (4, 2): "C", (4, 3): "D", (4, 4): "E", (4, 5): "E",
    (5, 1): "B", (5, 2): "D", (5, 3): "D", (5, 4): "E", (5, 5): "E",
}
CLASSIFICACAO = {
    ("A", 1): "negligenciavel", ("A", 2): "negligenciavel", ("A", 3): "negligenciavel",
    ("A", 4): "marginal", ("A", 5): "marginal",
    ("B", 1): "negligenciavel", ("B", 2): "negligenciavel", ("B", 3): "marginal",
    ("B", 4): "moderado", ("B", 5): "moderado",
    ("C", 1): "negligenciavel", ("C", 2): "marginal", ("C", 3): "moderado",
    ("C", 4): "moderado", ("C", 5): "muito_grave",
    ("D", 1): "marginal", ("D", 2): "moderado", ("D", 3): "moderado",
    ("D", 4): "muito_grave", ("D", 5): "muito_grave",
    ("E", 1): "marginal", ("E", 2): "moderado", ("E", 3): "muito_grave",
    ("E", 4): "muito_grave", ("E", 5): "critico",
}
PRIORIDADE = {"critico": "critica", "muito_grave": "critica",
              "moderado": "alta", "marginal": "media", "negligenciavel": "baixa"}
PRAZO_DIAS = {"critico": 15, "muito_grave": 30, "moderado": 90}  # default 180


def aplicar_classificacao(risco):
    """Calcula S (de G×E), classificação (S×P) e prioridade. Sem lado-efeito de I/O."""
    if risco.gravidade_g and risco.exposicao_e:
        risco.severidade_s = SEVERIDADE.get((risco.gravidade_g, risco.exposicao_e), risco.severidade_s)
    if risco.severidade_s and risco.probabilidade_p:
        c = CLASSIFICACAO.get((risco.severidade_s, risco.probabilidade_p), "moderado")
        risco.classificacao_risco = c
        risco.prioridade_acao = PRIORIDADE[c]

