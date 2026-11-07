"""Construção da ontologia OWL 2 de atividades físicas (Questões 9 e 15).

Executar ``python ontologia_atividades.py`` regera os três arquivos ``.owl``
versionados nesta pasta:

* ``ontologia_atividades_fisicas.owl``: ontologia principal (TBox + ABox);
* ``ontologia_atividades_fisicas_inconsistente.owl``: cópia com um erro de
  cadastro que torna a ontologia inconsistente;
* ``ontologia_atividades_fisicas_insatisfazivel.owl``: cópia consistente, mas
  com uma classe que não pode ter instâncias.

Valores de MET são aproximações arredondadas do Compendium of Physical
Activities (Ainsworth et al., 2011). Custos e locais são fictícios, ambientados
em Maceió.
"""

from __future__ import annotations

from pathlib import Path

from owlready2 import (
    AllDifferent,
    AllDisjoint,
    AnnotationProperty,
    ConstrainedDatatype,
    DataProperty,
    FunctionalProperty,
    ObjectProperty,
    OneOf,
    Ontology,
    PropertyChain,
    Thing,
    TransitiveProperty,
    World,
    locstr,
)

IRI = "http://ic.ufal.br/ecom031/lista2/atividades-fisicas"
PASTA = Path(__file__).resolve().parent
ARQUIVO_OWL = PASTA / "ontologia_atividades_fisicas.owl"
ARQUIVO_INCONSISTENTE = PASTA / "ontologia_atividades_fisicas_inconsistente.owl"
ARQUIVO_INSATISFAZIVEL = PASTA / "ontologia_atividades_fisicas_insatisfazivel.owl"

LIMIAR_MET_VIGOROSO = 6.0  # ACSM: >= 6 MET é vigoroso; 3 a 6, moderado
LIMIAR_MET_MODERADO = 3.0
IDADE_IDOSO = 60  # Estatuto da Pessoa Idosa
MINUTOS_OMS = 150  # recomendação semanal mínima da OMS para adultos
MESES_INICIANTE = 6
IMC_OBESIDADE = 30.0


def _doc(entidade, rotulo: str, comentario: str = "") -> None:
    """Anota rótulo e comentário em português do Brasil."""
    entidade.label = [locstr(rotulo, lang="pt-BR")]
    if comentario:
        entidade.comment = [locstr(comentario, lang="pt-BR")]


