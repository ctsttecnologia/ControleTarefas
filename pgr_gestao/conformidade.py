"""Verificação de conformidade do PGR. Serve de apoio e não substitui a análise técnica."""
from django.urls import NoReverseMatch, reverse

from .models import (
    AvaliacaoQuantitativa,
    PlanoAcaoPGR,
    RiscoEPIRecomendado,
    RiscoIdentificado,
    RiscoMedidaControle,
    RiscoTreinamentoNecessario,
)

PRIORITARIAS = ("critico", "muito_grave")
CATEGORIAS_MENSURAVEIS = ("fisico", "quimico", "biologico")  # os demais não têm medição
OK, PARCIAL, NAO = "conforme", "parcial", "nao_conforme"

# estado -> (classe css, rótulo, cor bootstrap, ícone)
ESTADOS = {
    OK: ("conforme", "CONFORME", "success", "bi-check-circle-fill"),
    PARCIAL: ("parcial", "PARCIALMENTE CONFORME", "warning", "bi-exclamation-circle-fill"),
    NAO: ("nao-conforme", "NÃO CONFORME", "danger", "bi-x-circle-fill"),
}
PONTOS = {OK: 1, PARCIAL: 0.5, NAO: 0}


def _estado(ok, parcial=False):
    return OK if ok else (PARCIAL if parcial else NAO)


def _cobertura(alvo, faltam, minimo=NAO):
    """Conforme se nada falta; parcial se parte está coberta; senão `minimo`."""
    if not alvo:
        return NAO
    if not faltam:
        return OK
    return PARCIAL if len(faltam) < len(alvo) else minimo


def _fracao(alvo, faltam):
    return f"{len(alvo) - len(faltam)} de {len(alvo)}"


def _link(user, perm, rotulo, nome, *args):
    """Link só se o usuário tem a permissão e a rota existe."""
    if perm and not user.has_perm(perm):
        return None
    try:
        return {"rotulo": rotulo, "url": reverse(nome, args=args)}
    except NoReverseMatch:
        return None


def _item(codigo, titulo, nr, estado, detalhe, acao="", links=()):
    css, rotulo, cor, icone = ESTADOS[estado]
    return {
        "codigo": codigo, "titulo": titulo, "nr": nr, "estado": estado,
        "css": css, "rotulo": rotulo, "cor": cor, "icone": icone,
        "detalhe": detalhe, "acao": acao, "links": [l for l in links if l],
    }


