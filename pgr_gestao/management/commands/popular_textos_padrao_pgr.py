
"""
Management command para popular os textos padrão das seções do PGR
Baseado no documento modelo: 10-CM 652 - JAGUARE-PGR-OUT25_assinado.pdf

Uso:
    python manage.py popular_textos_padrao_pgr
    python manage.py popular_textos_padrao_pgr --force  (sobrescreve existentes)
"""
from django.core.management.base import BaseCommand
from pgr_gestao.models import PGRSecaoTextoPadrao


class Command(BaseCommand):
    help = 'Popula os textos padrão das seções do PGR conforme modelo oficial CETEST'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sobrescreve textos existentes (default: apenas cria novos)',
        )

    def handle(self, *args, **options):
        force = options['force']
        textos = self._get_textos()

        criados = 0
        atualizados = 0
        ignorados = 0

        for texto in textos:
            if force:
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
            else:
                obj, created = PGRSecaoTextoPadrao.objects.get_or_create(
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
                    ignorados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Textos padrão populados com sucesso!\n'
            f'   📄 Criados: {criados}\n'
            f'   🔄 Atualizados: {atualizados}\n'
            f'   ⏭️  Ignorados (já existiam): {ignorados}\n'
            f'   📊 Total de seções: {len(textos)}'
        ))

    def _get_textos(self):
        return [
            # ══════════════════════════════════════════════════════════
            # 2. DOCUMENTO BASE
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'documento_base',
                'titulo': '2. DOCUMENTO BASE',
                'conteudo_padrao': (
                    'PGR – PROGRAMA DE GERENCIAMENTO DE RISCOS\n\n'
                    'Este Programa de Gerenciamento de Riscos foi elaborado de acordo com os requisitos da '
                    'Norma Regulamentadora (NR) 1, com redação dada pela Portaria SEPRT nº 6.730, de '
                    '09/03/2020, publicada no Diário Oficial da União de 12/03/2020.\n\n'
                    'Todos os requisitos da NR 01 foram cumpridos neste PGR, sendo que destacamos alguns '
                    'para fins ilustrativos:\n\n'
                    'A organização deve implementar, por estabelecimento, o gerenciamento de riscos '
                    'ocupacionais em suas atividades.\n\n'
                    'Os documentos integrantes do PGR devem ser elaborados sob a responsabilidade da '
                    'organização, respeitado o disposto nas demais Normas Regulamentadoras, datados e '
                    'assinados, assim como devem estar sempre disponíveis aos trabalhadores interessados '
                    'ou seus representantes e à Inspeção do Trabalho.'
                ),
            },
            {
                'secao': 'documento_base_metas',
                'titulo': 'METAS',
                'conteudo_padrao': (
                    'A organização deve implementar, por estabelecimento, o gerenciamento de riscos '
                    'ocupacionais em suas atividades mantendo o ambiente de trabalho dentro de condições '
                    'adequadas ao desenvolvimento das atividades laborais de todos os trabalhadores da '
                    'empresa, eliminando ou minimizando os riscos existentes a níveis compatíveis com os '
                    'limites de tolerância da NR-15 da Portaria 3.214/78 do Ministério do Trabalho ou na '
                    'ausência destes os valores limites de exposição ocupacional adotados pela ACGIH '
                    '(American Conference of Governmental Industrial Hygienists) através de um '
                    'gerenciamento de riscos ocupacionais que deve constituir um Programa de '
                    'Gerenciamento de Riscos - PGR.'
                ),
            },
            {
                'secao': 'documento_base_objetivo',
                'titulo': 'OBJETIVO GERAL',
                'conteudo_padrao': (
                    'O PGR é um documento que tem como finalidade antecipar, reconhecer e avaliar os '
                    'riscos físicos, químicos, biológicos, ergonômicos e de acidentes, buscar melhoria '
                    'contínua na mitigação e na eliminação de fatores que podem trazer prejuízos à saúde '
                    'e segurança do trabalhador garantindo a implantação de medidas de controle quando '
                    'necessárias.\n\n'
                    'Manter a equipe, permanentemente, bem preparada para a realização dos trabalhos '
                    'seguindo procedimentos que previnam a ocorrência de acidentes e danos à sua saúde.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 3. DEFINIÇÕES
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'definicoes',
                'titulo': '3. DEFINIÇÕES',
                'conteudo_padrao': (
                    'RISCOS AMBIENTAIS\n'
                    'São aqueles proporcionados pelos agentes físicos, químicos, biológicos, ergonômicos '
                    'ou de acidentes que quando presentes no ambiente de trabalho, os quais, em razão de '
                    'sua natureza, intensidade, concentração e tempo de exposição podem causar danos à '
                    'saúde e integridade física dos trabalhadores expostos.\n\n'

                    'AGENTES FÍSICOS\n'
                    'São todas as formas de energia capaz de se propagar nos ambientes e atingir os '
                    'trabalhadores, podendo causar danos à saúde ou à integridade física dos mesmos, '
                    'tais como: calor, frio, ruído, vibração, radiação ionizante, radiação não ionizante, '
                    'pressões anormais e umidade.\n\n'

                    'AGENTES QUÍMICOS\n'
                    'São substâncias ou produtos de origens orgânicas ou minerais, naturais ou '
                    'artificiais, geradas e dispersas nos ambientes pelas mais variadas fontes, que '
                    'podem penetrar no organismo dos trabalhadores por inalação, absorção cutânea ou '
                    'ingestão, e causar danos à saúde e/ou integridade física dos mesmos, sob a forma '
                    'de poeiras, névoas, gases, vapores ou outras substâncias, compostas ou produtos '
                    'químicos em geral.\n\n'

                    'AGENTES BIOLÓGICOS\n'
                    'São todos os vírus, bactérias, protozoários, fungos, parasitas ou bacilos, que '
                    'podem penetrar no organismo dos trabalhadores por meio do aparelho respiratório, '
                    'contato com a pele, trato digestivo e que podem causar danos à saúde dos '
                    'trabalhadores.\n\n'

                    'AGENTES ERGONÔMICOS\n'
                    'Consideram-se agentes ergonômicos todos os fatores que possam interferir nas '
                    'características psicofisiológicas do trabalhador, causando desconforto ou afetando '
                    'sua saúde, tais como: trabalho físico pesado; posturas incorretas; posições '
                    'incômodas; repetitividade, monotonia; ritmo excessivo; trabalho em turnos e '
                    'trabalho noturno; jornada de trabalho.\n\n'

                    'AGENTES MECÂNICOS OU RISCOS DE ACIDENTES\n'
                    'Consideram-se agentes mecânicos ou riscos de acidente as diversas situações do '
                    'ambiente de trabalho que têm potencial de causar danos instantâneos, materiais ou '
                    'pessoais, aos quais os trabalhadores estão expostos, como por exemplo: as máquinas '
                    'e equipamentos sem proteção, probabilidade de incêndio e explosão, arranjo físico '
                    'inadequado, armazenamento inadequado, ferramentas inadequadas ou defeituosas; '
                    'iluminação inadequada; contato com eletricidade; animais peçonhentos; entre '
                    'outros.\n\n'

                    'EPI - EQUIPAMENTO DE PROTEÇÃO INDIVIDUAL\n'
                    'É todo meio ou dispositivo de uso exclusivamente pessoal, destinado a neutralizar, '
                    'preservar e proteger a saúde e/ou a integridade física dos trabalhadores.\n\n'

                    'EPC - EQUIPAMENTO DE PROTEÇÃO COLETIVA\n'
                    'Todo e qualquer equipamento utilizado para eliminar ou neutralizar os agentes '
                    'agressivos ao meio laboral, visando a preservação da saúde e/ou integridade física '
                    'dos trabalhadores.\n\n'

                    'ANÁLISE QUALITATIVA\n'
                    'Determinação nas atividades, através de inspeção dos locais de trabalho constante '
                    'nos anexos 7, 8, 9, 10 e 13 da NR-15. A Análise Qualitativa também indicará a '
                    'necessidade técnica de avaliações quantitativas dos GHEs expostos a agentes '
                    'ambientais quantificáveis, sendo seus resultados comparados com os limites de '
                    'tolerância oficialmente estabelecidos.\n\n'

                    'AVALIAÇÃO QUANTITATIVA\n'
                    'Determinação nas atividades que se desenvolvem com o objetivo de:\n'
                    'a) comprovar o controle da exposição ou a inexistência dos riscos identificados '
                    'na etapa de reconhecimento;\n'
                    'b) dimensionar a exposição dos trabalhadores;\n'
                    'c) subsidiar o equacionamento das medidas de controle.\n\n'

                    'PERIGO\n'
                    'Fonte ou situação ou ato potencial com capacidade de gerar dano ou perturbação '
                    'funcional no ser humano, ou ainda, originem de situações que podem culminar com '
                    'incidentes no produto ou processo dentro da empresa. Dentro deste entendimento '
                    'consideramos sua natureza com física, química, biológica, ergonômica e de '
                    'acidentes diretos ou indiretos.\n\n'

                    'IDENTIFICAÇÃO DE PERIGOS\n'
                    'Processo analítico de reconhecimento utilizando-se de ferramenta técnica Inventário '
                    'de riscos, perigos, aspectos e impactos, cuja finalidade é registrar sua existência, '
                    'bem como definir suas características.\n\n'

                    'RISCO\n'
                    'Combinação da Probabilidade e da Severidade da Consequência (Impacto) de um evento; '
                    'a ocorrência de um evento perigoso ou a exposição com a gravidade da lesão, doença '
                    'ou dano ao patrimônio que pode ser causado por um evento imponderável, imprevisto.\n\n'

                    'CLASSIFICAÇÃO DE RISCOS\n'
                    'Processo no qual estima-se a magnitude do Risco, considerando em decisão se este é '
                    'Baixo, Tolerável, Moderado ou Significativo; Avaliação de Risco proveniente de '
                    'perigos.\n\n'

                    'ACIDENTE\n'
                    'É uma ocorrência que resultou em lesão, doença, fatalidade, prejuízo ao processo '
                    'produtivo, perda de matéria prima (produto) ou ainda dano ao meio ambiente.\n\n'

                    'INCIDENTE\n'
                    'Evento ou ocorrência que poderia vir a acontecer no decorrer do processo produtivo '
                    'relacionado ao trabalho podendo gerar lesão, doença, fatalidade ou perda dentro do '
                    'processo produtivo.\n\n'

                    'LIMITE DE TOLERÂNCIA\n'
                    'Concentração ou intensidade máxima ou mínima, relacionada com a natureza e o tempo '
                    'de exposição ao agente, que não causará danos à saúde do trabalhador, durante sua '
                    'vida laboral.\n\n'

                    'LIMITE DE EXPOSIÇÃO\n'
                    'Concentração da média ponderada pelo tempo para uma jornada de 8 horas diárias e '
                    '44 horas semanais, para a qual a maioria dos trabalhadores pode estar repetidamente '
                    'exposta, dia após dia, sem sofrer efeitos adversos à sua saúde.\n\n'

                    'LIMITE DE EXPOSIÇÃO – CURTA DURAÇÃO\n'
                    'Concentração Máxima a que os trabalhadores podem estar expostos continuamente por '
                    'um período curto, de até 15 minutos, sem sofrer irritação, lesão tissular crônica '
                    'ou irreversível, narcose em grau suficiente para aumentar a predisposição a '
                    'acidentes, impedir auto salvamento ou reduzir significativamente a eficiência no '
                    'trabalho, desde que não sejam permitidas mais de 4 exposições diárias, com pelo '
                    'menos 60 minutos de intervalo entre os períodos de exposição.\n\n'

                    'NÍVEL DE AÇÃO\n'
                    'Valor acima do qual devem ser iniciadas as ações preventivas (Monitoramento '
                    'periódicos, Informação aos Trabalhadores e o Controle Médico), de forma a '
                    'minimizar a probabilidade de que as exposições a agentes ambientais ultrapassem '
                    'os limites de exposição.\n\n'

                    'GRUPO HOMOGÊNEO DE EXPOSIÇÃO (GHE)\n'
                    'Grupo formado por trabalhadores que experimentam ou estão expostos a um mesmo '
                    'agente, permitindo desta forma que seja feita apenas uma avaliação individual de '
                    'exposição à agentes ambientais agressivos no ambiente de trabalho que é possível '
                    'aplicá-la para todo o grupo. Isso não implica em concluir que todos eles necessitem '
                    'sofrer idênticas exposições num mesmo dia. Como decorrência da aplicação dos '
                    'fundamentos em que se baseia a estatística, como ciência, um pequeno número de '
                    'amostras selecionadas randomicamente, ou seja, aleatoriamente, pode ser utilizado '
                    'para determinar as distribuições de exposição dentro de um GHE. Escolher o '
                    'parâmetro, que servirá como base para estruturação do GHE. Normalmente a escolha '
                    'recairá sobre um dos parâmetros a seguir:\n'
                    '• Tarefas dos trabalhadores;\n'
                    '• Funções/atividades;\n'
                    '• Agentes ambientais.\n\n'

                    'GRUPO DE EXPOSIÇÃO SIMILAR (GES)\n'
                    'Grupo formado por trabalhadores que desenvolvem uma atividade especial, não '
                    'rotineira e que em realizando-as experimentam ou ficam expostas a um determinado '
                    'agente, não existente em sua atividade rotineira.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 4. ESTRUTURA DO PGR
            # ══════════════════════════════════════════════════════════
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
                    'É Obrigação Legal por parte da empresa a elaboração do Programa de Gerenciamento '
                    'de Risco – PGR – visando preservar a saúde e integridade física dos trabalhadores.\n\n'
                    'A concepção do PGR atende as exigências da NR 09 relativas à avaliação e controle '
                    'de fatores de riscos ambientais de natureza química, física ou biológica. Contempla '
                    'também as exigências da NR 15. De acordo com a NR 09, NR 15 e limites da ACGIH, '
                    'são considerados riscos inaceitáveis aqueles cujas exposições ultrapassarem os '
                    'limites exposição ocupacionais estabelecidos. Entretanto, ações devem ser tomadas '
                    'quando a exposição estimada ultrapassar o nível de ação que, segundo a NR-09, para '
                    'agentes químicos corresponde à metade do limite de exposição ocupacional, e para o '
                    'ruído, a dose de 0,5 (dose superior a 50%). Essas ações não se restringem apenas à '
                    'modificação das medidas de controle, mas inclui também a pesquisa aprofundada das '
                    'fontes geradoras, o monitoramento mais frequente da exposição e a intensificação da '
                    'vigilância médica, com atenção especial para identificação de efeitos precoces.\n\n'
                    'Segundo o critério legal podem ser considerados aceitáveis riscos relacionados a '
                    'exposições acima dos limites permitidos quando os trabalhadores utilizarem proteção '
                    'individual adequada, com garantia de manutenção e comprovação de eficácia e '
                    'eficiência de uso dos mesmos.\n\n'
                    'Os critérios legais serão utilizados para demonstrar que a {empresa} atende os '
                    'requisitos legais, buscando-se adotar critérios complementares e voluntários para '
                    'reduzir as exposições e garantir uma qualidade adequada dos ambientes de trabalho.'
                ),
            },
            {
                'secao': 'estrutura_estrategia',
                'titulo': 'ESTRATÉGIA E METODOLOGIA DE AÇÃO',
                'conteudo_padrao': (
                    'O PGR está estruturado em cinco fases distintas:\n\n'
                    '1) A primeira fase trata da elaboração do documento base onde está contemplado os '
                    'tópicos básicos da estrutura do programa de gerenciamento de risco;\n'
                    '2) Na segunda fase é a realização da análise preliminar de perigos e sua inserção '
                    'na planilha de inventário de riscos, perigos, aspectos e impactos;\n'
                    '3) A terceira é realização de avaliação quantitativa (quando houver necessidade) '
                    'para os itens avaliados no levantamento preliminar de perigo considerando uma '
                    'avaliação qualitativa;\n'
                    '4) A quarta fase é a realização da construção do cronograma de ação com todas as '
                    'partes envolvidas para o estabelecimento do Plano de Ação;\n'
                    '5) Por fim, a execução do plano de ação, com a implementação de todo o planejado '
                    'incluindo os programas complementares de atendimento a NRs especificas e seus '
                    'desdobramentos.'
                ),
            },
            {
                'secao': 'estrutura_registro',
                'titulo': 'FORMA DE REGISTRO, MANUTENÇÃO E DIVULGAÇÃO DE DADOS',
                'conteudo_padrao': (
                    'Este Documento Base, será apresentado aos Designados CIPA, ficando a disposição '
                    'para consultas dos trabalhadores e órgãos oficiais de fiscalização.'
                ),
            },
            {
                'secao': 'estrutura_periodicidade',
                'titulo': 'PERIODICIDADE E FORMA DE AVALIAÇÃO DO DESENVOLVIMENTO DO PGR',
                'conteudo_padrao': (
                    'Faz-se necessário 01 (uma) vez a cada 02 (dois) anos deverá ser realizada uma '
                    'análise global do PGR, para avaliação do seu desenvolvimento e ajustes, '
                    'estabelecendo novas metas e prioridades, exceto quando na ocorrência das seguintes '
                    'situações:\n\n'
                    'a) Após implementação das medidas de prevenção, para avaliação de riscos '
                    'residuais;\n'
                    'b) Após inovações e modificações nas tecnologias, ambientes, processos, condições, '
                    'procedimentos e organização do trabalho que impliquem em novos riscos ou modifiquem '
                    'os riscos existentes;\n'
                    'c) Quando identificadas inadequações, insuficiências ou ineficácias das medidas de '
                    'prevenção;\n'
                    'd) Na ocorrência de acidentes ou doenças relacionadas ao trabalho;\n'
                    'e) Quando houver mudança nos requisitos legais aplicáveis.'
                ),
            },
            {
                'secao': 'estrutura_implantacao',
                'titulo': 'IMPLANTAÇÃO DO CRONOGRAMA DE AÇÃO',
                'conteudo_padrao': (
                    'O Plano de ação com seu cronograma será apresentado às Hierarquias superiores, à '
                    'Designados CIPA e os registros das ações serão mantidos em arquivo sob '
                    'responsabilidade do funcionário responsável pela Segurança do Trabalho, por período '
                    'de 20 anos, fazendo divulgação das soluções propostas, através dos meios de '
                    'comunicação existentes na empresa.'
                ),
            },
            {
                'secao': 'estrutura_eficacia',
                'titulo': 'ANÁLISE DA EFICÁCIA E CORREÇÕES DAS METAS E PRIORIDADES',
                'conteudo_padrao': (
                    'A análise da eficácia e as correções das metas e prioridades serão realizadas, '
                    'considerando as avaliações do ambiente de trabalho, os dados coletados com os '
                    'trabalhadores e a verificação de possíveis alterações nos setores de trabalho. O '
                    'cronograma de ações será alterado conforme as correções das metas e prioridades '
                    'estabelecidas.\n\n'
                    'Este Documento Base, será apresentado em reunião de Designados CIPA, ficando a '
                    'disposição para consultas dos trabalhadores e órgãos oficiais de fiscalização.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 5. DEFINIÇÃO DAS RESPONSABILIDADES
            # ══════════════════════════════════════════════════════════
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
                    'd) Classificar os riscos ocupacionais para determinar a necessidade de adoção de '
                    'medidas de prevenção;\n'
                    'e) Implementar medidas de prevenção, de acordo com a classificação de risco e na '
                    'ordem de prioridade estabelecida na tabela 6; e\n'
                    'f) Acompanhar o controle dos riscos ocupacionais.\n'
                    'g) A organização deve adotar as medidas necessárias para melhorar o desempenho '
                    'em SST.\n'
                    'h) Realizar a avaliação de riscos ocupacionais.\n'
                    'i) A organização deve avaliar os riscos ocupacionais relativos aos perigos '
                    'identificados em seu(s) estabelecimento(s), de forma a manter informações para '
                    'adoção de medidas de prevenção.'
                ),
            },
            {
                'secao': 'resp_informacao',
                'titulo': 'DA INFORMAÇÃO',
                'conteudo_padrao': (
                    'a) Consultar os trabalhadores quanto à percepção de riscos ocupacionais, podendo '
                    'para este fim ser adotadas as manifestações da Comissão Interna de Prevenção de '
                    'Acidentes - CIPA, quando houver; e\n'
                    'b) Comunicar aos trabalhadores sobre os riscos consolidados no inventário de riscos '
                    'e as medidas de prevenção do plano de ação do PGR.'
                ),
            },
            {
                'secao': 'resp_procedimentos',
                'titulo': 'PROCEDIMENTOS',
                'conteudo_padrao': (
                    'a) Cabe a Alta Direção e superiores hierárquicos: Apoiar a implantação, manutenção '
                    'e desenvolvimento do PGR e das atividades prevencionistas e efetivar normas, '
                    'instruções e programas estabelecidos pelo Ministério do Trabalho e Emprego.\n'
                    'b) Desenvolver, administrar e inspecionar as atividades de prevenção de acidentes, '
                    'cumprindo os dispositivos legais vigentes.\n'
                    'c) Orientar e assessorar os diversos órgãos da Empresa de forma a garantir o '
                    'desempenho dos mesmos, na aplicação dos programas de segurança estabelecidos.\n'
                    'd) Elaborar e propor normas, instruções e regulamentos de Segurança e Higiene do '
                    'Trabalho.\n'
                    'e) Manter, obrigatoriamente, programa de inspeção de segurança visando levantar '
                    'os riscos de acidentes.\n'
                    'f) Investigar os acidentes, elaborar e colocar em prática os procedimentos '
                    'específicos, incluindo atribuições a todos que possam vir a participar nas '
                    'investigações.\n'
                    'g) Manter registros de acidentes e todos os detalhes necessários aos estudos '
                    'estatísticos e funcionais, da prevenção de acidentes.\n'
                    'h) Elaborar programas e ministrar treinamento geral e específico, de segurança e '
                    'medicina do trabalho e promover campanhas internas de prevenção de acidentes e '
                    'higiene do trabalho.'
                ),
            },
            {
                'secao': 'resp_seguranca',
                'titulo': 'DA SEGURANÇA DO TRABALHO',
                'conteudo_padrao': (
                    'a) Elaborar, estabelecer, implantar, assegurar a manutenção do programa, '
                    'acompanhar e monitorar, bem como promover o comprometimento, envolvimento, '
                    'treinamentos sobre a importância do programa e oferecer suporte técnico, de '
                    'acordo com a solicitação da empresa.'
                ),
            },
            {
                'secao': 'resp_cipa',
                'titulo': 'DO AGENTE DE PREVENÇÃO DE ACIDENTES / DESIGNADOS DE CIPA',
                'conteudo_padrao': (
                    'a) Conhecer o PGR da Empresa e relacionar-se com a Engenharia de Segurança do '
                    'Trabalho, no sentido de participar das ações de prevenção dos infortúnios e '
                    'doenças do trabalho junto aos empregados, como também no controle das ações de '
                    'segurança programadas na Empresa.\n'
                    'b) O representante designado pela {empresa}, devidamente treinado, irá atuar na '
                    'coordenação de todas as atividades relativas à Segurança e Saúde.'
                ),
            },
            {
                'secao': 'resp_medicina',
                'titulo': 'DA MEDICINA DO TRABALHO',
                'conteudo_padrao': (
                    'a) Informar, ao responsável pelo PGR, as alterações biológicas ocorridas com os '
                    'empregados;\n'
                    'b) Contribuir com as informações técnicas sobre os riscos à saúde, que podem ser '
                    'causados pelos agentes de risco;\n'
                    'c) Desenvolver o PCMSO.'
                ),
            },
            {
                'secao': 'resp_supervisao',
                'titulo': 'DA SUPERVISÃO',
                'conteudo_padrao': (
                    'a) Colaborar em todas as ações que se fizerem necessárias à implantação do '
                    'programa e promover a motivação de todas as pessoas da unidade a que pertence;\n'
                    'b) Informar aos trabalhadores de maneira apropriada e suficiente, sobre os riscos '
                    'ambientais que possam existir nos locais de trabalho e sobre os meios disponíveis '
                    'para prevenir ou limitar a ação dos mesmos.\n'
                    'c) Cumprir e fazer cumprir as disposições legais e regulamentares sobre segurança '
                    'e saúde no trabalho;\n'
                    'd) Informar aos trabalhadores, quanto aos riscos existentes no local de trabalho e '
                    'medidas prevenção adotadas para eliminação de riscos;\n'
                    'e) Inspecionar, permanentemente, as operações, equipamentos, máquinas e '
                    'edificações, em suas áreas de atuação, visando eliminar riscos de acidentes.\n'
                    'f) Permitir que representantes dos trabalhadores acompanhem a fiscalização dos '
                    'preceitos legais e regulamentares sobre segurança e saúde no trabalho;\n'
                    'g) Determinar procedimentos que devem ser adotados em caso de acidente ou doença '
                    'relacionada ao trabalho, incluindo a análise de suas causas;\n'
                    'h) Disponibilizar à Inspeção do Trabalho todas as informações relativas à '
                    'segurança e saúde no trabalho;\n'
                    'i) Implementar medidas de prevenção, ouvidos os trabalhadores, de acordo com a '
                    'seguinte ordem de prioridade;\n'
                    'j) Eliminação dos fatores de risco;\n'
                    'k) Informar à administração a ocorrência de acidentes do trabalho quando houver;\n'
                    'l) Minimização e controle dos fatores de risco, com a adoção de medidas '
                    'administrativas ou de organização do trabalho.'
                ),
            },
            {
                'secao': 'resp_empregados',
                'titulo': 'DOS EMPREGADOS',
                'conteudo_padrao': (
                    'a) Colaborar e participar da implantação e execução do PGR;\n'
                    'b) Seguir as orientações recebidas nos treinamentos do PGR, que participar;\n'
                    'c) Informar à chefia ocorrências que a seu julgamento ofereçam riscos ambientais.\n'
                    'd) Cumprir as disposições legais e regulamentares sobre segurança e saúde no '
                    'trabalho, inclusive as ordens de serviço expedidas pelo empregador;\n'
                    'e) Submeter-se aos exames médicos previstos nas NR;\n'
                    'f) Em caso de acidente de trabalho, informar à supervisão;\n'
                    'g) Colaborar com a organização na aplicação das NR;\n'
                    'h) Usar o equipamento de proteção individual (EPI) fornecido pelo empregador.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 6. DIRETRIZES
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'diretrizes',
                'titulo': '6. DIRETRIZES',
                'conteudo_padrao': '',
            },
            {
                'secao': 'diretrizes_estrategia',
                'titulo': 'ESTRATÉGIA',
                'conteudo_padrao': (
                    'DIREÇÃO\n'
                    'Este PGR está sendo elaborado pela área de Segurança do Trabalho da {empresa} e '
                    'com apoio operacional para implantação.\n\n'
                    'COLABORADORES\n'
                    'Todos os empregados em todos os cargos devem colaborar e participar de forma '
                    'efetiva dentro de seu setor de trabalho, com informações, para que este Programa '
                    'alcance seus objetivos.\n\n'
                    'RECURSOS\n'
                    'Deverão ser disponibilizados recursos humanos, materiais e financeiros, para a '
                    'elaboração e execução do "Programa"; das medidas de controle, dos monitoramentos '
                    'e das atualizações permanentes, conforme exigência Legal do Ministério do Trabalho '
                    'e Emprego.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 7. DESENVOLVIMENTO DO PGR
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'desenvolvimento',
                'titulo': '7. DESENVOLVIMENTO DO PGR',
                'conteudo_padrao': (
                    'ETAPAS\n\n'
                    'a) Antecipação:\n'
                    'Análise prévia de projetos, de instalações, de processos e de métodos de trabalho, '
                    'ou modificações nos mesmos, visando identificar os possíveis riscos, propor e '
                    'introduzir medidas para a sua redução ou eliminação.\n\n'

                    'b) Reconhecimento dos Riscos:\n'
                    'Aplicação das Ordens de Serviço de Segurança (OSS) conforme NR-1 a fim de divulgar '
                    'e antecipar a neutralização ou eliminação de atitudes e/ou condições de riscos '
                    'ambientais e de acidentes nas áreas de trabalho. Complementação com realização de '
                    'Análise Preliminar de Risco (APR), somente quando necessário.\n\n'
                    'Realização de Inspeções nos locais de trabalho para avaliação dos riscos e de '
                    'entrevistas com os empregados para obter as seguintes informações:\n'
                    '- Identificação;\n'
                    '- Fontes geradoras;\n'
                    '- Trajetórias e meio de propagação dos agentes;\n'
                    '- Identificação das funções e número de trabalhadores expostos aos riscos com a '
                    'realização do Grupo de exposição similar (GES);\n'
                    '- Caracterização da atividade e do tipo de exposição;\n'
                    '- Dados possíveis de comprometimentos à saúde no trabalho;\n'
                    '- Possíveis danos à saúde, conforme literatura técnica;\n'
                    '- Descrição das medidas de controle já existente.\n\n'
                    'Para cada GES então é realizada a identificação dos perigos levando em conta as '
                    'atividades, máquinas equipamentos, ferramentas, toxicidade dos produtos químicos '
                    'que utilizam, agentes e perigos presentes e a eficácia das medidas de proteção '
                    'existentes, verificação das condições sanitárias, de iluminação, ventilação e '
                    'estado de conservação. Em seguida realiza-se a avaliação qualitativa dos riscos e '
                    'a priorização de ações e/ou avaliações necessárias ao seu controle.\n\n'

                    'c) Avaliação:\n'
                    'As avaliações dos agentes físicos, químicos, biológicos e ergonômicos nas áreas de '
                    'trabalho serão realizadas, quando necessário ou durante a revisão do "Programa".'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 8. METODOLOGIA DE AVALIAÇÃO
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'metodologia_avaliacao',
                'titulo': '8. METODOLOGIA DE AVALIAÇÃO',
                'conteudo_padrao': (
                    'O PGR é parte integrante do conjunto mais amplo das iniciativas da empresa no '
                    'campo da preservação da saúde e integridade dos trabalhadores, devendo estar '
                    'articulado com o disposto nas demais NR\'s. Em especial com o Programa de Controle '
                    'Médico de Saúde Ocupacional - PCMSO, determinado de acordo com a NR - 7, '
                    'promovendo assim uma interligação entre os programas prevencionistas da empresa.'
                ),
            },
            {
                'secao': 'metodo_ruido',
                'titulo': 'AGENTE FÍSICO RUÍDO',
                'conteudo_padrao': (
                    'Conforme estabelece a Norma NHO 01 da Fundacentro, Normas Técnicas ANSI 4-1983 e '
                    'IEC 651-79 e Anexo 1 da NR 15 da Portaria 3214/78, o agente ruído será avaliado '
                    'por Dosimetria inicial na elaboração do PGR ou quando houver mudanças '
                    'significativas no ambiente de trabalho.'
                ),
            },
            {
                'secao': 'metodo_calor',
                'titulo': 'AGENTE FÍSICO CALOR',
                'conteudo_padrao': (
                    'A Norma Regulamentadora 15 (NR 15), em seu Anexo 3, especifica algumas condições '
                    'em que o ambiente, exposto ao calor, é considerado acima da tolerância para a '
                    'saúde do trabalhador. A medição de níveis de calor e temperatura, é através do '
                    'IBUTG (Índice de Bulbo Úmido Termômetro de Globo), que são calculados através de '
                    'medidores de stress térmico.'
                ),
            },
            {
                'secao': 'metodo_quimico',
                'titulo': 'AGENTES QUÍMICOS',
                'conteudo_padrao': (
                    'Inventário de agentes Químicos, utilizando as Fichas de Informação de Produtos '
                    'Químicos (FISPQ) fornecida pelo fabricante do produto, com critérios estabelecidos '
                    'pelos anexos 11 e 13 da NR 15 da Portaria 3214/78.'
                ),
            },
            {
                'secao': 'metodo_biologico',
                'titulo': 'AGENTES BIOLÓGICOS',
                'conteudo_padrao': (
                    'Consideram-se agentes biológicos as bactérias, fungos, bacilos, parasitas, '
                    'protozoários, vírus, microrganismos, entre outros, e a avaliação será qualitativa, '
                    'com base no serviço prestado.'
                ),
            },
            {
                'secao': 'metodo_ergonomico',
                'titulo': 'AGENTES ERGONÔMICOS',
                'conteudo_padrao': (
                    'Relatório de Avaliação de Condições Ergonômicas, conforme NR 17 da Portaria '
                    '3214/78, será realizado anualmente, ou quando houver mudanças significativas no '
                    'ambiente de trabalho.'
                ),
            },
            {
                'secao': 'metodo_mecanico',
                'titulo': 'AGENTES MECÂNICOS E ACIDENTES',
                'conteudo_padrao': (
                    'Por se tratar de risco de acidente sua metodologia e caracterização passa pela '
                    'utilização da ferramenta Análise Preliminar de Risco – APR, e considera as '
                    'situações que envolvam acidentes do tipo mecânico advindo de atividades "braçais", '
                    'de organização e distribuição de layout, atividades especificas que envolvam risco '
                    'de movimentação manual de peças ou equipamentos, bem como a movimentação do '
                    'trabalhador dentro da empresa, trabalhos em altura e trabalhos com eletricidade.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 9. INVENTÁRIO DE RISCOS — TABELAS DE CLASSIFICAÇÃO
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'inventario_riscos_intro',
                'titulo': '9. INVENTÁRIO DE RISCOS, PERIGOS, ASPECTOS E IMPACTOS',
                'conteudo_padrao': (
                    'RISCOS AMBIENTAIS E OCUPACIONAIS\n\n'
                    'Durante as avaliações serão considerados os seguintes aspectos:'
                ),
            },
            {
                'secao': 'inventario_tab_probabilidade',
                'titulo': 'TABELA 1 – CRITÉRIOS PARA GRADAÇÃO DA PROBABILIDADE DE OCORRÊNCIA DO DANO (P)',
                'conteudo_padrao': (
                    'Conceito que caracteriza a chance de que o perigo se concretize, ou seja, a '
                    'probabilidade de consequência prejudicial ao ser humano ou a empresa, caso '
                    'permita-se que as condições inseguras persistam.\n\n'
                    'PROBABILIDADE (P)\n'
                    'Nível | Classificação | Descrição | Frequência\n'
                    '1 | IMPROVÁVEL | Probabilidade de 1 ocorrência até uma vez em cada 50 anos | '
                    '(P ≤ 1 ocorrência/50 anos)\n'
                    '2 | REMOTO | Probabilidade de 1 ocorrência em cada 5 anos | '
                    '(1 ocorrência/50 anos < P ≤ 1 ocorrência/5 anos)\n'
                    '3 | OCASIONAL | Probabilidade de 1 ocorrência em cada ano | '
                    '(1 ocorrência/5 anos < P ≤ 1 ocorrência/ano)\n'
                    '4 | PROVÁVEL | Probabilidade de 1 ocorrência em cada mês | '
                    '(1 ocorrência/ano < P ≤ 1 ocorrência/mês)\n'
                    '5 | FREQUENTE | Probabilidade de ocorrência mais do que uma vez por mês | '
                    '(P > 1 ocorrência/mês)\n\n'
                    'OBSERVAÇÃO\n'
                    'Se a exposição a contaminantes atmosféricos ou ao ruído for avaliada como '
                    'excessiva, ou seja, maior que o limite de exposição permitido, ou acima do nível '
                    'de ação, deve-se definir o índice de probabilidade de ocorrência do dano estimado '
                    'como 1, 2, 3, 4 ou 5 por julgamento profissional do avaliador, conforme o grau de '
                    'adequação do EPI ao tipo de exposição, sua manutenção e uso efetivo.'
                ),
            },
            {
                'secao': 'inventario_tab_gravidade',
                'titulo': 'TABELA 2 – CRITÉRIOS PARA GRADAÇÃO DA GRAVIDADE DO DANO (G)',
                'conteudo_padrao': (
                    'Para a gradação da gravidade do dano potencial (efeito crítico) atribui-se um '
                    'índice de gravidade (G) variando de 1 a 5 conforme os critérios da tabela '
                    'abaixo.\n\n'
                    'GRAVIDADE (G)\n'
                    'Nível | Classificação | Descrição\n'
                    '1 | NEGLIGENCIÁVEL | Danos pessoais ligeiros ou sem danos, mal-estar passageiro, '
                    'pequenas lesões sem qualquer tipo de incapacidade. (Sem baixa)\n'
                    '2 | MARGINAL | Danos ou doenças ocupacionais menores com ou sem incapacidade '
                    'temporária sem assistência médica especializada, primeiro socorro. (Lesões ou '
                    'doenças até 10 dias de baixa)\n'
                    '3 | MODERADO | Danos ou doenças ocupacionais de média gravidade, requerendo '
                    'assistência médica e baixa com duração superior a 10 dias. (Lesões ou doenças '
                    'suscetíveis de provocar baixa de duração compreendida entre 11 e 60 dias)\n'
                    '4 | GRAVE | Danos ou doenças ocupacionais graves, lesões com incapacidade '
                    'temporária ou parcial permanente, internamento hospitalar. (Incapacidade parcial '
                    'permanente, ou lesões ou doenças suscetíveis de provocar baixa de duração superior '
                    'a 60 dias)\n'
                    '5 | CRÍTICO | Morte ou incapacidade total permanente'
                ),
            },
            {
                'secao': 'inventario_tab_exposicao',
                'titulo': 'TABELA 3 – MONITORAMENTO DA EXPOSIÇÃO (GRAU DE EXPOSIÇÃO AO RISCO)',
                'conteudo_padrao': (
                    'Para a gradação da exposição ao dano potencial (efeito crítico) atribui-se um '
                    'índice de exposição (E) variando de 1 a 5 conforme os critérios da Tabela 3.\n\n'
                    'EXPOSIÇÃO (E)\n'
                    'Nível | Classificação | Descrição\n'
                    '1 | ESPORÁDICA | Exposição acontece pelo menos uma vez por ano por um período '
                    'curto de tempo ou nunca acontece\n'
                    '2 | POUCO FREQUENTE | Exposição acontece algumas vezes por mês\n'
                    '3 | OCASIONAL | Exposição acontece várias vezes por semana ou várias vezes por dia '
                    'por períodos curtos (< 60 min.)\n'
                    '4 | FREQUENTE | Exposição ocorre várias vezes por dia por períodos não prolongados '
                    '(< 120 min. seguidos)\n'
                    '5 | CONTÍNUA | Exposição por períodos diários ou várias vezes por dia por períodos '
                    'prolongados (> 120 min. seguidos)'
                ),
            },
            {
                'secao': 'inventario_tab_matriz_severidade',
                'titulo': 'TABELA 4 – MATRIZ DE RISCO PARA ESTIMAR A SEVERIDADE DO RISCO',
                'conteudo_padrao': (
                    'Estimar e definir a categoria de cada risco, a partir da combinação dos valores '
                    'atribuídos para exposição (E) e gravidade (G) do dano, utilizando a matriz '
                    'apresentada na Tabela 4.\n\n'
                    'MATRIZ GRAVIDADE (G) x EXPOSIÇÃO (E) → SEVERIDADE\n\n'
                    '         |  G=1  |  G=2  |  G=3  |  G=4  |  G=5\n'
                    'E=1      |   A   |   A   |   A   |   B   |   B\n'
                    'E=2      |   A   |   B   |   B   |   C   |   D\n'
                    'E=3      |   A   |   B   |   C   |   D   |   D\n'
                    'E=4      |   B   |   C   |   D   |   E   |   E\n'
                    'E=5      |   B   |   D   |   D   |   E   |   E'
                ),
            },
            {
                'secao': 'inventario_tab_severidade',
                'titulo': 'TABELA 5 – CRITÉRIOS PARA GRADAÇÃO DA SEVERIDADE DO DANO (S)',
                'conteudo_padrao': (
                    'SEVERIDADE (S)\n'
                    'Nível | Classificação\n'
                    'A | NEGLIGENCIÁVEL\n'
                    'B | MARGINAL\n'
                    'C | GRAVE\n'
                    'D | MUITO GRAVE\n'
                    'E | CRÍTICO'
                ),
            },
            {
                'secao': 'inventario_tab_acoes_mitigacao',
                'titulo': 'TABELA 6 – AÇÕES A SEREM ADOTADAS DE FORMA A MITIGAR O RISCO',
                'conteudo_padrao': (
                    'Serão priorizadas as medidas de controle coletivo dos agentes nocivos à Segurança '
                    'e Saúde dos Trabalhadores de acordo com a seguinte ordem abaixo.\n\n'
                    'Priorização | Medida | Significado | Descrição | Redução do Risco\n'
                    '1° | E - Eliminação | Eliminação total da fonte de risco | 100%\n'
                    '2° | S - Substituição ou Minimização | Substituição de matérias-primas, '
                    'equipamentos e procedimento de trabalho | 40%\n'
                    '3° | CE - Controle de Engenharia | Enclausuramento, adaptação do ambiente de '
                    'trabalho, automatização do processo e etc. | 25%\n'
                    '4° | CA - Controle Administrativo | Sinalização, treinamentos, exames médicos, '
                    'implementação de procedimento de segurança e etc. | 15%\n'
                    '5° | DP - Dispositivo de Proteção | Uso de EPIs e implementação de EPCs | 10%\n\n'
                    'Quando, em qualquer fase do Programa, os riscos detectados ultrapassarem os '
                    'valores limites das normas utilizadas, serão adotadas medidas de controle, com o '
                    'objetivo de eliminar ou reduzir a exposição ao risco.\n\n'
                    'Situações de risco grave e iminente serão comunicados ao supervisor da área, que '
                    'deverá tomar medidas para eliminação do agente causador, sob risco de interdição '
                    'do local.'
                ),
            },
            {
                'secao': 'inventario_tab_priorizacao',
                'titulo': 'TABELA 7 – CRITÉRIOS PARA PRIORIZAÇÃO DAS AÇÕES',
                'conteudo_padrao': (
                    'Para priorização das ações será avaliado a Severidade (S) após a verificação das '
                    'medidas de controle adotadas, juntamente com o grau de Probabilidade (P).\n\n'
                    'RISCO (R)\n'
                    'Classificação do Risco | Prazo para Ações\n'
                    'Baixo | Aceitável\n'
                    'Tolerável | < 01 (um) ano\n'
                    'Moderado | < 06 (seis) meses\n'
                    'Significativo | Paralização\n\n'
                    'Se o risco for considerado aceitável, não será necessário adotar ações de '
                    'mitigação do risco.'
                ),
            },
            {
                'secao': 'inventario_tab_matriz_risco',
                'titulo': 'TABELA 8 – TABELA PARA ESTIMAR A CLASSIFICAÇÃO DO RISCO',
                'conteudo_padrao': (
                    'MATRIZ SEVERIDADE (S) x PROBABILIDADE (P) → CLASSIFICAÇÃO DO RISCO\n\n'
                    '         |  S=A  |  S=B  |  S=C  |  S=D  |  S=E\n'
                    'P=1      |   B   |   B   |   B   |   T   |   T\n'
                    'P=2      |   B   |   B   |   T   |   M   |   M\n'
                    'P=3      |   B   |   T   |   M   |   M   |   S\n'
                    'P=4      |   T   |   M   |   M   |   S   |   S\n'
                    'P=5      |   T   |   M   |   S   |   S   |   S\n\n'
                    'Legenda: B = Baixo | T = Tolerável | M = Moderado | S = Significativo\n\n'
                    'Caso a tabela 7 indique que para determinado risco não é necessário realizar uma '
                    'ação específica, mas a empresa venha a receber uma autuação de organismo '
                    'fiscalizador, ou venha acontecer algum acidente em decorrência do perigo '
                    'relacionado ao risco, deve-se realizar alguma ação para minimizar esse risco, '
                    'independente do resultado obtido na tabela.\n\n'
                    'O plano de ação deve ser amplo e deve atender as reais necessidades de melhoria '
                    'da empresa, não se prendendo somente as exigências da NR 01.'
                ),
            },
            {
                'secao': 'inventario_excecoes',
                'titulo': 'EXCEÇÕES NA DEFINIÇÃO DA PERIODICIDADE DE MONITORAMENTOS',
                'conteudo_padrao': (
                    'Ruído – se as exposições forem superiores ao limite de tolerância ou nível de '
                    'ação, mas as condições se mantiverem constantes e o controle for baseado apenas no '
                    'uso de equipamento de proteção individual avaliado como eficaz, a periodicidade do '
                    'monitoramento poderá ser reduzida a critério do avaliador.\n\n'
                    'Também a critério do avaliador a periodicidade do monitoramento para outras '
                    'exposições poderá ser reduzida se as condições de trabalho forem estáveis e a '
                    'incerteza das avaliações for baixa, exceto se houver exigência legal em contrário.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 10. PLANO DE AÇÃO
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'plano_acao',
                'titulo': '10. PLANO DE AÇÃO',
                'conteudo_padrao': (
                    'No Programa Gerenciamento de Riscos – PGR serão observadas e seguidas as '
                    'seguintes etapas no plano de ação:\n\n'
                        'a) Antecipação e Reconhecimento dos riscos;\n'
                        'b) Estabelecimento de prioridades e metas de avaliação e controle;\n'
                        'c) Avaliação dos riscos e da exposição dos trabalhadores;\n'
                        'd) Implantação de medidas de controle e avaliação de sua eficácia;\n'
                        'e) Monitoramento da exposição aos riscos;\n'
                        'f) Registro e divulgação de dados através de treinamentos informando sobre os '
                        'riscos identificados;\n'
                        'g) Prevenção, eliminação ou redução de agentes prejudiciais à saúde ou à '
                        'integridade física dos trabalhadores.'
                ),
            },
            {
                'secao': 'plano_acao_documentacao',
                'titulo': 'DOCUMENTAÇÃO',
                'conteudo_padrao': (
                    'O PGR deve conter, no mínimo, os seguintes documentos:\n'
                        'a) inventário de riscos;\n'
                        'b) plano de ação.\n\n'
                    'Como metodologia de execução do plano de ação, estabeleceu o método 5 porquês '
                    'como ferramenta para construção objetiva das soluções que serão implantadas neste '
                    'PGR, desta forma o gerenciamento dos riscos ocupacionais poderá estar detalhado '
                    'neste documento e seu resumo controlado pela planilha GRO.\n\n'
                    'As metodologias de investigação vão auxiliar no mapeamento e na padronização de '
                    'processos de análise de riscos, cumprindo suas etapas a indefinição dará lugar à '
                    'produtividade na resolução dos problemas (perigos) detectados no inventário de '
                    'perigos, riscos, aspectos e impactos tendo em vista que todos os envolvidos têm o '
                    'conhecimento exato de o que fazer, quando, onde, de que forma, porquê, etc.\n\n'
                    'Como resultado, além do ganho de produtividade, constrói-se sinergia que, hoje em '
                    'dia é extremamente importante para construção de um diferencial estratégico para '
                    'qualquer negócio.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 11. MEDIDAS DE PROTEÇÃO
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'medidas_protecao',
                'titulo': '11. MEDIDAS DE PROTEÇÃO',
                'conteudo_padrao': '',
            },
            {
                'secao': 'medidas_epc',
                'titulo': 'MEDIDAS DE PROTEÇÃO COLETIVA',
                'conteudo_padrao': (
                    'A {empresa} faz uso de suas normas e seus procedimentos para orientar, treinar e '
                    'capacitar os funcionários quanto às medidas de controle coletivos que proporcionam '
                    'maior segurança na execução de suas tarefas. Através destes treinamentos e '
                    'procedimentos os funcionários recebem orientações diversas tais como:\n\n'
                    'a) Sinalizar à área para a execução da tarefa de forma segura tanto para os '
                    'envolvidos diretos quanto indiretos, com a utilização de cones, fita zebrada, '
                    'placas de informações, colete refletivo, alerta sonoro e iluminação.\n'
                    'b) Fazer uso de sistemas de bloqueio de fontes hidráulicas, mecânicas, elétricas '
                    'e outras fontes geradoras de riscos.\n'
                    'c) Os funcionários são orientados a respeitar as normas de nossos clientes no '
                    'que diz respeito à utilização e conservação dos equipamentos e das medidas de '
                    'proteção coletiva oferecidas pelos nossos clientes, como por exemplo, corrimão, '
                    'cabos guia, passarelas, regras de trânsito, guarda-corpo, além de orientação '
                    'básicas de utilização de equipamentos de combate a princípio de incêndios.'
                ),
            },
            {
                'secao': 'medidas_administrativas',
                'titulo': 'MEDIDAS ADMINISTRATIVAS OU DE ORGANIZAÇÃO DO TRABALHO',
                'conteudo_padrao': (
                    'A {empresa} possui procedimentos de segurança e saúde ocupacional, que são '
                    'repassados para os funcionários através de treinamentos e material de informações '
                    'contendo todas as normas da empresa no que diz respeito à segurança e saúde '
                    'ocupacional.\n\n'
                    'Os funcionários recebem uma ordem de serviço (OSS) contendo suas obrigações no '
                    'que diz respeito à segurança e saúde, assim como as penalidades pelo '
                    'descumprimento das normas de segurança impostas pela legislação vigente, pela '
                    '{empresa} e pelo Cliente.'
                ),
            },
            {
                'secao': 'medidas_epi',
                'titulo': 'MEDIDAS DE ORDEM INDIVIDUAL (EPI)',
                'conteudo_padrao': (
                    'A {empresa}faz uso de suas normas e seus procedimentos para orientar, treinar '
                    'e capacitar os funcionários quanto às medidas ordem individuais (EPI) que proporcionam '
                    'maior segurança na execução de suas tarefas.\n'
                    'Quando comprovadas a inviabilidade técnica ou econômica para a implementação da proteção '
                    'coletiva, a empresa fornecerá EPI conforme procedimentos específicos para as áreas envolvidas. '
                    'O fornecimento do EPI, quando aplicável, para os colaboradores deve ser controlado por cada '
                    'gerência vinculada às áreas operacionais. Os Coordenadores, Líderes e Supervisores deverão '
                    'efetuar o registro e controle de entrega de EPI conforme Planilha de Controle de EPI '
                    '(Lista de Formulários – QHSE 06).\n'
                    'Depois de preenchida, esta planilha deve ficar armazenada nos arquivos das áreas operacionais '
                    'para fins de registros e possível evidência requerida por órgãos trabalhistas e / ou clientes.\n'
                    'Cabe ao empregador quanto ao EPI:\n'
                        'a) adquirir o EPI adequado ao risco de cada atividade;\n'
                        'b) exigir seu uso;\n'
                        'c) fornecer ao trabalhador somente o aprovado pelo órgão nacional competente em '
                        'matéria de segurança e saúde no trabalho;\n'
                        'd) orientar e treinar o trabalhador sobre o uso adequado guarda e conservação;\n'
                        'e) substituir imediatamente, quando danificado ou extraviado;\n'
                        'f) responsabilizar-se pela higienização e manutenção periódica;\n'
                        'g) comunicar ao MTE qualquer irregularidade observada;\n'
                        'h) registrar o seu fornecimento ao trabalhador, podendo ser adotados livros, '
                        'fichas ou sistema eletrônico.'
                ),
            },
            {
                'secao': 'medidas_uso_epi',
                'titulo': 'USO, GUARDA, HIGIENIZAÇÃO E CONSERVAÇÃO DO EPI',
                'conteudo_padrao': (
                    'O EPI deve ser utilizado apenas para a finalidade a que se destina e guardado com '
                    'o próprio usuário. Sua conservação deve ser realizada conforme treinamento aplicado '
                    'pela {empresa} ou instruções de uso definidas pelo fabricante.\n\n'
                    'A {empresa} não realiza e nem solicita aos fabricantes readequação de EPI. O EPI '
                    'quando apresenta algum tipo de problema é imediatamente substituído. Em caso de '
                    'C.A vencido a {empresa} entra em contato com o fornecedor para verificar a '
                    'possibilidade de troca do mesmo, ou o fornecimento de documento de solicitação de '
                    'renovação do C.A junto ao MTE, quando vencido o prazo de validade estipulado pelo '
                    'órgão nacional competente em matéria de segurança e saúde do trabalho. Quando '
                    'nenhuma dessas opções for obtida o EPI deverá ser substituído.\n\n'
                    'A {empresa} não realiza higienização do EPI, eles são simplesmente '
                    'substituídos.\n\n'
                    'Cabe ao colaborador quanto ao EPI:\n'
                        'a) Usar o EPI apenas para a finalidade a que se destina;\n'
                        'b) responsabilizar-se pela guarda e conservação;\n'
                        'c) comunicar ao empregador qualquer alteração que o torne impróprio para uso;\n'
                        'd) cumprir as determinações do empregador sobre o uso adequado.'
                ),
            },
            {
                'secao': 'medidas_substituicao_epi',
                'titulo': 'SUBSTITUIÇÃO E REPOSIÇÃO DO EPI',
                'conteudo_padrao': (
                    'É responsabilidade do empregado, comunicar a sua gerência imediata, sobre '
                    'qualquer alteração no EPI que o torne impróprio para uso, além da perda ou '
                    'extravio do equipamento solicitando sua reposição. No caso de EPI impróprio para '
                    'uso, o mesmo deverá ser devolvido na ocasião de sua reposição, para posterior '
                    'descarte.'
                ),
            },
            {
                'secao': 'medidas_protecao_geral',
                'titulo': 'MEDIDAS DE PROTEÇÃO – EPC, EPI E OUTRAS',
                'conteudo_padrao': (
                        'a) Medidas que eliminam ou reduzam a utilização ou a formação de agentes '
                        'prejudiciais à saúde;\n'
                        'b) Medidas que previnem a liberação ou disseminação desses agentes no ambiente de '
                        'trabalho;\n'
                        'c) Medidas que reduzem os níveis ou a concentração desses agentes nos ambientes '
                        'de trabalho;\n'
                        'd) Medidas de caráter administrativo ou de organização do trabalho;\n'
                        'e) Medidas de ordem individual (Equipamento de Proteção Individual – EPI):\n'
                        'f) Seleção do EPI adequado tecnicamente ao risco a que o trabalhador está exposto '
                        'e a atividade exercida;\n'
                        'g) Programa de treinamento dos trabalhadores quanto a sua correta utilização e '
                        'orientação sobre as limitações de proteção que o EPI oferece;\n'
                        'h) Critérios e mecanismos de avaliação da eficácia das medidas de proteção, '
                        'conforme análise e dados do PCMSO.'
                ),
            },
            {
                'secao': 'medidas_monitoramento',
                'titulo': 'MONITORAMENTO DO RISCO',
                'conteudo_padrao': (
                    'Todas as medidas de controle, existentes ou implantadas, serão avaliadas '
                    'periodicamente, tendo como base as avaliações ambientais e o PCMSO.\n\n'
                    'O PGR também será avaliado periodicamente, em concordância com o cronograma '
                    'implantado e por período nunca superior a 2 (dois) anos.'
                ),
            },
            {
                'secao': 'medidas_registro_divulgacao',
                'titulo': 'REGISTRO E DIVULGAÇÃO DE DADOS',
                'conteudo_padrao': (
                    'O registro e a divulgação de dados são estruturados de forma a constituir um '
                    'histórico técnico e administrativo do desenvolvimento do Programa.\n\n'
                    'Os dados serão mantidos por um período mínimo de 20 (vinte) anos. O registro de '
                    'dados estará sempre disponível aos trabalhadores interessados ou de seus '
                    'representantes legais e para as autoridades competentes.'
                ),
            },
            {
                'secao': 'medidas_recomendacao_epi',
                'titulo': 'RECOMENDAÇÃO ESPECIAL (EPI)',
                'conteudo_padrao': (
                    'Deverá ser utilizada a "Ficha de Controle de EPIs – Equipamentos de Proteção '
                    'Individual", conforme determinação de ordem legal, para registro de 1ª (primeira) '
                    'dotação e substituição dos EPIs (Equipamentos de Proteção Individual) quando '
                    'necessário, em função dos riscos existentes no ambiente de trabalho.\n\n'
                    'CONSOLIDAÇÃO DAS LEIS DO TRABALHO – CLT\n'
                    'Art. 158 – Cabe aos empregados:\n'
                    'I – Observar as normas de segurança e medicina do trabalho, inclusive as instruções '
                    'de que trata o item II do artigo anterior;\n'
                    'II – Colaborar com a empresa na aplicação dos dispositivos deste capítulo.\n\n'
                    'Parágrafo Único: Constitui ato faltoso do empregado a recusa injustificada:\n'
                    'a) ...\n'
                    'b) ao uso dos equipamentos de proteção individual fornecidos pela empresa.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 12. CRONOGRAMA DE AÇÕES
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'cronograma_acoes',
                'titulo': '12. CRONOGRAMA DE AÇÕES',
                'conteudo_padrao': (
                    'O cronograma de ações abaixo apresenta as atividades necessárias para o '
                    'cumprimento do PGR, com seus respectivos públicos alvo, periodicidade de '
                    'realização e próxima avaliação/revisão prevista.\n\n'
                    'CM = contrato de manutenção\n\n'
                    '*** O cronograma detalhado é gerado automaticamente a partir dos dados cadastrados '
                    'no sistema (model CronogramaAcaoPGR). ***'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 13. DIVULGAÇÃO DO PROGRAMA
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'divulgacao',
                'titulo': '13. DIVULGAÇÃO DO PROGRAMA',
                'conteudo_padrao': (
                    'Os documentos e os procedimentos operacionais que integram o Programa de '
                    'Gerenciamento de Risco (PGR) estarão disponíveis aos empregados.\n\n'
                    'A atualização do PGR será realizada quando da ocorrência de alterações '
                    'significativas de ordem tecnológica, operacional, legal ou regulatória que '
                    'provoquem a necessidade de adequação dos documentos que o integram ou ainda '
                    'quando for recomendado na auditoria anual.\n\n'
                    'Cabe aos responsáveis pelas respectivas áreas procederem a divulgação das '
                    'atualizações dos documentos que integram o PGR, após as devidas aprovações, '
                    'respeitadas eventuais restrições para o manuseio e circulação quando se tratarem '
                    'de documentos controlados.\n\n'
                    'Esses dados foram levantados por profissionais do departamento de QHSE '
                    '(Qualidade, Saúde, Segurança e Meio Ambiente) com a participação dos responsáveis '
                    'pelas áreas analisadas, designados de CIPA e dos próprios trabalhadores e '
                    'inseridos no Inventário de Riscos deste PGR.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 14. RECOMENDAÇÕES GERAIS
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'recomendacoes',
                'titulo': '14. RECOMENDAÇÕES GERAIS',
                'conteudo_padrao': (
                    '- Aplicação de medidas, sempre que necessárias, de caráter administrativo ou da '
                    'organização do trabalho.\n'
                    '- Aplicação de Treinamento de Segurança em geral, sobre Uso de EPI, Cuidados com '
                    'produtos de químicos, Levantamento de peso e Trabalho em Altura, assim como outros '
                    'treinamentos que se fizerem necessários;\n'
                    '- Aplicação de Treinamento para membro designado de segurança da CIPA, no setor, '
                    'em cumprimento com a portaria 3214 de 08/06/78 – NR 05;\n'
                    '- Dotação de creme protetor para as mãos para os funcionários que tiverem contato '
                    'direto com graxas, óleos e outros produtos químicos durante a jornada de '
                    'trabalho;\n'
                    '- Fornecimento de EPIs adequados de acordo com Ficha Técnica de Classificação de '
                    'EPI por Função;\n'
                    '- Orientações sobre o uso correto e higiênico dos vestiários e asseio pessoal;\n'
                    '- Execução do Gerenciamento de Riscos através da observação de segurança e uso '
                    'dos EPIs;\n'
                    '- Guarda de documentação do controle das intervenções de segurança do trabalho;\n'
                    '- Aplicação de rígido controle médico dos empregados.'
                ),
            },

            # ══════════════════════════════════════════════════════════
            # 15. LEGISLAÇÃO COMPLEMENTAR
            # ══════════════════════════════════════════════════════════
            {
                'secao': 'legislacao',
                'titulo': '15. LEGISLAÇÃO COMPLEMENTAR',
                'conteudo_padrao': (
                    'Além de atender a Portaria SEPRT n° 6730 de 09 de março de 2020, o PGR atende '
                    'uma série de outras normas e legislações complementares:\n\n'
                    '- PORTARIA 3214/78 – NORMAS REGULAMENTADORAS\n'
                    '- NORMAS DE HIGIENE OCUPACIONAL – FUNDACENTRO\n'
                    '- ABNT ISO NBR 45001 – SISTEMA DE GESTÃO DE SEGURANÇA E SAÚDE OCUPACIONAL\n'
                    '- ABNT ISO NBR 31000 – GESTÃO DE RISCOS – DIRETRIZES\n'
                    '- ABNT NBR 5413 – ILUMINAÇÃO DE INTERIORES\n'
                    '- ABNT NBR 10152 – NÍVEL DE RUÍDO PARA CONFORTO ACÚSTICO'
                ),
            },
        ]