# (nome, modalidade, impacto, MET, nível técnico, locais, custo R$/mês,
#  benefícios, partes sobrecarregadas, mínimo de participantes, rótulo)
ATIVIDADES = [
    ("caminhada", "AtividadeAerobica", "baixo", 3.5, "basico",
     ["orla_de_ponta_verde", "parque_municipal_de_maceio"], 0.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "relaxamento"], [], 1, "Caminhada"),
    ("corrida", "AtividadeAerobica", "alto", 9.8, "basico",
     ["orla_de_ponta_verde", "parque_municipal_de_maceio"], 0.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico"], ["joelho", "tornozelo"], 1, "Corrida"),
    ("ciclismo_na_orla", "AtividadeAerobica", "baixo", 8.0, "intermediario",
     ["orla_de_ponta_verde"], 0.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico"], [], 1, "Ciclismo na orla"),
    ("spinning", "AtividadeAerobica", "baixo", 8.5, "basico",
     ["academia_do_bairro"], 120.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico"], [], 1, "Spinning"),
    ("natacao", "AtividadeAerobica", "baixo", 5.8, "intermediario",
     ["piscina_do_clube"], 180.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "forca_muscular"], ["ombro"], 1, "Natação"),
    ("hidroginastica", "AtividadeAerobica", "baixo", 5.5, "basico",
     ["piscina_do_clube"], 150.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "interacao_social"], [], 1, "Hidroginástica"),
    ("zumba", "AtividadeAerobica", "moderado", 6.5, "basico",
     ["academia_do_bairro"], 100.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "interacao_social"],
     ["joelho", "tornozelo"], 1, "Zumba"),
    ("stand_up_paddle", "AtividadeAerobica", "baixo", 5.0, "intermediario",
     ["praia_da_pajucara"], 150.0,
     ["equilibrio", "forca_muscular", "relaxamento"], ["ombro"], 1, "Stand up paddle"),
    ("musculacao", "AtividadeDeForca", "baixo", 3.5, "basico",
     ["academia_do_bairro"], 100.0, ["forca_muscular"], [], 1, "Musculação"),
    ("treino_funcional", "AtividadeDeForca", "moderado", 5.0, "basico",
     ["parque_municipal_de_maceio", "academia_do_bairro"], 90.0,
     ["forca_muscular", "equilibrio", "gasto_calorico"], [], 1, "Treino funcional"),
    ("crossfit", "AtividadeDeForca", "alto", 8.0, "avancado",
     ["box_de_crossfit"], 300.0,
     ["forca_muscular", "condicionamento_cardiorrespiratorio", "gasto_calorico", "interacao_social"],
     ["coluna_lombar", "joelho", "ombro"], 1, "CrossFit"),
    ("pilates", "AtividadeDeFlexibilidade", "baixo", 3.0, "basico",
     ["estudio_de_pilates_e_yoga"], 280.0,
     ["forca_muscular", "flexibilidade", "equilibrio"], [], 1, "Pilates"),
    ("yoga", "AtividadeDeFlexibilidade", "baixo", 2.5, "basico",
     ["estudio_de_pilates_e_yoga"], 160.0,
     ["flexibilidade", "equilibrio", "relaxamento"], [], 1, "Yoga"),
    ("alongamento", "AtividadeDeFlexibilidade", "baixo", 2.3, "basico",
     ["parque_municipal_de_maceio"], 0.0, ["flexibilidade", "relaxamento"], [], 1, "Alongamento"),
    ("tai_chi_chuan", "AtividadeDeFlexibilidade", "baixo", 3.0, "basico",
     ["parque_municipal_de_maceio"], 0.0,
     ["equilibrio", "relaxamento", "flexibilidade"], [], 1, "Tai chi chuan"),
    ("futebol_society", "Esporte", "alto", 7.0, "intermediario",
     ["campo_society"], 60.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "interacao_social"],
     ["joelho", "tornozelo"], 10, "Futebol society"),
    ("volei_de_praia", "Esporte", "alto", 8.0, "intermediario",
     ["quadra_de_areia_da_jatiuca"], 0.0,
     ["condicionamento_cardiorrespiratorio", "interacao_social"],
     ["ombro", "joelho", "coluna_lombar"], 4, "Vôlei de praia"),
    ("beach_tennis", "Esporte", "moderado", 6.0, "intermediario",
     ["quadra_de_areia_da_jatiuca"], 200.0,
     ["condicionamento_cardiorrespiratorio", "gasto_calorico", "interacao_social"], ["ombro"], 2,
     "Beach tennis"),
]

# (nome, classes, rótulo)
LOCAIS = [
    ("orla_de_ponta_verde", ["LocalAoArLivre"], "Orla de Ponta Verde"),
    ("parque_municipal_de_maceio", ["LocalAoArLivre"], "Parque Municipal de Maceió"),
    ("praia_da_pajucara", ["LocalAoArLivre", "LocalAquatico"], "Praia da Pajuçara"),
    ("quadra_de_areia_da_jatiuca", ["LocalAoArLivre"], "Quadra de areia da Jatiúca"),
    ("campo_society", ["LocalAoArLivre"], "Campo society"),
    ("piscina_do_clube", ["LocalFechado", "LocalAquatico"], "Piscina coberta do clube"),
    ("academia_do_bairro", ["LocalFechado"], "Academia do bairro"),
    ("estudio_de_pilates_e_yoga", ["LocalFechado"], "Estúdio de pilates e yoga"),
    ("box_de_crossfit", ["LocalFechado"], "Box de CrossFit"),
]

