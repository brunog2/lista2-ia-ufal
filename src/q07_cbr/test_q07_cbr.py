"""Testes da Q7 (CBR): similaridade, ciclo completo e política de retenção."""

import itertools
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from cbr_avaliacao import avaliar_loo
from cbr_casos import SINTOMAS, Problema, carregar_base
from cbr_ciclo import SistemaCBR, adaptar_tratamento, revisar, revisar_interativo
from cbr_cli import interpretar_sintomas
from cbr_similaridade import METRICAS_SINTOMAS, PESOS_ATRIBUTOS, PESOS_SINTOMAS, similaridade

BASE = Path(__file__).with_name("base_casos.json")


@pytest.fixture
def casos():
    return carregar_base(BASE)


@pytest.fixture
def sistema_temp(tmp_path):
    copia = tmp_path / "base.json"
    shutil.copy(BASE, copia)
    return SistemaCBR.de_arquivo(copia)


def dengue_classica(**kw) -> Problema:
    dados = dict(sintomas={"dor_retroorbital": 3, "dor_cabeca": 3, "mialgia": 3, "nauseas": 1},
                 temperatura=39.3, dias_sintomas=3, idade=30, inicio="subito")
    return Problema(**{**dados, **kw})


def test_base_atende_requisitos_minimos(casos):
    assert len(casos) >= 15
    assert len({c.diagnostico for c in casos}) >= 5
    assert len({c.id for c in casos}) == len(casos)
    assert all(c.tratamento for c in casos)


