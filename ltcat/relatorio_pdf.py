"""
Montagem completa do relatório LTCAT em PDF — fiel ao modelo Word oficial.

Cada seção principal inicia SEMPRE no topo de uma nova página.
"""

from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether,
)
from reportlab.lib.units import mm
from reportlab.lib import colors

from .pdf_generator import (
    LTCATPDFGenerator, AZUL_ESCURO, AZUL_MEDIO, AZUL_CLARO,
    CINZA_CLARO, CINZA_MEDIO, CONTENT_WIDTH,
)
from .texto_padrao import (
    get_texto, TEXTOS_LTCAT, TABELA_RUIDO_NR15, TABELA_DEMAIS_AGENTES,
)
from .models import (
    FuncaoAnalisada, ReconhecimentoRisco, AvaliacaoPericulosidade,
    ConclusaoFuncao, RecomendacaoTecnica, RevisaoLTCAT, AnexoLTCAT,
    LTCATDocumentoResponsavel, LTCATSecaoTexto, EmpresaLTCAT,
)


class LTCATRelatorio(LTCATPDFGenerator):
    """Monta o relatório LTCAT completo fiel ao modelo Word."""

    def gerar(self):
        self._capa()
        self._caracterizacao_contratada()
        self._caracterizacao_contratante()
        self._local_prestacao()
        self._responsavel_elaboracao()
        self._secao_01_revisoes()
        self._secao_02_objetivo()
        self._secao_03_condicoes()
        self._secao_04_gfip()
        self._secao_05_ppp()
        self._secao_06_funcoes()
        self._secao_07_riscos()
        self._secao_08_periculosidade()
        self._secao_09_conclusoes()
        self._secao_10_recomendacoes()
        self._secao_11_embasamento()
        self._secao_12_referencias()
        self._secao_13_responsavel_tecnico()
        self._anexos()
        return self.build()

    # ================================================================
    # HELPER — Resolve a empresa contratada (CETEST)
    # ================================================================

    def _get_contratada(self):
        """
        Retorna o objeto EmpresaLTCAT da contratada (CETEST).
        Ordem de busca:
          1. doc.empresa_contratada (FK direta no LTCATDocumento)
          2. self.empresa_ltcat (fallback do __init__ do generator)
          3. Busca automática: EmpresaLTCAT da filial que não seja a contratante
        """
        # 1. FK direta no documento
        contratada = getattr(self.doc, 'empresa_contratada', None)
        if contratada:
            return contratada

        # 2. Fallback do generator (já resolvido no __init__)
        if self.empresa_ltcat:
            return self.empresa_ltcat

        # 3. Última tentativa
        filial_id = getattr(self.doc, 'filial_id', None)
        if filial_id:
            from .models import EmpresaLTCAT
            return EmpresaLTCAT.objects.filter(
                filial_id=filial_id,
                ativo=True,
            ).exclude(
                cliente=self.empresa
            ).first()

        return None


    # ================================================================
    # HELPER — Monta endereço a partir de Logradouro ou campos manuais
    # ================================================================

    def _endereco_de_logradouro(self, log):
        """Extrai dados de endereço de um objeto Logradouro."""
        if not log:
            return {
                'endereco': 'N/I', 'bairro': 'N/I',
                'cidade_uf': 'N/I - N/I', 'cep': 'N/I'
            }

        endereco = self.val(getattr(log, 'endereco', None))
        if getattr(log, 'numero', None):
            endereco += f", nº {log.numero}"
        if getattr(log, 'complemento', None):
            endereco += f" - {log.complemento}"

        cidade = self.val(getattr(log, 'cidade', None))
        estado = self.val(getattr(log, 'estado', None))

        return {
            'endereco': endereco,
            'bairro': self.val(getattr(log, 'bairro', None)),
            'cidade_uf': f"{cidade} - {estado}",
            'cep': self.val(getattr(log, 'cep', None)),
        }

    def _endereco_de_campos(self, obj):
        """Extrai dados de endereço de um objeto com campos manuais."""
        if not obj:
            return {
                'endereco': 'N/I', 'bairro': 'N/I',
                'cidade_uf': 'N/I - N/I', 'cep': 'N/I'
            }

        endereco = self.val(getattr(obj, 'endereco', None))
        if getattr(obj, 'numero', None):
            endereco += f", nº {obj.numero}"
        if getattr(obj, 'complemento', None):
            endereco += f" - {obj.complemento}"

        cidade = self.val(getattr(obj, 'cidade', None))
        estado = self.val(getattr(obj, 'estado', None))

        return {
            'endereco': endereco,
            'bairro': self.val(getattr(obj, 'bairro', None)),
            'cidade_uf': f"{cidade} - {estado}",
            'cep': self.val(getattr(obj, 'cep', None)),
        }

    def _endereco_de_local(self, local):
        """Extrai endereço de um LocalPrestacaoServicoLTCAT (logradouro > campos)."""
        if not local:
            return {
                'endereco': 'N/I', 'bairro': 'N/I',
                'cidade_uf': 'N/I - N/I', 'cep': 'N/I'
            }
        log = getattr(local, 'logradouro', None)
        if log:
            return self._endereco_de_logradouro(log)
        return self._endereco_de_campos(local)

    # ================================================================
    # CAPA
    # ================================================================

    def _capa(self):
        self.sp(50)

        self.p(
            "LTCAT - LAUDO TÉCNICO DAS CONDIÇÕES<br/>AMBIENTAIS DO TRABALHO",
            'capa_titulo'
        )
        self.sp(15)

        # ── EMPRESA = Contratada (CETEST) ──
        contratada = self._get_contratada()
        nome_contratada = contratada.razao_social if contratada else 'N/I'
        self.tabela_capa("EMPRESA", nome_contratada)
        self.sp(8)

        # ── LOCAL DE TRABALHO = Contratante (Cliente) ──
        nome_contratante = self.empresa.razao_social if self.empresa else 'N/I'
        self.tabela_capa("LOCAL DE TRABALHO", nome_contratante)
        self.sp(8)

        # ── Cidade/UF — do local de prestação principal ──
        cidade_uf = ''
        if self.local:
            dados_local = self._endereco_de_local(self.local)
            if dados_local['cidade_uf'] != 'N/I - N/I':
                cidade_uf = dados_local['cidade_uf']

        if not cidade_uf and self.empresa:
            log_cli = getattr(self.empresa, 'logradouro', None)
            if log_cli:
                dados = self._endereco_de_logradouro(log_cli)
                if dados['cidade_uf'] != 'N/I - N/I':
                    cidade_uf = dados['cidade_uf']

        if cidade_uf:
            self.p(cidade_uf, 'capa_valor_branco')

        self.sp(8)

        # ── CRIADO EM ──
        data_elab = ''
        if self.doc.data_elaboracao:
            meses = [
                '', 'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO',
                'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO',
                'NOVEMBRO', 'DEZEMBRO',
            ]
            d = self.doc.data_elaboracao
            data_elab = f"{meses[d.month]}/{d.year}"

        self.tabela_capa("CRIADO EM", data_elab or 'N/I')
        self.sp(10)

        # ── Tabela ELABORAÇÃO / ÚLTIMA REVISÃO / VENCIMENTO ──
        s = self.styles
        data_elab_fmt = (
            self.doc.data_elaboracao.strftime('%d/%m/%Y')
            if self.doc.data_elaboracao else 'N/I'
        )
        data_rev_fmt = (
            self.doc.data_ultima_revisao.strftime('%d/%m/%Y')
            if self.doc.data_ultima_revisao else '---------'
        )
        data_venc_fmt = (
            self.doc.data_vencimento.strftime('%d/%m/%Y')
            if self.doc.data_vencimento else 'Sem vencimento'
        )

        th_capa = s.get('capa_label_branco', s['td_center'])
        td_capa = s.get('capa_valor_branco', s['td_center'])

        t_data = [
            [
                Paragraph("<b>ELABORAÇÃO</b>", th_capa),
                Paragraph("<b>DATA DA ÚLTIMA REVISÃO</b>", th_capa),
                Paragraph("<b>DATA DO VENCIMENTO</b>", th_capa),
            ],
            [
                Paragraph(data_elab_fmt, td_capa),
                Paragraph(data_rev_fmt, td_capa),
                Paragraph(data_venc_fmt, td_capa),
            ],
        ]
        col_w = CONTENT_WIDTH / 3
        t = Table(t_data, colWidths=[col_w, col_w, col_w])
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1.5, colors.white),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.Color(1, 1, 1, alpha=0.5)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.1)),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        self.elements.append(t)

    # ================================================================
    # CARACTERIZAÇÃO DA EMPRESA CONTRATADA (CETEST)
    # ================================================================

    def _caracterizacao_contratada(self):
        self.titulo_secao('', 'CARACTERIZAÇÃO DA EMPRESA CONTRATADA')

        contratada = self._get_contratada()

        if not contratada:
            self.p("Empresa contratada não cadastrada neste documento.")
            return

        # Endereço da contratada (campos manuais do EmpresaLTCAT)
        end = self._endereco_de_campos(contratada)

        # CNAE formatado
        cnae_display = 'N/I'
        if contratada.cnae:
            desc = contratada.descricao_cnae or ''
            cnae_display = f"{contratada.cnae} – {desc}" if desc else contratada.cnae

        self.tabela_campos([
            ('RAZÃO SOCIAL', contratada.razao_social),
            ('CNPJ', self.val(contratada.cnpj)),
            ('CNAE', cnae_display),
            ('GRAU DE RISCO', self.val(
                contratada.grau_risco_texto or contratada.grau_risco
            )),
            ('ATIVIDADE', self.val(contratada.atividade_principal)),
            ('Nº EMPREGADOS', self.val(
                contratada.numero_empregados_texto
                or str(contratada.numero_empregados or '')
            )),
            ('JORNADA', self.val(contratada.jornada_trabalho)),
            ('ENDEREÇO', end['endereco']),
            ('BAIRRO', end['bairro']),
            ('CIDADE/UF', end['cidade_uf']),
            ('CEP', end['cep']),
            ('TELEFONE', self.val(getattr(contratada, 'telefone', None))),
        ])

    # ================================================================
    # CARACTERIZAÇÃO DA EMPRESA CONTRATANTE (Cliente)
    # ================================================================

    def _caracterizacao_contratante(self):
        self.titulo_secao('', 'CARACTERIZAÇÃO DA EMPRESA CONTRATANTE')

        cliente = self.empresa

        if not cliente:
            self.p("Empresa contratante não cadastrada.")
            return

        # Endereço via Logradouro FK do Cliente
        log = getattr(cliente, 'logradouro', None)
        end = self._endereco_de_logradouro(log)

        self.tabela_campos([
            ('RAZÃO SOCIAL', cliente.razao_social),
            ('CNPJ', self.val(getattr(cliente, 'cnpj', None))),
            ('CONTRATO', self.val(getattr(cliente, 'contrato', None))),
            ('ENDEREÇO', end['endereco']),
            ('BAIRRO', end['bairro']),
            ('CIDADE/UF', end['cidade_uf']),
            ('CEP', end['cep']),
            ('TELEFONE', self.val(getattr(cliente, 'telefone', None))),
            ('E-MAIL', self.val(getattr(cliente, 'email', None))),
        ])

    # ================================================================
    # LOCAL DA PRESTAÇÃO DE SERVIÇOS
    # ================================================================

    def _local_prestacao(self):
        """Renderiza TODOS os locais vinculados ao documento."""
        self.titulo_secao('', 'LOCAL DA PRESTAÇÃO DE SERVIÇOS')

        # Busca todos os locais vinculados via M2M intermediária
        vinculos = self.doc.documento_locais.select_related(
            'local_prestacao', 'local_prestacao__logradouro'
        ).order_by('-principal', 'ordem')

        if vinculos.exists():
            total = vinculos.count()

            for i, vinculo in enumerate(vinculos):
                local = vinculo.local_prestacao
                flag = ' ★' if vinculo.principal else ''

                # Se há mais de 1 local, mostra subtítulo
                if total > 1:
                    self.subtitulo(f"Local {i + 1} de {total}: {local.nome_local}{flag}")

                # Monta endereço
                end = self._endereco_de_local(local)

                campos = [
                    ('RAZÃO SOCIAL', self.val(
                        local.razao_social or getattr(self.doc.empresa, 'razao_social', '')
                    )),
                    ('CNPJ', self.val(local.cnpj)),
                    ('ENDEREÇO', end.get('endereco', '')),
                    ('BAIRRO', end.get('bairro', '')),
                    ('CIDADE/UF', end.get('cidade_uf', '')),
                    ('CEP', end.get('cep', '')),
                ]

                if local.descricao:
                    campos.append(('DESCRIÇÃO', local.descricao))
                if vinculo.observacoes:
                    campos.append(('OBSERVAÇÕES', vinculo.observacoes))

                self.tabela_campos(campos)

                # Espaço entre locais (exceto o último)
                if i < total - 1:
                    self.sp(8)

        elif self.local:
            # Fallback: campo local_prestacao_principal do documento
            end = self._endereco_de_local(self.local)
            self.tabela_campos([
                ('RAZÃO SOCIAL', self.val(
                    self.local.razao_social or getattr(self.doc.empresa, 'razao_social', '')
                )),
                ('CNPJ', self.val(self.local.cnpj)),
                ('ENDEREÇO', end.get('endereco', '')),
                ('BAIRRO', end.get('bairro', '')),
                ('CIDADE/UF', end.get('cidade_uf', '')),
                ('CEP', end.get('cep', '')),
            ])
        else:
            self.p("Local de prestação de serviços não cadastrado.")


    # ================================================================
    # RESPONSÁVEL PELA ELABORAÇÃO DO LTCAT
    # ================================================================

    def _responsavel_elaboracao(self):
        self.titulo_secao('', 'RESPONSÁVEL PELA ELABORAÇÃO DO LTCAT')

        responsaveis = LTCATDocumentoResponsavel.objects.filter(
            ltcat_documento=self.doc
        ).select_related('profissional')

        if responsaveis.exists():
            for resp in responsaveis:
                prof = resp.profissional
                self.tabela_campos([
                    ('NOME', prof.nome_completo),
                    ('FUNÇÃO', prof.funcao),
                    ('REGISTRO DE CLASSE', prof.registro_classe),
                ])

                # ═══ Assinatura Digital ═══
                if prof.assinatura_imagem and prof.assinatura_imagem.name:
                    try:
                        from reportlab.platypus import Image as RLImage
                        from reportlab.lib.units import mm
                        import os

                        img_path = prof.assinatura_imagem.path
                        if os.path.exists(img_path):
                            # Tamanho da assinatura no PDF
                            img = RLImage(img_path, width=50*mm, height=18*mm)
                            img.hAlign = 'CENTER'
                            self.elements.append(img)

                            # Linha de assinatura
                            from reportlab.platypus import Paragraph
                            self.elements.append(Paragraph(
                                f'<para alignment="center">____________________________<br/>'
                                f'<b>{prof.nome_completo}</b><br/>'
                                f'{prof.funcao}<br/>'
                                f'{prof.registro_classe}</para>',
                                self.styles['td']
                            ))
                    except Exception:
                        pass  # Se falhar, mostra apenas tabela sem imagem

                self.sp(3)
        else:
            self.p("Nenhum responsável cadastrado.")


    # ================================================================
    # 1. CONTROLE DE REVISÃO
    # ================================================================

    def _secao_01_revisoes(self):
        self.titulo_secao('1', 'CONTROLE DE REVISÃO')

        revisoes = RevisaoLTCAT.objects.filter(
            ltcat_documento=self.doc
        ).order_by('numero_revisao')

        headers = ['REVISÃO', 'DESCRIÇÃO', 'REALIZADA']

        if revisoes.exists():
            dados = []
            for rev in revisoes:
                dados.append([
                    f"{rev.numero_revisao:02d}",
                    rev.descricao or '',
                    rev.data_realizada.strftime('%d/%m/%Y') if rev.data_realizada else '',
                ])
        else:
            dados = [[
                '00',
                'Emissão inicial (Elaboração do LTCAT)',
                self.doc.data_elaboracao.strftime('%d/%m/%Y') if self.doc.data_elaboracao else '',
            ]]

        self.tabela(headers, dados, col_widths=[25, 100, 40])

    # ================================================================
    # 2. OBJETIVO
    # ================================================================

    def _secao_02_objetivo(self):
        self.titulo_secao('2', 'OBJETIVO')
        self.p(self._get_texto('objetivo'))

    # ================================================================
    # 3. CONDIÇÕES PRELIMINARES
    # ================================================================

    def _secao_03_condicoes(self):
        self.titulo_secao('3', 'CONDIÇÕES PRELIMINARES')
        self.p(self._get_texto('condicoes_preliminares'))

    # ================================================================
    # 4. CÓDIGOS GFIP
    # ================================================================

    def _secao_04_gfip(self):
        self.titulo_secao('4', 'CÓDIGOS DO SISTEMA SEFIP / GFIP')

        self.p(self._get_texto('codigos_gfip'))
        self.sp(5)

        self.subtitulo("TRABALHO PERMANENTE NÃO OCASIONAL OU INTERMITENTE")
        self.p(self._get_texto('trabalho_permanente'))
        self.sp(5)

        self.subtitulo("AGENTES NOCIVOS CONSTATADOS NO LTCAT")
        self.p(self._get_texto('agentes_nocivos'))

    # ================================================================
    # 5. PPP
    # ================================================================

    def _secao_05_ppp(self):
        self.titulo_secao('5', 'PERFIL PROFISSIOGRÁFICO PREVIDENCIÁRIO - PPP')

        self.p(self._get_texto('ppp_finalidade'))
        self.sp(3)
        self.p(self._get_texto('ppp_impressao'))
        self.sp(3)
        self.p(self._get_texto('ppp_especificacoes'))

    # ================================================================
    # 6. DESCRIÇÃO DAS FUNÇÕES ANALISADAS
    # ================================================================

    def _secao_06_funcoes(self):
        self.titulo_secao('6', 'DESCRIÇÃO DAS FUNÇÕES ANALISADAS')

        funcoes = FuncaoAnalisada.objects.filter(
            ltcat_documento=self.doc, ativo=True
        ).order_by('nome_funcao')

        if not funcoes.exists():
            self.p("Nenhuma função analisada cadastrada.")
            return

        headers = ['FUNÇÃO', 'CBO', 'DESCRIÇÃO']
        dados = []
        for f in funcoes:
            dados.append([
                f.nome_funcao,
                f.cbo,
                f.descricao_atividades or '',
            ])

        self.tabela(headers, dados, col_widths=[40, 20, 105])

    # ================================================================
    # 7. RECONHECIMENTO DOS RISCOS (por GHE)
    # ================================================================

    def _secao_07_riscos(self):
        self.titulo_secao('7', 'RECONHECIMENTO DOS RISCOS')

        funcoes = FuncaoAnalisada.objects.filter(
            ltcat_documento=self.doc, ativo=True
        ).prefetch_related('riscos').order_by('nome_funcao')

        if not funcoes.exists():
            self.p("Nenhuma função/risco cadastrado.")
            return

        for idx, func in enumerate(funcoes):
            if idx > 0:
                self.pb()

            local_nome = self.get_local_nome()
            depto = func.departamento or 'N/I'
            ghe = func.ghe or func.nome_funcao

            self.tabela_campos([
                ('LOCAL', local_nome),
                ('DEPARTAMENTO', depto),
                ('GHE (GRUPO HOMOGÊNEO DE EXPOSIÇÃO)', ghe),
            ])
            self.sp(3)

            self.p("<b>RECONHECIMENTO DOS RISCOS E AVALIAÇÃO DOS AGENTES</b>", 'corpo_bold')
            self.sp(1)

            riscos = func.riscos.all().order_by('tipo_risco', 'agente')

            if not riscos.exists():
                self.p("Nenhum agente de risco identificado para esta função.")
                continue

            headers = [
                'TIPO', 'AGENTE', 'FONTE GERADORA',
                'LIMITE DE\nTOLERÂNCIA', 'RESULTADO DA\nAVALIAÇÃO',
                'EXPOSIÇÃO CONTÍNUA\nOU INTERMITENTE',
            ]
            dados = []
            for r in riscos:
                dados.append([
                    r.get_tipo_risco_display().upper(),
                    r.agente,
                    r.fonte_geradora or '',
                    r.limite_tolerancia or 'NA',
                    r.resultado_avaliacao or 'Qualitativo',
                    r.get_exposicao_display(),
                ])

            self.tabela(headers, dados, col_widths=[20, 30, 35, 22, 25, 33])

    # ================================================================
    # 8. AVALIAÇÃO DAS ATIVIDADES PERICULOSAS
    # ================================================================

    def _secao_08_periculosidade(self):
        self.titulo_secao('8', 'AVALIAÇÃO DAS ATIVIDADES E OPERAÇÕES PERICULOSAS')

        avaliacoes = AvaliacaoPericulosidade.objects.filter(
            ltcat_documento=self.doc
        ).order_by('tipo')

        tipo_chave = {
            'explosivos': 'periculosidade_explosivos',
            'inflamaveis': 'periculosidade_inflamaveis',
            'violencia': 'periculosidade_violencia',
            'eletricidade': 'periculosidade_eletricidade',
            'transito': 'periculosidade_transito',
            'radiacao': 'periculosidade_radiacao',
        }

        if avaliacoes.exists():
            for av in avaliacoes:
                chave = tipo_chave.get(av.tipo)
                if chave:
                    if av.descricao and av.descricao.strip():
                        titulo = av.get_tipo_display()
                        self.p(f"<b>{titulo}</b>")
                        self.p(av.descricao)
                    else:
                        if av.tipo == 'eletricidade':
                            txt = get_texto(chave,
                                            texto_periculosidade_eletricidade=av.descricao or '')
                        else:
                            txt = get_texto(chave)
                        self.p(txt)
                    self.sp(3)

            if self.doc.avaliacao_periculosidade_texto:
                self.sp(3)
                self.p(self.doc.avaliacao_periculosidade_texto)
            else:
                self.sp(3)
                self.p(get_texto('periculosidade_conclusao'))
        else:
            for chave in [
                'periculosidade_explosivos', 'periculosidade_inflamaveis',
                'periculosidade_violencia', 'periculosidade_eletricidade',
                'periculosidade_transito', 'periculosidade_radiacao',
            ]:
                txt = get_texto(chave,
                                texto_periculosidade_eletricidade='N/I')
                self.p(txt)
                self.sp(3)
            self.p(get_texto('periculosidade_conclusao'))

    # ================================================================
    # 9. CONCLUSÕES FINAIS
    # ================================================================

    def _secao_09_conclusoes(self):
        self.titulo_secao('9', 'CONCLUSÕES FINAIS')

        conclusoes = ConclusaoFuncao.objects.filter(
            ltcat_documento=self.doc
        ).select_related('funcao').order_by('funcao__nome_funcao')

        if not conclusoes.exists():
            self.p("Nenhuma conclusão registrada.")
            return

        for c in conclusoes:
            func_nome = c.funcao.nome_funcao if c.funcao else 'N/I'

            if c.justificativa and c.justificativa.strip():
                texto = c.justificativa
            elif c.faz_jus_periculosidade:
                texto = (
                    f"Os empregados que exercem a função de <b>{func_nome}</b> "
                    f"estão expostos permanentemente a condições perigosas durante a "
                    f"realização de atividades, portanto, <b>FAZEM JUS</b> ao direito "
                    f"a receber o adicional de periculosidade no valor de 30% incidente "
                    f"sobre o salário, sem os acréscimos resultantes de gratificações, "
                    f"prêmios ou participações nos lucros da empresa, em períodos de "
                    f"atividade com as devidas exposições, assim como faz jus à "
                    f"aposentadoria especial, conforme a Lei 8213/91, com alteração "
                    f"dada pela Lei 9032/95, da Previdência Social."
                )
            elif c.faz_jus_insalubridade:
                grau_display = c.get_grau_insalubridade_display() if c.grau_insalubridade else 'N/I'
                perc = {'minimo': '10', 'medio': '20', 'maximo': '40'}.get(
                    c.grau_insalubridade, 'N/I'
                )
                texto = (
                    f"Os empregados que exercem a função de <b>{func_nome}</b>, "
                    f"estão expostos a condições insalubres por executarem atividades "
                    f"envolvendo riscos. Assim, esses profissionais <b>FAZEM JUS</b> "
                    f"ao direito a receber o adicional de insalubridade em "
                    f"<b>GRAU {grau_display.upper()}</b> ({perc}% do salário mínimo)."
                )
            else:
                texto = (
                    f"Os empregados que exercem a função de <b>{func_nome}</b>, "
                    f"não estão expostos a condições insalubres por executarem atividades "
                    f"envolvendo riscos físicos, visto que os valores apresentados nas "
                    f"avaliações estão abaixo dos LIMITES DE TOLERÂNCIA. Assim, esses "
                    f"profissionais <b>NÃO FAZEM JUS</b> ao direito a receber o "
                    f"adicional de insalubridade (10, 20 ou 40% do salário mínimo)."
                )

            self.p(texto)
            self.p(
                f"<b>Código GFIP/SEFIP:</b> {c.codigo_gfip} — "
                f"{c.get_codigo_gfip_display()}", 'corpo_small'
            )
            self.sp(4)

    # ================================================================
    # 10. RECOMENDAÇÕES TÉCNICAS
    # ================================================================

    def _secao_10_recomendacoes(self):
        self.titulo_secao('10', 'RECOMENDAÇÕES TÉCNICAS')

        recomendacoes = RecomendacaoTecnica.objects.filter(
            ltcat_documento=self.doc
        ).order_by('ordem', 'pk')

        if not recomendacoes.exists():
            self.p("Nenhuma recomendação técnica registrada.")
            return

        for rec in recomendacoes:
            self.p(f"• {rec.descricao}")
            self.sp(1)

    # ================================================================
    # 11. EMBASAMENTO LEGAL
    # ================================================================

    def _secao_11_embasamento(self):
        self.titulo_secao('11', 'EMBASAMENTO LEGAL - PORTARIA 3.214/78')

        self.p(self._get_texto('embasamento_ruido_intro'))
        self.sp(3)

        s = self.styles
        meio = len(TABELA_RUIDO_NR15) // 2
        col_esq = TABELA_RUIDO_NR15[:meio + 1]
        col_dir = TABELA_RUIDO_NR15[meio + 1:]

        header = [
            Paragraph("<b>Nível de Ruído<br/>dB(A)</b>", s['th']),
            Paragraph("<b>Máxima Exposição<br/>Diária Permitida</b>", s['th']),
            Paragraph("", s['th']),
            Paragraph("<b>Nível de Ruído<br/>dB(A)</b>", s['th']),
            Paragraph("<b>Máxima Exposição<br/>Diária Permitida</b>", s['th']),
        ]

        rows = [header]
        max_len = max(len(col_esq), len(col_dir))

        for i in range(max_len):
            row = []
            if i < len(col_esq):
                row.append(Paragraph(col_esq[i][0], s['td_center']))
                row.append(Paragraph(col_esq[i][1], s['td_center']))
            else:
                row.extend([Paragraph('', s['td']), Paragraph('', s['td'])])

            row.append(Paragraph('', s['td']))

            if i < len(col_dir):
                row.append(Paragraph(col_dir[i][0], s['td_center']))
                row.append(Paragraph(col_dir[i][1], s['td_center']))
            else:
                row.extend([Paragraph('', s['td']), Paragraph('', s['td'])])

            rows.append(row)

        cw = [25 * mm, 45 * mm, 5 * mm, 25 * mm, 45 * mm]
        t = Table(rows, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), AZUL_ESCURO),
            ('BACKGROUND', (3, 0), (4, 0), AZUL_ESCURO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (1, -1), 0.5, CINZA_MEDIO),
            ('GRID', (3, 0), (4, -1), 0.5, CINZA_MEDIO),
            ('LINEBELOW', (0, 0), (1, 0), 1.5, AZUL_ESCURO),
            ('LINEBELOW', (3, 0), (4, 0), 1.5, AZUL_ESCURO),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            *[('BACKGROUND', (0, i), (1, i), CINZA_CLARO)
              for i in range(2, max_len + 1, 2)],
            *[('BACKGROUND', (3, i), (4, i), CINZA_CLARO)
              for i in range(2, max_len + 1, 2)],
            ('BACKGROUND', (2, 0), (2, -1), colors.white),
            ('LINEWIDTH', (2, 0), (2, -1), 0),
        ]))
        self.elements.append(t)
        self.sp(5)

        self.p(self._get_texto('embasamento_demais_intro'))
        self.sp(3)

        headers = ['RISCO ANALISADO', 'NORMA UTILIZADA']
        dados = [[r, n] for r, n in TABELA_DEMAIS_AGENTES]
        self.tabela(headers, dados, col_widths=[90, 75])

    # ================================================================
    # 12. REFERÊNCIAS BIBLIOGRÁFICAS
    # ================================================================

    def _secao_12_referencias(self):
        self.titulo_secao('12', 'REFERÊNCIAS BIBLIOGRÁFICAS')

        texto = self.doc.referencias_bibliograficas
        if not texto:
            texto = self._get_texto('referencias_bibliograficas')
        self.p(texto)

    # ================================================================
    # 13. RESPONSÁVEL TÉCNICO + ASSINATURA
    # ================================================================

    def _secao_13_responsavel_tecnico(self):
        self.titulo_secao('13', 'RESPONSÁVEL TÉCNICO')

        self.p(get_texto('responsavel_tecnico'))
        self.sp(20)

        responsaveis = LTCATDocumentoResponsavel.objects.filter(
            ltcat_documento=self.doc
        ).select_related('profissional')

        if responsaveis.exists():
            for resp in responsaveis:
                prof = resp.profissional
                self.p("________________________________________", 'corpo_center')
                self.p(f"<b>{prof.nome_completo}</b>", 'corpo_center')
                self.p(prof.funcao, 'corpo_center')
                self.p(prof.registro_classe, 'corpo_center')
                self.sp(10)
        else:
            self.p("________________________________________", 'corpo_center')
            self.p("Responsável Técnico", 'corpo_center')

    # ================================================================
    # ANEXOS
    # ================================================================

    def _anexos(self):
        anexos = AnexoLTCAT.objects.filter(
            ltcat_documento=self.doc,
            incluir_no_pdf=True,
        ).order_by('ordem', 'numero_romano')

        if not anexos.exists():
            return

        for anx in anexos:
            self.pb()
            titulo = f"ANEXO {anx.numero_romano}" if anx.numero_romano else "ANEXO"
            self.p(f"<b>{titulo}</b>", 'capa_titulo')
            self.sp(3)
            self.p(f"<b>{anx.titulo or anx.get_tipo_display()}</b>", 'capa_subtitulo')
            self.sp(5)

            if anx.descricao:
                self.p(anx.descricao)
            else:
                self.p(
                    "<i>(Documento anexo disponibilizado separadamente)</i>",
                    'corpo_center'
                )

    # ================================================================
    # HELPER — busca texto customizado ou padrão
    # ================================================================

    def _get_texto(self, chave):
        try:
            secao = LTCATSecaoTexto.objects.get(
                ltcat_documento=self.doc,
                secao=chave,
                incluir_no_pdf=True,
            )
            if secao.conteudo and secao.conteudo.strip():
                return secao.conteudo
        except LTCATSecaoTexto.DoesNotExist:
            pass

        campo_map = {
            'objetivo': 'objetivo',
            'condicoes_preliminares': 'condicoes_preliminares',
            'referencias_bibliograficas': 'referencias_bibliograficas',
        }
        campo = campo_map.get(chave)
        if campo:
            valor = getattr(self.doc, campo, None)
            if valor and valor.strip():
                return valor

        return get_texto(chave)