# (nome, partes que integra, rótulo)
PARTES_DO_CORPO = [
    ("tronco", [], "Tronco"),
    ("coluna_vertebral", ["tronco"], "Coluna vertebral"),
    ("coluna_lombar", ["coluna_vertebral"], "Coluna lombar"),
    ("membro_inferior", [], "Membro inferior"),
    ("joelho", ["membro_inferior"], "Joelho"),
    ("tornozelo", ["membro_inferior"], "Tornozelo"),
    ("membro_superior", [], "Membro superior"),
    ("ombro", ["membro_superior"], "Ombro"),
    ("sistema_cardiovascular", [], "Sistema cardiovascular"),
]

# (nome, classe, partes afetadas, rótulo)
CONDICOES = [
    ("artrose_no_joelho", "CondicaoArticular", ["joelho"], "Artrose no joelho"),
    ("entorse_recorrente_de_tornozelo", "CondicaoArticular", ["tornozelo"],
     "Entorse recorrente de tornozelo"),
    ("tendinite_no_ombro", "CondicaoArticular", ["ombro"], "Tendinite no ombro"),
    ("hernia_de_disco", "CondicaoDaColuna", ["coluna_vertebral"], "Hérnia de disco"),
    ("hipertensao_nao_controlada", "CondicaoCardiovascular", ["sistema_cardiovascular"],
     "Hipertensão não controlada"),
]

BENEFICIOS = [
    ("condicionamento_cardiorrespiratorio", "Condicionamento cardiorrespiratório"),
    ("gasto_calorico", "Gasto calórico"),
    ("forca_muscular", "Força muscular"),
    ("flexibilidade", "Flexibilidade"),
    ("equilibrio", "Equilíbrio"),
    ("relaxamento", "Relaxamento"),
    ("interacao_social", "Interação social"),
]

# (nome, benefícios de que depende, rótulo)
OBJETIVOS = [
    ("perder_peso", ["gasto_calorico"], "Perder peso"),
    ("ganhar_forca", ["forca_muscular"], "Ganhar força"),
    ("melhorar_condicionamento", ["condicionamento_cardiorrespiratorio"], "Melhorar o condicionamento"),
    ("ganhar_flexibilidade", ["flexibilidade"], "Ganhar flexibilidade"),
    ("prevenir_quedas", ["equilibrio", "forca_muscular"], "Prevenir quedas"),
    ("reduzir_estresse", ["relaxamento"], "Reduzir o estresse"),
    ("socializar", ["interacao_social"], "Socializar"),
]

# (nome, idade, IMC, minutos ativos/semana, meses de experiência, condições
#  (None = não informado), objetivos, orçamento R$/mês, rótulo)
USUARIOS = [
    ("maria", 67, 27.0, 60, 0, ["artrose_no_joelho"], ["prevenir_quedas", "socializar"], 200.0,
     "Maria (67 anos)"),
    ("joao", 34, 31.5, 30, 2, ["hipertensao_nao_controlada"], ["perder_peso"], 150.0,
     "João (34 anos)"),
    ("pedro", 45, 25.0, 200, 12, ["hernia_de_disco"], ["reduzir_estresse", "ganhar_flexibilidade"],
     300.0, "Pedro (45 anos)"),
    ("carla", 25, 22.0, 300, 36, None, ["ganhar_forca", "socializar"], 350.0, "Carla (25 anos)"),
    ("lucas", 28, 23.5, 240, 24, [], ["melhorar_condicionamento"], 100.0, "Lucas (28 anos)"),
]


def construir_ontologia(world: World | None = None) -> Ontology:
    """Cria a TBox (classes, propriedades, axiomas) e a ABox (indivíduos)."""
    world = world or World()
    onto = world.get_ontology(IRI + "#")
    with onto:
        _construir_tbox(onto)
        _construir_abox(onto)
    onto.metadata.label = [locstr("Ontologia de recomendação de atividades físicas", lang="pt-BR")]
    onto.metadata.comment = [locstr(
        "Ontologia OWL 2 DL usada nas Questões 9 e 15 da Lista 2 de IA (UFAL, ECOM031, 2026.2). "
        "Dupla: Bruno Gomes de Barros Filho e Antônio Rodrigo Lima de Andrade Tenório.", lang="pt-BR")]
    onto.metadata.versionInfo = ["1.0"]
    return onto