def verificar(doc, user):
    def L(perm, rotulo, nome, *args):
        return _link(user, perm, rotulo, nome, *args)

    # ---- Dados -----------------------------------------------------------
    riscos = RiscoIdentificado.objects.filter(pgr_documento=doc)
    ids = set(riscos.values_list("id", flat=True))
    prior = set(riscos.filter(classificacao_risco__in=PRIORITARIAS).values_list("id", flat=True))
    prior_mens = set(
        riscos.filter(
            classificacao_risco__in=PRIORITARIAS,
            tipo_risco__categoria__in=CATEGORIAS_MENSURAVEIS,
        ).values_list("id", flat=True)
    )
    alvo = prior or ids
    rot_alvo = "prioritário(s)" if prior else "do inventário"
    tem = bool(ids)

    def por_risco(model):
        return set(
            model.objects.filter(risco_identificado_id__in=ids)
            .values_list("risco_identificado_id", flat=True)
        )

    avaliados = por_risco(AvaliacaoQuantitativa)
    com_plano = por_risco(PlanoAcaoPGR)
    com_medida = por_risco(RiscoMedidaControle)
    com_epi = por_risco(RiscoEPIRecomendado)
    com_trein = por_risco(RiscoTreinamentoNecessario)

    sem_avaliacao = prior_mens - avaliados
    sem_plano = alvo - com_plano
    sem_medida = alvo - com_medida
    sem_epi = alvo - com_epi
    sem_trein = alvo - com_trein

    n_planos = PlanoAcaoPGR.objects.filter(risco_identificado_id__in=ids).count()
    n_ges = doc.grupos_exposicao.filter(ativo=True).count()
    n_crono = doc.cronograma_acoes.count()
    sem_ges = riscos.filter(ges__isnull=True).count()
    tem_resp = doc.responsaveis.exists()
    dias = doc.dias_para_vencimento

    # ---- Links reutilizados ---------------------------------------------
    v_doc = L("pgr_gestao.view_pgrdocumento", "Ver documento", "pgr_gestao:documento_detail", doc.pk)
    e_doc = L("pgr_gestao.change_pgrdocumento", "Editar documento", "pgr_gestao:documento_update", doc.pk)
    v_riscos = L("pgr_gestao.view_riscoidentificado", "Ver riscos", "pgr_gestao:risco_list")
    n_risco = L("pgr_gestao.add_riscoidentificado", "Cadastrar risco", "pgr_gestao:risco_create")
    v_planos = L("pgr_gestao.view_planoacaopgr", "Ver planos de ação", "pgr_gestao:plano_acao_list")
    n_plano = L("pgr_gestao.add_planoacaopgr", "Criar plano de ação", "pgr_gestao:plano_acao_create")
    v_ges = L("pgr_gestao.view_gesgrupoexposicao", "Ver GES", "pgr_gestao:ges_list")
    n_ges_l = L("pgr_gestao.add_gesgrupoexposicao", "Cadastrar GES", "pgr_gestao:ges_create")
    x_excel = L("pgr_gestao.view_riscoidentificado", "Exportar Excel",
                "pgr_gestao:exportar_inventario_excel", doc.pk)

    # ---- Estados ---------------------------------------------------------
    est_aval = _estado(tem and not sem_avaliacao, tem)
    est_inventario = _estado(tem and not sem_ges, tem)
    if dias is None:
        est_rev, txt_rev = NAO, "Vencimento não informado."
    else:
        est_rev = _estado(dias > 30, dias >= 0)
        txt_rev = f"Vence em {dias} dia(s)." if dias >= 0 else f"Vencido há {-dias} dia(s)."

    secoes = [
        {"titulo": "1. Gerenciamento de Riscos Ocupacionais (GRO)", "nr": "NR-01, item 1.5",
         "icone": "bi-gear", "itens": [
            _item("1.1", "PGR implementado", "NR-01, item 1.5.3.1",
                  _estado(doc.status in ("vigente", "em_revisao")),
                  f"Situação do documento: {doc.get_status_display()}.",
                  "Atualizar a situação do documento para vigente.", [v_doc, e_doc]),
            _item("1.2", "Identificação de perigos e avaliação de riscos", "NR-01, item 1.5.4.3",
                  est_aval,
                  f"{len(ids)} risco(s) no inventário; {len(sem_avaliacao)} de {len(prior_mens)} "
                  "crítico(s)/muito grave(s) mensurável(is) sem avaliação quantitativa.",
                  "Cadastrar os riscos e avaliar os agentes físicos, químicos e biológicos críticos.",
                  [v_riscos, n_risco]),
            _item("1.3", "Grupos de exposição similar (GES)", "NR-01, item 1.5.5.1",
                  _estado(n_ges > 0), f"{n_ges} GES ativo(s).",
                  "Definir os GES dos trabalhadores.", [v_ges, n_ges_l]),
            _item("1.4", "Plano de ação para os riscos", "NR-01, item 1.5.4.1.1",
                  _cobertura(alvo, sem_plano),
                  f"{n_planos} plano(s); {_fracao(alvo, sem_plano)} risco(s) {rot_alvo} com plano.",
                  "Criar plano com prazo para cada risco prioritário.", [v_planos, n_plano]),
        ]},
        {"titulo": "2. Medidas de prevenção", "nr": "NR-01, item 1.4", "icone": "bi-shield-check", "itens": [
            _item("2.1", "Hierarquia das medidas de prevenção", "NR-01, item 1.4.1",
                  _cobertura(alvo, sem_medida),
                  f"{_fracao(alvo, sem_medida)} risco(s) {rot_alvo} com medida de controle.",
                  "Registrar medidas de controle, da eliminação ao EPI.", [v_riscos]),
            _item("2.2", "EPI especificado quando necessário", "NR-01, item 1.4.1 (EPI)",
                  _cobertura(alvo, sem_epi, minimo=PARCIAL),
                  f"{_fracao(alvo, sem_epi)} risco(s) {rot_alvo} com EPI recomendado.",
                  "Especificar EPI para os riscos residuais (EPI é o último recurso).",
                  [L(None, "Catálogo de EPIs", "seguranca_trabalho:equipamento_list"),
                   L(None, "Matriz de EPIs", "seguranca_trabalho:controle_epi_por_funcao")]),
        ]},
        {"titulo": "3. Capacitação e treinamento", "nr": "NR-01, item 1.7", "icone": "bi-mortarboard", "itens": [
            _item("3.1", "Capacitações previstas", "NR-01, item 1.7.1",
                  _cobertura(alvo, sem_trein),
                  f"{_fracao(alvo, sem_trein)} risco(s) {rot_alvo} com treinamento vinculado.",
                  "Vincular as capacitações exigidas aos riscos.",
                  [L(None, "Treinamentos", "treinamentos:treinamento_list"),
                   L(None, "Criar treinamento", "treinamentos:criar_treinamento")]),
        ]},
        {"titulo": "4. Documentação e registros", "nr": "NR-01, item 1.6", "icone": "bi-folder2-open", "itens": [
            _item("4.1", "Inventário de riscos ocupacionais", "NR-01, item 1.5.4.3",
                  est_inventario, f"{len(ids)} risco(s) no inventário; {sem_ges} sem GES.",
                  "Vincular cada risco a um GES.", [v_riscos, x_excel]),
            _item("4.2", "Responsável pela elaboração", "NR-01, item 1.5.7.1.7",
                  _estado(tem_resp),
                  "Responsável identificado." if tem_resp else "Nenhum responsável cadastrado.",
                  "Cadastrar o responsável técnico no documento.", [v_doc, e_doc]),
            _item("4.3", "Revisão periódica", "NR-01, item 1.5.4.6",
                  est_rev, txt_rev, "Revisar o PGR antes do vencimento.", [e_doc]),
        ]},
        {"titulo": "5. Cronograma de ações", "nr": "NR-01, item 1.5.7.1.6", "icone": "bi-calendar-event", "itens": [
            _item("5.1", "Cronograma das ações preventivas", "NR-01, item 1.5.7.1.6",
                  _estado(n_crono > 0), f"{n_crono} ação(ões) no cronograma.",
                  "Elaborar o cronograma anual de ações.", [v_doc]),
        ]},
    ]

    # ---- Totais ------------------------------------------------------------
    todos = [i for s in secoes for i in s["itens"]]
    for s in secoes:
        s["percentual"] = round(sum(PONTOS[i["estado"]] for i in s["itens"]) / len(s["itens"]) * 100)

    total = len(todos)
    return {
        "secoes": secoes,
        "pendencias": [i for i in todos if i["estado"] != OK],
        "total_itens": total,
        "itens_conformes": sum(i["estado"] == OK for i in todos),
        "itens_parciais": sum(i["estado"] == PARCIAL for i in todos),
        "itens_nao_conformes": sum(i["estado"] == NAO for i in todos),
        "percentual_conformidade": round(sum(PONTOS[i["estado"]] for i in todos) / total * 100),
        "grafico": {
            "labels": ["GRO", "Medidas de Prevenção", "Capacitação", "Documentação", "Cronograma"],
            "dados": [s["percentual"] for s in secoes],
        },
    }
