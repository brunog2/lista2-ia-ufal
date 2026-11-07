"""Testes de ranking, métricas e TransE."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transe import (avaliar, dividir, escores_transe, metricas, posto,  # noqa: E402
                    treinar_transe)


def test_posto_simples_e_filtrado():
    s = np.array([0.9, 0.5, 0.8, 0.1])
    assert posto(s, 1, set()) == 3
    assert posto(s, 1, {0}) == 2          # a candidata 0 também é verdadeira: sai da disputa
    assert posto(s, 0, set()) == 1


def test_posto_com_empate_usa_media():
    s = np.zeros(5)
    assert posto(s, 2, set()) == 3        # 1 + 0 maiores + 4 empatadas / 2
    assert posto(np.array([1.0, 1.0, 0.0]), 0, set()) == 1.5


def test_metricas_conhecidas():
    m = metricas(np.array([1, 2, 4, 20]))
    assert m["MRR"] == pytest.approx((1 + 0.5 + 0.25 + 0.05) / 4)
    assert m["Hits@1"] == 0.25 and m["Hits@3"] == 0.5 and m["Hits@10"] == 0.75
    assert m["MR"] == pytest.approx(6.75)


def test_avaliar_com_oraculo_da_mrr_1():
    verdade = np.array([[0, 0, 1], [0, 0, 2], [3, 0, 2]])
    teste = verdade[:1]

    def caudas(h, r):
        s = np.zeros(4)
        s[[t for hh, rr, t in verdade if hh == h and rr == r]] = 1
        return s

    def cabecas(r, t):
        s = np.zeros(4)
        s[[h for h, rr, tt in verdade if tt == t and rr == r]] = 1
        return s
    # sem filtro, (0,0,2) empataria com (0,0,1); com filtro o oráculo acerta tudo
    assert metricas(avaliar(teste, verdade, caudas, cabecas))["MRR"] == 1.0


def test_dividir_mantem_entidades_do_teste_no_treino():
    triplas = [(f"e{i}", "r", f"e{(i + 1) % 30}") for i in range(30)] + [("solta", "r", "e0")]
    treino, teste = dividir(triplas, 0.3, seed=1)
    vistos = {x for h, r, t in treino for x in (h, r, t)}
    assert set(treino) | set(teste) == set(triplas)
    assert not set(treino) & set(teste)
    assert all(set(tr) <= vistos for tr in teste)
    assert ("solta", "r", "e0") in treino  # única aparição de "solta" não pode ir para o teste


def test_transe_aprende_em_grafo_sintetico():
    # 10 "pessoas" moram em 5 "cidades" (N-para-1) e cada cidade fica em 1 de 2 "estados"
    triplas = np.array([(i, 0, 10 + i % 5) for i in range(10)] +
                       [(10 + j, 1, 15 + j % 2) for j in range(5)])
    E, R, perdas = treinar_transe(triplas, 17, 2, dim=16, epocas=300, seed=0)
    assert perdas[-1] < perdas[0] / 2
    m = metricas(avaliar(triplas, triplas, *escores_transe(E, R)))
    assert m["MRR"] > 0.9  # aleatório fica perto de 0,2 com 17 candidatas


def test_transe_nao_representa_ciclo():
    """Limitação conhecida: num ciclo h->...->h, a soma das translações teria de ser zero."""
    n = 6
    ciclo = np.array([(i, 0, (i + 1) % n) for i in range(n)])
    E, R, _ = treinar_transe(ciclo, n, 1, dim=8, epocas=300, seed=0)
    assert metricas(avaliar(ciclo, ciclo, *escores_transe(E, R)))["Hits@1"] < 1.0