def test_pesos_cobrem_vocabulario():
    assert PESOS_SINTOMAS.keys() == SINTOMAS.keys()
    assert sum(PESOS_ATRIBUTOS.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("metrica", METRICAS_SINTOMAS.values(), ids=METRICAS_SINTOMAS.keys())
def test_propriedades_da_similaridade(casos, metrica):
    for c in casos:
        assert similaridade(c.problema, c.problema, metrica) == pytest.approx(1.0)
    for a, b in itertools.combinations(casos, 2):
        s = similaridade(a.problema, b.problema, metrica)
        assert 0.0 <= s <= 1.0
        assert s == pytest.approx(similaridade(b.problema, a.problema, metrica))


def test_peso_de_sintoma_especifico_faz_diferenca():
    consulta = {"dor_retroorbital": 2, "dor_cabeca": 2}
    com_especifico = {"dor_retroorbital": 2, "tosse": 2}
    com_inespecifico = {"dor_cabeca": 2, "tosse": 2}
    simples, ponderada = METRICAS_SINTOMAS["simples"], METRICAS_SINTOMAS["ponderada"]
    assert simples(consulta, com_especifico) == simples(consulta, com_inespecifico)
    assert ponderada(consulta, com_especifico) > ponderada(consulta, com_inespecifico)


def test_problema_rejeita_entrada_invalida():
    with pytest.raises(ValueError):
        dengue_classica(sintomas={"sintoma_inventado": 2})
    with pytest.raises(ValueError):
        dengue_classica(sintomas={"tosse": 5})
    with pytest.raises(ValueError):
        dengue_classica(temperatura=50.0)


def test_interpretar_sintomas_aceita_nome_e_numero():
    nomes = list(SINTOMAS)
    assert interpretar_sintomas("dor_retroorbital:3, 1:2, tosse") == {
        "dor_retroorbital": 3, nomes[0]: 2, "tosse": 2}
    with pytest.raises(ValueError):
        interpretar_sintomas("inexistente:2")


def test_recuperacao_ordenada_e_diagnostico_correto(casos):
    sistema = SistemaCBR(casos, k=3)
    vizinhos = sistema.recuperar(dengue_classica())
    sims = [s for _, s in vizinhos]
    assert sims == sorted(sims, reverse=True) and len(vizinhos) == 3
    sugestao = sistema.reutilizar(dengue_classica(), vizinhos)
    assert sugestao.diagnostico == "Dengue"
    assert 0 < sugestao.confianca <= 1
    assert sum(sugestao.votos.values()) == pytest.approx(sum(sims))


def test_adaptacao_por_alergia_e_idade():
    tratamento = ["Paracetamol ou dipirona para febre", "Evitar AAS e ibuprofeno",
                  "Paciente pediátrico: doses calculadas pelo peso"]
    novo, ajustes = adaptar_tratamento(tratamento, dengue_classica(idade=70, alergias=("dipirona", "ibuprofeno")))
    assert not any("dipirona" in i and "Não usar" not in i for i in novo)
    assert "Evitar AAS e ibuprofeno" in novo  # proibição mantida
    assert not any(i.startswith("Paciente pediátrico") for i in novo)
    assert any(i.startswith("Paciente idoso") for i in novo)
    assert len(ajustes) == 2


def test_ciclo_completo_retem_e_recupera_caso_novo(sistema_temp):
    sinusite = Problema(sintomas={"congestao_nasal": 3, "dor_cabeca": 3, "coriza": 2},
                        temperatura=38.0, dias_sintomas=12, idade=40, inicio="gradual")
    sugestao = sistema_temp.consultar(sinusite)
    caso = revisar(sinusite, sugestao, "Sinusite bacteriana", ["Lavagem nasal", "Antibiótico a critério médico"])
    resultado = sistema_temp.reter(caso)
    assert resultado.retido
    # persistiu no arquivo temporário e é recuperado numa nova consulta parecida
    recarregado = SistemaCBR.de_arquivo(sistema_temp.caminho)
    parecido = Problema(sintomas={"congestao_nasal": 3, "dor_cabeca": 2, "coriza": 2},
                        temperatura=37.9, dias_sintomas=10, idade=45, inicio="gradual")
    melhor, _ = recarregado.recuperar(parecido)[0]
    assert (melhor.id, melhor.diagnostico, melhor.origem) == (resultado.id_caso, "Sinusite bacteriana", "retido")


def test_retencao_nao_duplica_caso_quase_identico(sistema_temp, casos):
    original = casos[0]
    quase_igual = replace(original.problema, temperatura=original.problema.temperatura + 0.1)
    caso = revisar(quase_igual, sistema_temp.consultar(quase_igual))
    tamanho = len(sistema_temp.casos)
    resultado = sistema_temp.reter(caso)
    assert not resultado.retido and resultado.id_caso == original.id
    assert len(carregar_base(sistema_temp.caminho)) == tamanho
    assert carregar_base(sistema_temp.caminho)[0].confirmacoes == 1


def test_base_original_intacta_apos_testes():
    assert all(c.origem == "base" and c.confirmacoes == 0 for c in carregar_base(BASE))


def test_revisao_exige_tratamento_quando_corrige(casos):
    sugestao = SistemaCBR(casos).consultar(dengue_classica())
    with pytest.raises(ValueError):
        revisar(dengue_classica(), sugestao, "Chikungunya")


def test_revisao_interativa(casos):
    sugestao = SistemaCBR(casos).consultar(dengue_classica())
    respostas = iter(["n", "Chikungunya", "", "Repouso; Hidratação", "teste"])
    caso = revisar_interativo(dengue_classica(), sugestao, perguntar=lambda _: next(respostas))
    assert caso.diagnostico == "Chikungunya" and caso.tratamento == ["Repouso", "Hidratação"]
    confirmado = revisar_interativo(dengue_classica(), sugestao, perguntar=lambda _: "s")
    assert confirmado.diagnostico == sugestao.diagnostico == "Dengue"


def test_avaliacao_loo(casos):
    df = avaliar_loo(casos, k=3)
    assert len(df) == len(casos)
    assert df["acerto_top1"].mean() >= 0.8
    assert (df["acerto_top3"] >= df["acerto_top1"]).all()