def _construir_tbox(onto: Ontology) -> None:
    # Classes primitivas (nomeadas e organizadas por especialização).
    class AtividadeFisica(Thing): pass
    class AtividadeAerobica(AtividadeFisica): pass
    class AtividadeDeForca(AtividadeFisica): pass
    class AtividadeDeFlexibilidade(AtividadeFisica): pass
    class Esporte(AtividadeFisica): pass
    class Usuario(Thing): pass
    class CondicaoDeSaude(Thing): pass
    class CondicaoArticular(CondicaoDeSaude): pass
    class CondicaoDaColuna(CondicaoDeSaude): pass
    class CondicaoCardiovascular(CondicaoDeSaude): pass
    class Local(Thing): pass
    class LocalAoArLivre(Local): pass
    class LocalFechado(Local): pass
    class LocalAquatico(Local): pass
    class ParteDoCorpo(Thing): pass
    class Beneficio(Thing): pass
    class Objetivo(Thing): pass
    class NivelDeImpacto(Thing): pass
    class NivelTecnico(Thing): pass

    AllDisjoint([AtividadeFisica, Usuario, CondicaoDeSaude, Local, ParteDoCorpo, Beneficio,
                 Objetivo, NivelDeImpacto, NivelTecnico])
    AllDisjoint([AtividadeAerobica, AtividadeDeForca, AtividadeDeFlexibilidade, Esporte])
    AllDisjoint([LocalAoArLivre, LocalFechado])

    # Propriedades de objeto.
    class temImpacto(ObjectProperty, FunctionalProperty):
        domain = [AtividadeFisica]; range = [NivelDeImpacto]
    class temNivelTecnico(ObjectProperty, FunctionalProperty):
        domain = [AtividadeFisica]; range = [NivelTecnico]
    class realizadaEm(ObjectProperty):
        domain = [AtividadeFisica]; range = [Local]
    class sediaAtividade(ObjectProperty):
        inverse_property = realizadaEm
    class parteDe(ObjectProperty, TransitiveProperty):
        domain = [ParteDoCorpo]; range = [ParteDoCorpo]
    class sobrecarrega(ObjectProperty):
        domain = [AtividadeFisica]; range = [ParteDoCorpo]
    class afeta(ObjectProperty):
        domain = [CondicaoDeSaude]; range = [ParteDoCorpo]
    class afetadaPor(ObjectProperty):
        inverse_property = afeta
    class contraindicadaPara(ObjectProperty):
        domain = [AtividadeFisica]; range = [CondicaoDeSaude]
    class contraindica(ObjectProperty):
        inverse_property = contraindicadaPara
    class temCondicao(ObjectProperty):
        domain = [Usuario]; range = [CondicaoDeSaude]
    class naoDevePraticar(ObjectProperty):
        domain = [Usuario]; range = [AtividadeFisica]
    class promove(ObjectProperty):
        domain = [AtividadeFisica]; range = [Beneficio]
    class dependeDe(ObjectProperty):
        domain = [Objetivo]; range = [Beneficio]
    class contribuiPara(ObjectProperty):
        inverse_property = dependeDe
    class atendeObjetivo(ObjectProperty):
        domain = [AtividadeFisica]; range = [Objetivo]
    class atendidoPor(ObjectProperty):
        inverse_property = atendeObjetivo
    class temObjetivo(ObjectProperty):
        domain = [Usuario]; range = [Objetivo]
    class temAtividadeCandidata(ObjectProperty):
        domain = [Usuario]; range = [AtividadeFisica]

    # Cadeias de propriedades: relacionamentos implícitos que o reasoner deduz.
    sobrecarrega.property_chain.append(PropertyChain([sobrecarrega, parteDe]))
    contraindicadaPara.property_chain.append(PropertyChain([sobrecarrega, afetadaPor]))
    naoDevePraticar.property_chain.append(PropertyChain([temCondicao, contraindica]))
    atendeObjetivo.property_chain.append(PropertyChain([promove, contribuiPara]))
    temAtividadeCandidata.property_chain.append(PropertyChain([temObjetivo, atendidoPor]))

    # Propriedades de dados (todas funcionais: um único valor por indivíduo).
    def dado(nome: str, dominio, tipo, rotulo: str, comentario: str):
        prop = type(nome, (DataProperty, FunctionalProperty), {"namespace": onto})
        prop.domain = [dominio]
        prop.range = [tipo]
        _doc(prop, rotulo, comentario)
        return prop

    gastoMET = dado("gastoMET", AtividadeFisica, float, "gasto energético (MET)",
                    "Equivalente metabólico médio da atividade.")
    dado("custoMensal", AtividadeFisica, float, "custo mensal (R$)", "Custo mensal estimado em reais.")
    minimoDeParticipantes = dado("minimoDeParticipantes", AtividadeFisica, int,
                                 "mínimo de participantes", "Pessoas necessárias para praticar.")
    idade = dado("idade", Usuario, int, "idade", "Idade em anos completos.")
    imc = dado("imc", Usuario, float, "IMC", "Índice de massa corporal (kg/m²), calculado fora da ontologia.")
    minutosAtivosPorSemana = dado("minutosAtivosPorSemana", Usuario, int, "minutos ativos por semana",
                                  "Minutos semanais de atividade física moderada ou vigorosa.")
    mesesDeExperiencia = dado("mesesDeExperiencia", Usuario, int, "meses de experiência",
                              "Tempo de prática regular de exercícios, em meses.")
    dado("orcamentoMensal", Usuario, float, "orçamento mensal (R$)", "Quanto o usuário aceita pagar por mês.")
    dado("prefereAmbiente", Usuario, str, "prefere ambiente",
         "Preferência declarada: 'ar livre', 'fechado' ou 'indiferente'.")

    class exigeAtividadeDoTipo(AnnotationProperty): pass

    # Valores enumerados (padrão "value partition" com nominais).
    impacto = {n: NivelDeImpacto(f"impacto_{n}") for n in ("baixo", "moderado", "alto")}
    tecnico = {n: NivelTecnico(f"nivel_{n}") for n in ("basico", "intermediario", "avancado")}
    NivelDeImpacto.equivalent_to.append(OneOf(list(impacto.values())))
    NivelTecnico.equivalent_to.append(OneOf(list(tecnico.values())))
    AllDifferent(list(impacto.values()))
    AllDifferent(list(tecnico.values()))
    for ind, rotulo in [(impacto["baixo"], "impacto baixo"), (impacto["moderado"], "impacto moderado"),
                        (impacto["alto"], "impacto alto"), (tecnico["basico"], "nível básico"),
                        (tecnico["intermediario"], "nível intermediário"),
                        (tecnico["avancado"], "nível avançado")]:
        _doc(ind, rotulo)
    sistema_cardiovascular = ParteDoCorpo("sistema_cardiovascular")

    # Restrições de cardinalidade e existenciais (condições necessárias).
    AtividadeFisica.is_a += [temImpacto.exactly(1, NivelDeImpacto), gastoMET.exactly(1, float),
                             promove.min(1, Beneficio), realizadaEm.min(1, Local)]
    Usuario.is_a.append(idade.exactly(1, int))

    def met(**faceta):
        return gastoMET.some(ConstrainedDatatype(float, **faceta))

    # Classes definidas (condições necessárias e suficientes).
    definidas = {
        "AtividadeDeBaixoImpacto": AtividadeFisica & temImpacto.value(impacto["baixo"]),
        "AtividadeDeAltoImpacto": AtividadeFisica & temImpacto.value(impacto["alto"]),
        "AtividadeLeve": AtividadeFisica & met(max_exclusive=LIMIAR_MET_MODERADO),
        "AtividadeModerada": AtividadeFisica & met(min_inclusive=LIMIAR_MET_MODERADO,
                                                   max_exclusive=LIMIAR_MET_VIGOROSO),
        "AtividadeVigorosa": AtividadeFisica & met(min_inclusive=LIMIAR_MET_VIGOROSO),
        "AtividadeAoArLivre": AtividadeFisica & realizadaEm.some(LocalAoArLivre),
        "AtividadeEmAmbienteFechado": AtividadeFisica & realizadaEm.some(LocalFechado),
        "AtividadeAquatica": AtividadeFisica & realizadaEm.some(LocalAquatico),
        "AtividadeEmGrupo": AtividadeFisica & minimoDeParticipantes.some(
            ConstrainedDatatype(int, min_inclusive=2)),
        "AtividadeGratuita": AtividadeFisica & onto.custoMensal.some(
            ConstrainedDatatype(float, max_inclusive=0.0)),
        "AtividadeAdequadaParaIniciante": AtividadeFisica & temNivelTecnico.value(tecnico["basico"]),
        "AtividadeAdequadaParaSedentario": AtividadeFisica & met(max_exclusive=LIMIAR_MET_VIGOROSO),
        "AtividadeAdequadaParaIdoso": AtividadeFisica & temImpacto.value(impacto["baixo"])
        & met(max_exclusive=LIMIAR_MET_VIGOROSO),
        "AtividadeAdequadaParaObesidade": AtividadeFisica & temImpacto.value(impacto["baixo"])
        & met(min_inclusive=LIMIAR_MET_MODERADO),
        "UsuarioIdoso": Usuario & idade.some(ConstrainedDatatype(int, min_inclusive=IDADE_IDOSO)),
        "UsuarioSedentario": Usuario & minutosAtivosPorSemana.some(
            ConstrainedDatatype(int, max_exclusive=MINUTOS_OMS)),
        "UsuarioIniciante": Usuario & mesesDeExperiencia.some(
            ConstrainedDatatype(int, max_exclusive=MESES_INICIANTE)),
        "UsuarioComObesidade": Usuario & imc.some(ConstrainedDatatype(float, min_inclusive=IMC_OBESIDADE)),
        "UsuarioComCondicaoArticular": Usuario & temCondicao.some(CondicaoArticular),
        "UsuarioSemCondicaoDeSaude": Usuario & temCondicao.max(0, CondicaoDeSaude),
    }
    for nome, definicao in definidas.items():
        pai = AtividadeFisica if nome.startswith("Atividade") else Usuario
        type(nome, (pai,), {"namespace": onto}).equivalent_to.append(definicao)

    # Axioma geral: toda atividade vigorosa exige do sistema cardiovascular.
    onto.AtividadeVigorosa.is_a.append(sobrecarrega.value(sistema_cardiovascular))

    # Regras de segurança por perfil (lidas pelo recomendador).
    for perfil, tipo in [("UsuarioIdoso", "AtividadeAdequadaParaIdoso"),
                         ("UsuarioSedentario", "AtividadeAdequadaParaSedentario"),
                         ("UsuarioIniciante", "AtividadeAdequadaParaIniciante"),
                         ("UsuarioComObesidade", "AtividadeAdequadaParaObesidade")]:
        onto[perfil].exigeAtividadeDoTipo = [onto[tipo]]

    _documentar_tbox(onto)


