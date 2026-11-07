"""Testes da Q10. Rodar da raiz: .venv/bin/python -m pytest src/q10_buscas -q"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from q10_algoritmos import a_estrela, bfs, dfs, estados_alcancaveis, ucs, verificar_heuristica  # noqa: E402
from q10_problema import (GRAFO, H_ENUNCIADO, ProblemaRota, ProblemaRotaDF,  # noqa: E402
                      criar_h_paradas, dijkstra, h_enunciado, h_nula)


@pytest.fixture
def rota():
    return ProblemaRota()


@pytest.fixture
def rota_df():
    return ProblemaRotaDF()


def test_grafo_simetrico_com_12_trechos():
    assert len(GRAFO) == 9
    assert sum(len(v) for v in GRAFO.values()) == 24
    assert all(GRAFO[v][u] == c for u in GRAFO for v, c in GRAFO[u].items())


def test_custos_otimos_ate_I_conferidos_a_mao():
    assert dijkstra(GRAFO, "I") == {"I": 0, "H": 2, "F": 4, "G": 5, "C": 6,
                                    "E": 7, "B": 9, "D": 11, "A": 13}


def test_bfs_teste_na_geracao(rota):
    r = bfs(rota)
    assert r.rota == list("ABCFI") and r.custo == 15
    assert r.ordem_expansao == list("ABDCEGF") and r.expandidos == 7


def test_dfs(rota):
    r = dfs(rota)
    assert r.rota == list("ABCFI") and r.custo == 15
    assert r.ordem_expansao == list("ABCFI") and r.expandidos == 4


def test_ucs(rota):
    r = ucs(rota)
    assert r.rota == list("ABEFI") and r.custo == 13
    assert r.ordem_expansao == list("ADBEGCFHI") and r.expandidos == 8


def test_a_estrela(rota):
    r = a_estrela(rota, h_enunciado)
    assert r.rota == list("ABEFI") and r.custo == 13
    assert r.ordem_expansao == list("ABDEFHI") and r.expandidos == 6
    assert [(p.estado, p.g, p.h) for p in r.passos][-1] == ("I", 13, 0)


def test_desempate_por_h_troca_a_rota_otima(rota):
    r = a_estrela(rota, h_enunciado, desempate_por_h=True)
    assert r.rota == list("ABEHI") and r.custo == 13 and r.expandidos == 5


def test_a_estrela_com_h_nula_reproduz_ucs(rota):
    a, u = a_estrela(rota, h_nula), ucs(rota)
    assert a.ordem_expansao == u.ordem_expansao and a.rota == u.rota


def test_heuristica_do_enunciado_admissivel_e_consistente(rota):
    v = verificar_heuristica(rota, h_enunciado)
    assert v["admissivel"] and v["consistente"]


def test_verificacao_detecta_heuristica_ruim(rota):
    ruim = dict(H_ENUNCIADO, E=12)  # h(E)=12 > h*(E)=7
    v = verificar_heuristica(rota, ruim.get)
    assert not v["admissivel"] and not v["consistente"]
    assert v["nao_admissiveis"] == [("E", 12, 7)]


def test_estado_inicial_da_variante(rota_df):
    assert rota_df.inicial == ("A", False, False)
    assert ProblemaRotaDF(inicio="D").inicial == ("D", True, False)
    assert len(estados_alcancaveis(rota_df)) == 32


@pytest.mark.parametrize("h", [None, h_enunciado, "df"])
def test_variante_df_rota_otima(rota_df, h):
    if h is None:
        r = ucs(rota_df)
    else:
        r = a_estrela(rota_df, criar_h_paradas() if h == "df" else h)
    assert [s[0] for s in r.rota] == list("ADEFI") and r.custo == 14


def test_heuristica_df_admissivel_consistente_e_mais_informada(rota_df):
    h_df = criar_h_paradas()
    v = verificar_heuristica(rota_df, h_df)
    assert v["admissivel"] and v["consistente"]
    assert all(h_df(s) >= h_enunciado(s) for s in estados_alcancaveis(rota_df))
    assert a_estrela(rota_df, h_df).expandidos < a_estrela(rota_df, h_enunciado).expandidos \
        < ucs(rota_df).expandidos
