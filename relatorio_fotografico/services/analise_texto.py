
# services/analise_texto.py
def _lista(titulo, itens):
    if not itens:
        return ''
    return f"{titulo}\n" + "\n".join(f"- {i}" for i in itens) + "\n\n"

def analise_para_texto(d: dict) -> str:
    if not d:
        return ''
    t = ''
    t += f"RESUMO EXECUTIVO\n{d.get('resumo_executivo','')}\n\n"
    t += f"AVALIAÇÃO GERAL\n{d.get('avaliacao_geral','')}\n\n"
    t += f"CONSISTÊNCIA DOCUMENTAL\n{d.get('consistencia_documental','')}\n\n"
    t += _lista('DIVERGÊNCIAS', d.get('divergencias'))
    t += _lista('PONTOS DE ATENÇÃO', d.get('pontos_atencao'))
    t += _lista('EVIDÊNCIAS AUSENTES', d.get('evidencias_ausentes'))
    t += _lista('RECOMENDAÇÕES', d.get('recomendacoes'))

    fotos = d.get('analise_fotografias') or []
    if fotos:
        t += "ANÁLISE DAS FOTOGRAFIAS\n"
        for f in fotos:
            t += (f"\nFoto {f.get('foto_id')} — Legenda: {f.get('legenda_informada') or 'sem legenda'}\n"
                  f"{f.get('descricao_visual','')}\n"
                  f"Coerência: {f.get('coerencia_legenda','').replace('_',' ')} | "
                  f"Confiança: {f.get('confianca','')}\n")
            for p in f.get('pontos_atencao') or []:
                t += f"- {p}\n"
        t += "\n"

    t += _lista('LIMITAÇÕES DA ANÁLISE', d.get('limitacoes_analise'))
    if d.get('revisao_humana_obrigatoria'):
        t += "⚠ Revisão humana obrigatória.\n"
    return t.strip()