def _documentar_tbox(onto: Ontology) -> None:
    textos = {
        "AtividadeFisica": ("Atividade física", "Prática corporal que pode ser recomendada a um usuário."),
        "AtividadeAerobica": ("Atividade aeróbica", "Modalidade predominantemente cardiorrespiratória."),
        "AtividadeDeForca": ("Atividade de força", "Modalidade predominantemente de força e resistência muscular."),
        "AtividadeDeFlexibilidade": ("Atividade de flexibilidade", "Práticas de mobilidade, alongamento e mente-corpo."),
        "Esporte": ("Esporte", "Modalidade com regras e disputa, em geral coletiva."),
        "Usuario": ("Usuário", "Pessoa que pede uma recomendação."),
        "CondicaoDeSaude": ("Condição de saúde", "Condição que pode contraindicar atividades."),
        "CondicaoArticular": ("Condição articular", ""),
        "CondicaoDaColuna": ("Condição da coluna", ""),
        "CondicaoCardiovascular": ("Condição cardiovascular", ""),
        "Local": ("Local", "Lugar onde uma atividade é praticada."),
        "LocalAoArLivre": ("Local ao ar livre", ""),
        "LocalFechado": ("Local fechado", ""),
        "LocalAquatico": ("Local aquático", "Piscina, praia ou lagoa; ortogonal a aberto/fechado."),
        "ParteDoCorpo": ("Parte do corpo", "Estrutura corporal que uma atividade pode sobrecarregar."),
        "Beneficio": ("Benefício", "Efeito esperado da prática regular."),
        "Objetivo": ("Objetivo", "Meta declarada pelo usuário."),
        "NivelDeImpacto": ("Nível de impacto", "Enumeração fechada: baixo, moderado, alto."),
        "NivelTecnico": ("Nível técnico", "Enumeração fechada: básico, intermediário, avançado."),
        "AtividadeDeBaixoImpacto": ("Atividade de baixo impacto", "Definida: temImpacto value impacto_baixo."),
        "AtividadeDeAltoImpacto": ("Atividade de alto impacto", "Definida: temImpacto value impacto_alto."),
        "AtividadeLeve": ("Atividade leve", "Definida: gastoMET < 3."),
        "AtividadeModerada": ("Atividade moderada", "Definida: 3 <= gastoMET < 6."),
        "AtividadeVigorosa": ("Atividade vigorosa", "Definida: gastoMET >= 6; sobrecarrega o sistema cardiovascular."),
        "AtividadeAoArLivre": ("Atividade ao ar livre", ""),
        "AtividadeEmAmbienteFechado": ("Atividade em ambiente fechado", ""),
        "AtividadeAquatica": ("Atividade aquática", ""),
        "AtividadeEmGrupo": ("Atividade em grupo", "Definida: exige pelo menos 2 participantes."),
        "AtividadeGratuita": ("Atividade gratuita", "Definida: custo mensal <= 0."),
        "AtividadeAdequadaParaIniciante": ("Atividade adequada para iniciante", "Exige apenas nível técnico básico."),
        "AtividadeAdequadaParaSedentario": ("Atividade adequada para sedentário", "Não vigorosa (gastoMET < 6)."),
        "AtividadeAdequadaParaIdoso": ("Atividade adequada para idoso", "Baixo impacto e não vigorosa."),
        "AtividadeAdequadaParaObesidade": ("Atividade adequada para obesidade", "Baixo impacto e gastoMET >= 3."),
        "UsuarioIdoso": ("Usuário idoso", "Definida: idade >= 60."),
        "UsuarioSedentario": ("Usuário sedentário", "Definida: menos de 150 minutos ativos por semana (OMS)."),
        "UsuarioIniciante": ("Usuário iniciante", "Definida: menos de 6 meses de prática."),
        "UsuarioComObesidade": ("Usuário com obesidade", "Definida: IMC >= 30."),
        "UsuarioComCondicaoArticular": ("Usuário com condição articular", ""),
        "UsuarioSemCondicaoDeSaude": ("Usuário sem condição de saúde",
                                      "Definida: temCondicao max 0. Só é inferida se o mundo for fechado."),
        "temImpacto": ("tem impacto", "Funcional: cada atividade tem um único nível de impacto."),
        "temNivelTecnico": ("tem nível técnico", "Funcional."),
        "realizadaEm": ("realizada em", ""),
        "sediaAtividade": ("sedia atividade", "Inversa de realizadaEm."),
        "parteDe": ("parte de", "Transitiva: joelho parteDe membro inferior."),
        "sobrecarrega": ("sobrecarrega", "Cadeia: sobrecarrega o parteDe -> sobrecarrega."),
        "afeta": ("afeta", ""),
        "afetadaPor": ("afetada por", "Inversa de afeta."),
        "contraindicadaPara": ("contraindicada para", "Cadeia: sobrecarrega o afetadaPor."),
        "contraindica": ("contraindica", "Inversa de contraindicadaPara."),
        "temCondicao": ("tem condição", ""),
        "naoDevePraticar": ("não deve praticar", "Cadeia: temCondicao o contraindica."),
        "promove": ("promove", ""),
        "dependeDe": ("depende de", ""),
        "contribuiPara": ("contribui para", "Inversa de dependeDe."),
        "atendeObjetivo": ("atende objetivo", "Cadeia: promove o contribuiPara."),
        "atendidoPor": ("atendido por", "Inversa de atendeObjetivo."),
        "temObjetivo": ("tem objetivo", ""),
        "temAtividadeCandidata": ("tem atividade candidata", "Cadeia: temObjetivo o atendidoPor."),
        "exigeAtividadeDoTipo": ("exige atividade do tipo",
                                 "Anotação: liga um perfil de usuário à classe de atividades seguras para ele."),
    }
    for nome, (rotulo, comentario) in textos.items():
        _doc(onto[nome], rotulo, comentario)


