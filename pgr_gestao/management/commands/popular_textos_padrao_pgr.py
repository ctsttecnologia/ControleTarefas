
"""
Management command para popular os textos padrão das seções do PGR
Baseado no documento modelo: 10-CM 652 - JAGUARE-PGR-OUT25_assinado.pdf
"""
from django.core.management.base import BaseCommand
from pgr_gestao.models import PGRSecaoTextoPadrao


class Command(BaseCommand):
    help = 'Popula os textos padrão das seções do PGR conforme modelo oficial'

    def handle(self, *args, **options):
        textos = [
            {
                'secao': 'documento_base',
                'titulo': '2. DOCUMENTO BASE',
                'conteudo_padrao': (
                    'Este Programa de Gerenciamento de Riscos foi elaborado de acordo com os requisitos da '
                    'Norma Regulamentadora (NR) 1, com redação dada pela Portaria SEPRT nº 6.730, de 09/03/2020, '
                    'publicada no Diário Oficial da União de 12/03/2020.\n\n'
                    'Todos os requisitos da NR 01 foram cumpridos neste PGR, sendo que destacamos alguns para '
                    'fins ilustrativos:\n\n'
                    'A organização deve implementar, por estabelecimento, o gerenciamento de riscos ocupacionais '
                    'em suas atividades.\n\n'
                    'Os documentos integrantes do PGR devem ser elaborados sob a responsabilidade da organização, '
                    'respeitado o disposto nas demais Normas Regulamentadoras, datados e assinados, assim como '
                    'devem estar sempre disponíveis aos trabalhadores interessados ou seus representantes e à '
                    'Inspeção do Trabalho.'
                ),
            },
            {
                'secao': 'documento_base_metas',
                'titulo': 'METAS',
                'conteudo_padrao': (
                    'A organização deve implementar, por estabelecimento, o gerenciamento de riscos ocupacionais '
                    'em suas atividades mantendo o ambiente de trabalho dentro de condições adequadas ao '
                    'desenvolvimento das atividades laborais de todos os trabalhadores da empresa, eliminando ou '
                    'minimizando os riscos existentes a níveis compatíveis com os limites de tolerância da NR-15 '
                    'da Portaria 3.214/78 do Ministério do Trabalho ou na ausência destes os valores limites de '
                    'exposição ocupacional adotados pela ACGIH (American Conference of Governmental Industrial '
                    'Hygienists) através de um gerenciamento de riscos ocupacionais que deve constituir um '
                    'Programa de Gerenciamento de Riscos - PGR.'
                ),
            },
            {
                'secao': 'documento_base_objetivo',
                'titulo': 'OBJETIVO GERAL',
                'conteudo_padrao': (
                    'O PGR é um documento que tem como finalidade antecipar, reconhecer e avaliar os riscos '
                    'físicos, químicos, biológicos, ergonômicos e de acidentes, buscar melhoria contínua na '
                    'mitigação e na eliminação de fatores que podem trazer prejuízos à saúde e segurança do '
                    'trabalhador garantindo a implantação de medidas de controle quando necessárias.\n\n'
                    'Manter a equipe, permanentemente, bem preparada para a realização dos trabalhos seguindo '
                    'procedimentos que previnam a ocorrência de acidentes e danos à sua saúde.'
                ),
            },
            {
                'secao': 'definicoes',
                'titulo': '3. DEFINIÇÕES',
                'conteudo_padrao': (
                    'RISCOS AMBIENTAIS\n'
                    'São aqueles proporcionados pelos agentes físicos, químicos, biológicos, ergonômicos ou de '
                    'acidentes que quando presentes no ambiente de trabalho, os quais, em razão de sua natureza, '
                    'intensidade, concentração e tempo de exposição podem causar danos à saúde e integridade '
                    'física dos trabalhadores expostos.\n\n'
                    'AGENTES FÍSICOS\n'
                    'São todas as formas de energia capaz de se propagar nos ambientes e atingir os trabalhadores, '
                    'podendo causar danos à saúde ou à integridade física dos mesmos, tais como: calor, frio, '
                    'ruído, vibração, radiação ionizante, radiação não ionizante, pressões anormais e umidade.\n\n'
                    'AGENTES QUÍMICOS\n'
                    'São substâncias ou produtos de origens orgânicas ou minerais, naturais ou artificiais, '
                    'geradas e dispersas nos ambientes pelas mais variadas fontes, que podem penetrar no organismo '
                    'dos trabalhadores por inalação, absorção cutânea ou ingestão, e causar danos à saúde e/ou '
                    'integridade física dos mesmos.\n\n'
                    'AGENTES BIOLÓGICOS\n'
                    'São todos os vírus, bactérias, protozoários, fungos, parasitas ou bacilos, que podem penetrar '
                    'no organismo dos trabalhadores por meio do aparelho respiratório, contato com a pele, trato '
                    'digestivo e que podem causar danos à saúde dos trabalhadores.\n\n'
                    'AGENTES ERGONÔMICOS\n'
                    'Consideram-se agentes ergonômicos todos os fatores que possam interferir nas características '
                    'psicofisiológicas do trabalhador, causando desconforto ou afetando sua saúde, tais como: '
                    'trabalho físico pesado; posturas incorretas; posições incômodas; repetitividade, monotonia; '
                    'ritmo excessivo; trabalho em turnos e trabalho noturno; jornada de trabalho.\n\n'
                    'AGENTES MECÂNICOS OU RISCOS DE ACIDENTES\n'
                    'Consideram-se agentes mecânicos ou riscos de acidente as diversas situações do ambiente de '
                    'trabalho que têm potencial de causar danos instantâneos, materiais ou pessoais, aos quais os '
                    'trabalhadores estão expostos.\n\n'
                    'EPI - EQUIPAMENTO DE PROTEÇÃO INDIVIDUAL\n'
                    'É todo meio ou dispositivo de uso exclusivamente pessoal, destinado a neutralizar, preservar '
                    'e proteger a saúde e/ou a integridade física dos trabalhadores.\n\n'
                    'EPC - EQUIPAMENTO DE PROTEÇÃO COLETIVA\n'
                    'Todo e qualquer equipamento utilizado para eliminar ou neutralizar os agentes agressivos ao '
                    'meio laboral, visando a preservação da saúde e/ou integridade física dos trabalhadores.\n\n'
                    'PERIGO\n'
                    'Fonte ou situação ou ato potencial com capacidade de gerar dano ou perturbação funcional no '
                    'ser humano.\n\n'
                    'RISCO\n'
                    'Combinação da Probabilidade e da Severidade da Consequência (Impacto) de um evento.\n\n'
                    'LIMITE DE TOLERÂNCIA\n'
                    'Concentração ou intensidade máxima ou mínima, relacionada com a natureza e o tempo de '
                    'exposição ao agente, que não causará danos à saúde do trabalhador, durante sua vida laboral.\n\n'
                    'GRUPO HOMOGÊNEO DE EXPOSIÇÃO (GHE)\n'
                    'Grupo formado por trabalhadores que experimentam ou estão expostos a um mesmo agente.\n\n'
                    'GRUPO DE EXPOSIÇÃO SIMILAR (GES)\n'
                    'Grupo formado por trabalhadores que desenvolvem uma atividade especial, não rotineira e que '
                    'em realizando-as experimentam ou ficam expostas a um determinado agente.'
                ),
            },
            {
                'secao': 'estrutura_pgr',
                'titulo': '4. ESTRUTURA DO PGR',
                'conteudo_padrao': '',
            },
            {
                'secao': 'estrutura_requisitos',
                'titulo': 'REQUISITOS LEGAIS',
                'conteudo_padrao': (
                    'Sempre discutir com os empregados da {empresa} os assuntos pertinentes ao PGR.\n\n'
                    'É Obrigação Legal por parte da empresa a elaboração do Programa de Gerenciamento de '
                    'Risco – PGR – visando preservar a saúde e integridade física dos trabalhadores.\n\n'
                    'A concepção do PGR atende as exigências da NR 09 relativas à avaliação e controle de '
                    'fatores de riscos ambientais de natureza química, física ou biológica. Contempla também '
                    'as exigências da NR 15.'
                ),
            },
            {
                'secao': 'estrutura_estrategia',
                'titulo': 'ESTRATÉGIA E METODOLOGIA DE AÇÃO',
                'conteudo_padrao': (
                    'O PGR está estruturado em cinco fases distintas:\n\n'
                    '1) A primeira fase trata da elaboração do documento base onde está contemplado os tópicos '
                    'básicos da estrutura do programa de gerenciamento de risco;\n'
                    '2) Na segunda fase é a realização da análise preliminar de perigos e sua inserção na planilha '
                    'de inventário de riscos, perigos, aspectos e impactos;\n'
                    '3) A terceira é realização de avaliação quantitativa (quando houver necessidade) para os '
                    'itens avaliados no levantamento preliminar de perigo considerando uma avaliação qualitativa;\n'
                    '4) A quarta fase é a realização da construção do cronograma de ação com todas as partes '
                    'envolvidas para o estabelecimento do Plano de Ação;\n'
                    '5) Por fim, a execução do plano de ação, com a implementação de todo o planejado incluindo '
                    'os programas complementares de atendimento a NRs especificas e seus desdobramentos.'
                ),
            },
            {
                'secao': 'estrutura_periodicidade',
                'titulo': 'PERIODICIDADE E FORMA DE AVALIAÇÃO DO DESENVOLVIMENTO DO PGR',
                'conteudo_padrao': (
                    'Faz-se necessário 01 (uma) vez a cada 02 (dois) anos deverá ser realizada uma análise '
                    'global do PGR, para avaliação do seu desenvolvimento e ajustes, estabelecendo novas metas '
                    'e prioridades, exceto quando na ocorrência das seguintes situações:\n\n'
                    'a) Após implementação das medidas de prevenção, para avaliação de riscos residuais;\n'
                    'b) Após inovações e modificações nas tecnologias, ambientes, processos, condições, '
                    'procedimentos e organização do trabalho que impliquem em novos riscos ou modifiquem os '
                    'riscos existentes;\n'
                    'c) Quando identificadas inadequações, insuficiências ou ineficácias das medidas de prevenção;\n'
                    'd) Na ocorrência de acidentes ou doenças relacionadas ao trabalho;\n'
                    'e) Quando houver mudança nos requisitos legais aplicáveis.'
                ),
            },
            {
                'secao': 'responsabilidades',
                'titulo': '5. DEFINIÇÃO DAS RESPONSABILIDADES',
                'conteudo_padrao': '',
            },
            {
                'secao': 'resp_organizacao',
                'titulo': 'DA ORGANIZAÇÃO',
                'conteudo_padrao': (
                    'a) Evitar os riscos ocupacionais que possam ser originados no trabalho;\n'
                    'b) Identificar os perigos e possíveis lesões ou agravos à saúde;\n'
                    'c) Avaliar os riscos ocupacionais indicando o nível de risco;\n'
                    'd) Classificar os riscos ocupacionais para determinar a necessidade de adoção de medidas '
                    'de prevenção;\n'
                    'e) Implementar medidas de prevenção, de acordo com a classificação de risco e na ordem de '
                    'prioridade estabelecida;\n'
                    'f) Acompanhar o controle dos riscos ocupacionais;\n'
                    'g) A organização deve adotar as medidas necessárias para melhorar o desempenho em SST;\n'
                    'h) Realizar a avaliação de riscos ocupacionais;\n'
                    'i) A organização deve avaliar os riscos ocupacionais relativos aos perigos identificados '
                    'em seu(s) estabelecimento(s).'
                ),
            },
            {
                'secao': 'resp_empregados',
                'titulo': 'DOS EMPREGADOS',
                'conteudo_padrao': (
                    'a) Colaborar e participar da implantação e execução do PGR;\n'
                    'b) Seguir as orientações recebidas nos treinamentos do PGR;\n'
                    'c) Informar à chefia ocorrências que a seu julgamento ofereçam riscos ambientais;\n'
                    'd) Cumprir as disposições legais e regulamentares sobre segurança e saúde no trabalho;\n'
                    'e) Submeter-se aos exames médicos previstos nas NR;\n'
                    'f) Em caso de acidente de trabalho, informar à supervisão;\n'
                    'g) Colaborar com a organização na aplicação das NR;\n'
                    'h) Usar o equipamento de proteção individual (EPI) fornecido pelo empregador.'
                ),
            },
            {
                'secao': 'desenvolvimento',
                'titulo': '7. DESENVOLVIMENTO DO PGR',
                'conteudo_padrao': (
                    'a) Antecipação: Análise prévia de projetos, de instalações, de processos e de métodos de '
                    'trabalho, ou modificações nos mesmos, visando identificar os possíveis riscos.\n\n'
                    'b) Reconhecimento dos Riscos: Aplicação das Ordens de Serviço de Segurança (OSS) conforme '
                    'NR-1 a fim de divulgar e antecipar a neutralização ou eliminação de atitudes e/ou condições '
                    'de riscos ambientais e de acidentes nas áreas de trabalho.\n\n'
                    'c) Avaliação: As avaliações dos agentes físicos, químicos, biológicos e ergonômicos nas '
                    'áreas de trabalho serão realizadas, quando necessário ou durante a revisão do Programa.'
                ),
            },
            {
                'secao': 'metodologia_avaliacao',
                'titulo': '8. METODOLOGIA DE AVALIAÇÃO',
                'conteudo_padrao': (
                    'O PGR é parte integrante do conjunto mais amplo das iniciativas da empresa no campo da '
                    'preservação da saúde e integridade dos trabalhadores, devendo estar articulado com o '
                    'disposto nas demais NRs. Em especial com o Programa de Controle Médico de Saúde '
                    'Ocupacional - PCMSO, determinado de acordo com a NR - 7.'
                ),
            },
            {
                'secao': 'metodo_ruido',
                'titulo': 'AGENTE FÍSICO RUÍDO',
                'conteudo_padrao': (
                    'Conforme estabelece a Norma NHO 01 da Fundacentro, Normas Técnicas ANSI 4-1983 e '
                    'IEC 651-79 e Anexo 1 da NR 15 da Portaria 3214/78, o agente ruído será avaliado por '
                    'Dosimetria inicial na elaboração do PGR ou quando houver mudanças significativas no '
                    'ambiente de trabalho.'
                ),
            },
            {
                'secao': 'metodo_calor',
                'titulo': 'AGENTE FÍSICO CALOR',
                'conteudo_padrao': (
                    'A Norma Regulamentadora 15 (NR 15), em seu Anexo 3, especifica algumas condições em que '
                    'o ambiente, exposto ao calor, é considerado acima da tolerância para a saúde do trabalhador. '
                    'A medição de níveis de calor e temperatura, é através do IBUTG (Índice de Bulbo Úmido '
                    'Termômetro de Globo).'
                ),
            },
            {
                'secao': 'metodo_quimico',
                'titulo': 'AGENTES QUÍMICOS',
                'conteudo_padrao': (
                    'Inventário de agentes Químicos, utilizando as Fichas de Informação de Produtos Químicos '
                    '(FISPQ) fornecida pelo fabricante do produto, com critérios estabelecidos pelos anexos 11 '
                    'e 13 da NR 15 da Portaria 3214/78.'
                ),
            },
            {
                'secao': 'medidas_protecao',
                'titulo': '11. MEDIDAS DE PROTEÇÃO',
                'conteudo_padrao': '',
            },
            {
                'secao': 'medidas_epc',
                'titulo': 'MEDIDAS DE PROTEÇÃO COLETIVA',
                'conteudo_padrao': (
                    '{empresa} faz uso de suas normas e seus procedimentos para orientar, treinar e capacitar '
                    'os funcionários quanto às medidas de controle coletivos que proporcionam maior segurança '
                    'na execução de suas tarefas.'
                ),
            },
            {
                'secao': 'medidas_epi',
                'titulo': 'MEDIDAS DE ORDEM INDIVIDUAL (EPI)',
                'conteudo_padrao': (
                    '{empresa} faz uso de suas normas e seus procedimentos para orientar, treinar e capacitar '
                    'os funcionários quanto às medidas de ordem individuais (EPI) que proporcionam maior '
                    'segurança na execução de suas tarefas.\n\n'
                    'Quando comprovadas a inviabilidade técnica ou econômica para a implementação da proteção '
                    'coletiva, a empresa fornecerá EPI conforme procedimentos específicos para as áreas envolvidas.'
                ),
            },
            {
                'secao': 'plano_acao',
                'titulo': '10. PLANO DE AÇÃO',
                'conteudo_padrao': (
                    'No Programa Gerenciamento de Riscos – PGR serão observadas e seguidas as seguintes etapas '
                    'no plano de ação:\n\n'
                    'a) Antecipação e Reconhecimento dos riscos;\n'
                    'b) Estabelecimento de prioridades e metas de avaliação e controle;\n'
                    'c) Avaliação dos riscos e da exposição dos trabalhadores;\n'
                    'd) Implantação de medidas de controle e avaliação de sua eficácia;\n'
                    'e) Monitoramento da exposição aos riscos;\n'
                    'f) Registro e divulgação de dados através de treinamentos;\n'
                    'g) Prevenção, eliminação ou redução de agentes prejudiciais à saúde.'
                ),
            },
            {
                'secao': 'divulgacao',
                'titulo': '13. DIVULGAÇÃO DO PROGRAMA',
                'conteudo_padrao': (
                    'Os documentos e os procedimentos operacionais que integram o Programa de Gerenciamento '
                    'de Risco (PGR) estarão disponíveis aos empregados.\n\n'
                    'A atualização do PGR será realizada quando da ocorrência de alterações significativas de '
                    'ordem tecnológica, operacional, legal ou regulatória que provoquem a necessidade de '
                    'adequação dos documentos que o integram ou ainda quando for recomendado na auditoria anual.'
                ),
            },
            {
                'secao': 'recomendacoes',
                'titulo': '14. RECOMENDAÇÕES GERAIS',
                'conteudo_padrao': (
                    '- Aplicação de medidas, sempre que necessárias, de caráter administrativo ou da '
                    'organização do trabalho.\n'
                    '- Aplicação de Treinamento de Segurança em geral, sobre Uso de EPI, Cuidados com '
                    'produtos químicos, Levantamento de peso e Trabalho em Altura.\n'
                    '- Aplicação de Treinamento para membro designado de segurança da CIPA.\n'
                    '- Fornecimento de EPIs adequados de acordo com Ficha Técnica de Classificação de EPI '
                    'por Função.\n'
                    '- Orientações sobre o uso correto e higiênico dos vestiários e asseio pessoal.\n'
                    '- Execução do Gerenciamento de Riscos através da observação de segurança.\n'
                    '- Guarda de documentação do controle das intervenções de segurança do trabalho.\n'
                    '- Aplicação de rígido controle médico dos empregados.'
                ),
            },
            {
                'secao': 'legislacao',
                'titulo': '15. LEGISLAÇÃO COMPLEMENTAR',
                'conteudo_padrao': (
                    'Além de atender a Portaria SEPRT n° 6730 de 09 de março de 2020, o PGR atende uma série '
                    'de outras normas e legislações complementares:\n\n'
                    '- PORTARIA 3214/78 – NORMAS REGULAMENTADORAS\n'
                    '- NORMAS DE HIGIENE OCUPACIONAL – FUNDACENTRO\n'
                    '- ABNT ISO NBR 45001 – SISTEMA DE GESTÃO DE SEGURANÇA E SAÚDE OCUPACIONAL\n'
                    '- ABNT ISO NBR 31000 – GESTÃO DE RISCOS – DIRETRIZES\n'
                    '- ABNT NBR 5413 – ILUMINAÇÃO DE INTERIORES\n'
                    '- ABNT NBR 10152 – NÍVEL DE RUÍDO PARA CONFORTO ACÚSTICO'
                ),
            },
        ]

        criados = 0
        atualizados = 0
        
        for texto in textos:
            obj, created = PGRSecaoTextoPadrao.objects.update_or_create(
                secao=texto['secao'],
                defaults={
                    'titulo': texto['titulo'],
                    'conteudo_padrao': texto['conteudo_padrao'],
                    'ativo': True,
                }
            )
            if created:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Textos padrão populados: {criados} criados, {atualizados} atualizados.'
            )
        )

