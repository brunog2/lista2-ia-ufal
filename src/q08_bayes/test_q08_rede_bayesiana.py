import numpy as np
import pandas as pd
import pytest
from pgmpy.inference import VariableElimination

from inferencia_bayes import (
    atualizacao_incremental, distribuicao, entropia, enumeracao_manual, estimar_por_amostragem, evidencia_incerta,
    valor_da_informacao,
)
from rede_dengue import ARESTAS, DESCRICOES, FORMATOS, construir_rede, exportar_rede, ler_rede

SINTOMAS = ["Febre", "DorMuscular", "Tosse", "DorRetroOrbital", "Manchas", "ProvaLaco"]

EVIDENCIAS = [
    {},
    {"Febre": "Sim"},
    {"Febre": "Sim", "Tosse": "Sim", "DorMuscular": "Sim"},
    {"Estacao": "Seca", "Febre": "Sim", "Manchas": "Nao"},
    {"Exposicao": "Sim", "DorRetroOrbital": "Sim", "ProvaLaco": "Sim"},
]


@pytest.fixture(scope="module")
def rede():
    return construir_rede()


@pytest.fixture(scope="module")
def ve(rede):
    return VariableElimination(rede)


def test_requisitos_minimos_do_enunciado(rede):
    assert len(rede.nodes()) >= 5
    assert set(rede.nodes()) == set(DESCRICOES)
    assert len(SINTOMAS) >= 3 and set(SINTOMAS) <= set(rede.nodes())
    assert set(rede.edges()) == set(ARESTAS)


def test_cpts_normalizadas(rede):
    assert rede.check_model()
    for cpd in rede.get_cpds():
        np.testing.assert_allclose(cpd.get_values().sum(axis=0), 1.0)


@pytest.mark.parametrize("evidencia", EVIDENCIAS)
@pytest.mark.parametrize("alvo", ["Dengue", "Influenza"])
def test_enumeracao_manual_igual_eliminacao_de_variaveis(rede, ve, alvo, evidencia):
    np.testing.assert_allclose(enumeracao_manual(rede, alvo, evidencia), distribuicao(ve, alvo, evidencia), atol=1e-12)


def test_evidencia_incerta_pondera_os_dois_cenarios(rede, ve):
    conjunta_sim = enumeracao_manual(rede, "Dengue", {"Febre": "Sim"}) * distribuicao(ve, "Febre")["Sim"]
    conjunta_nao = enumeracao_manual(rede, "Dengue", {"Febre": "Nao"}) * distribuicao(ve, "Febre")["Nao"]
    esperado = 0.7 * conjunta_sim + 0.3 * conjunta_nao
    obtido = distribuicao(ve, "Dengue", incertas=[evidencia_incerta("Febre", 0.7)])
    np.testing.assert_allclose(obtido, esperado / esperado.sum())


def test_priori_de_dengue_calculada_a_mao(ve):
    p_exposicao = 0.4 * 0.6 + 0.6 * 0.25
    assert distribuicao(ve, "Dengue")["Sim"] == pytest.approx(p_exposicao * 0.20 + (1 - p_exposicao) * 0.03)


def test_explaining_away_tosse_reduz_dengue_quando_ha_febre(ve):
    so_febre = distribuicao(ve, "Dengue", {"Febre": "Sim"})["Sim"]
    febre_e_tosse = distribuicao(ve, "Dengue", {"Febre": "Sim", "Tosse": "Sim"})["Sim"]
    assert febre_e_tosse < so_febre
    # Sem febre observada, Tosse e Dengue ficam d-separadas dado Estacao
    assert distribuicao(ve, "Dengue", {"Estacao": "Seca", "Tosse": "Sim"})["Sim"] == pytest.approx(
        distribuicao(ve, "Dengue", {"Estacao": "Seca"})["Sim"]
    )


def test_d_separacao(rede):
    assert rede.is_dconnected("Dengue", "Influenza")
    assert not rede.is_dconnected("Dengue", "Influenza", observed=["Estacao"])
    assert rede.is_dconnected("Dengue", "Influenza", observed=["Estacao", "Febre"])
    assert not rede.is_dconnected("Manchas", "DorRetroOrbital", observed=["Dengue"])


def test_atualizacao_incremental_comeca_na_priori(ve):
    tabela = atualizacao_incremental(ve, "Dengue", "Sim", [("Febre", "Sim"), ("Tosse", "Sim")])
    assert list(tabela["evidencia"]) == ["(nenhuma)", "+ Febre=Sim", "+ Tosse=Sim"]
    assert tabela.iloc[0, 1] == pytest.approx(distribuicao(ve, "Dengue")["Sim"])


@pytest.mark.parametrize("metodo", ["rejeicao", "ponderacao"])
def test_amostragem_aproxima_valor_exato(rede, ve, metodo):
    evidencia = {"Febre": "Sim"}
    estimativa = estimar_por_amostragem(rede, "Dengue", "Sim", evidencia, 20_000, metodo, semente=0)
    assert estimativa == pytest.approx(distribuicao(ve, "Dengue", evidencia)["Sim"], abs=0.02)


def test_entropia():
    assert entropia(pd.Series([0.5, 0.5])) == pytest.approx(1.0)
    assert entropia(pd.Series([1.0, 0.0])) == 0.0


def test_valor_da_informacao_nao_negativo_e_ordenado(ve):
    tabela = valor_da_informacao(ve, "Dengue", "Sim", {"Febre": "Sim"}, SINTOMAS[1:])
    assert (tabela["informacao_mutua_bits"] >= -1e-12).all()
    assert tabela["informacao_mutua_bits"].is_monotonic_decreasing


@pytest.mark.parametrize("extensao", list(FORMATOS))
def test_round_trip_dos_arquivos_exportados(rede, tmp_path, extensao):
    relida = ler_rede(exportar_rede(rede, tmp_path)[extensao])
    assert set(relida.edges()) == set(rede.edges())
    for no in rede.nodes():
        assert relida.get_cpds(no) == rede.get_cpds(no)