def _construir_abox(onto: Ontology) -> None:
    def indiv(classe: str, nome: str, rotulo: str):
        ind = onto[nome] or onto[classe](nome)
        _doc(ind, rotulo)
        return ind

    for nome, classes, rotulo in LOCAIS:
        local = indiv(classes[0], nome, rotulo)
        local.is_a.extend(onto[c] for c in classes[1:])
    for nome, _, rotulo in PARTES_DO_CORPO:
        indiv("ParteDoCorpo", nome, rotulo)
    for nome, partes, _ in PARTES_DO_CORPO:
        onto[nome].parteDe = [onto[p] for p in partes]
    for nome, rotulo in BENEFICIOS:
        indiv("Beneficio", nome, rotulo)
    for nome, beneficios, rotulo in OBJETIVOS:
        indiv("Objetivo", nome, rotulo).dependeDe = [onto[b] for b in beneficios]
    for nome, classe, partes, rotulo in CONDICOES:
        indiv(classe, nome, rotulo).afeta = [onto[p] for p in partes]

    for (nome, classe, impacto, met, nivel, locais, custo, beneficios, partes, minimo,
         rotulo) in ATIVIDADES:
        a = indiv(classe, nome, rotulo)
        a.temImpacto = onto[f"impacto_{impacto}"]
        a.temNivelTecnico = onto[f"nivel_{nivel}"]
        a.gastoMET = met
        a.custoMensal = custo
        a.minimoDeParticipantes = minimo
        a.realizadaEm = [onto[x] for x in locais]
        a.promove = [onto[b] for b in beneficios]
        a.sobrecarrega = [onto[p] for p in partes]

    for nome, idade, imc, minutos, meses, condicoes, objetivos, orcamento, rotulo in USUARIOS:
        u = indiv("Usuario", nome, rotulo)
        u.idade, u.imc, u.minutosAtivosPorSemana, u.mesesDeExperiencia = idade, imc, minutos, meses
        u.orcamentoMensal = orcamento
        u.prefereAmbiente = "indiferente"
        u.temObjetivo = [onto[o] for o in objetivos]
        if condicoes is not None:
            u.temCondicao = [onto[c] for c in condicoes]
            if not condicoes:  # usuário declarou "nenhuma": fecha o mundo explicitamente
                u.is_a.append(onto.temCondicao.max(0, onto.CondicaoDeSaude))


def construir_variante_inconsistente(world: World | None = None) -> Ontology:
    """Cópia com erro de cadastro: corrida recebe dois níveis de impacto distintos."""
    onto = construir_ontologia(world)
    onto.corrida.is_a.append(onto.temImpacto.value(onto.impacto_baixo))
    return onto


def construir_variante_insatisfazivel(world: World | None = None) -> Ontology:
    """Cópia com classe contraditória (baixo e alto impacto ao mesmo tempo)."""
    onto = construir_ontologia(world)
    with onto:
        classe = type("AtividadeSuaveDeAltoImpacto", (onto.AtividadeFisica,), {"namespace": onto})
        classe.equivalent_to.append(onto.AtividadeDeBaixoImpacto & onto.AtividadeDeAltoImpacto)
        _doc(classe, "Atividade suave de alto impacto", "Classe propositalmente insatisfazível (Questão 15).")
    return onto


def main() -> None:
    for construtor, destino in [(construir_ontologia, ARQUIVO_OWL),
                                (construir_variante_inconsistente, ARQUIVO_INCONSISTENTE),
                                (construir_variante_insatisfazivel, ARQUIVO_INSATISFAZIVEL)]:
        construtor().save(file=str(destino), format="rdfxml")
        print(f"gravado: {destino.name}")


if __name__ == "__main__":
    main()
