import itertools
import random

import pytest

from explicacao import explicar
from planejador import Atividade, Segmento, hhmm_para_min as h, min_para_hhmm, planejar, urgencia, utilidade, verificar


def q11(divisivel_b=False):
    return [
        Atividade("A", "Preparar aula de IA", 90, "alta", 0),
        Atividade("B", "Corrigir trabalhos", 120, "media", 1, divisivel=divisivel_b),
        Atividade("C", "Reunião de pesquisa", 60, "alta", 0, inicio_fixo=h("16:00")),
        Atividade("D", "Revisar artigo", 60, "baixa", 7),
    ]


def blocos(plano):
    return [(s.atividade_id, min_para_hhmm(s.inicio), min_para_hhmm(s.fim)) for s in plano.segmentos]


def test_urgencia_e_valores():
    assert (urgencia(0), urgencia(1), urgencia(7)) == (3, 2, 1.25)
    assert [a.valor for a in q11()] == [9, 4, 9, 1.25]


def test_cenario_q11_sem_divisao():
    plano = planejar(q11(), h("14:00"), h("18:00")).melhor
    assert blocos(plano) == [("A", "14:00", "15:30"), ("C", "16:00", "17:00"), ("D", "17:00", "18:00")]
    assert plano.utilidade == pytest.approx(19.25)


def test_cenario_q11_com_b_divisivel():
    plano = planejar(q11(divisivel_b=True), h("14:00"), h("18:00")).melhor
    assert blocos(plano) == [("A", "14:00", "15:30"), ("B", "15:30", "16:00"),
                             ("C", "16:00", "17:00"), ("B", "17:00", "18:00")]
    assert plano.minutos["B"] == 90 and plano.minutos["D"] == 0
    assert plano.utilidade == pytest.approx(21.0)


def test_cenario_q11_janela_de_cinco_horas():
    plano = planejar(q11(), h("14:00"), h("19:00")).melhor
    assert blocos(plano) == [("A", "14:00", "15:30"), ("C", "16:00", "17:00"), ("B", "17:00", "19:00")]
    assert plano.utilidade == pytest.approx(22.0)


def test_explicacao_do_cenario_q11():
    r = explicar(q11(), h("14:00"), h("18:00"))
    por_id = {d["id"]: d for d in r["atividades"]}
    assert por_id["B"]["status"] == "fora"
    assert por_id["B"]["contrafactual"]["perda"] == pytest.approx(5.0)
    assert r["segunda_melhor_alternativa"]["forcando"] == "B"
    assert r["ociosidade"] == [{"inicio": "15:30", "fim": "16:00", "minutos": 30,
                                "motivo": "B precisa de 120 min contínuos"}]
    assert r["verificacao"] == {"valido": True, "violacoes": []}


def test_atividade_que_nao_cabe_em_intervalo_algum():
    ativs = q11() + [Atividade("E", "Escrever projeto", 150, "alta", 0)]
    r = explicar(ativs, h("14:00"), h("18:00"))
    e = next(d for d in r["atividades"] if d["id"] == "E")
    assert e["status"] == "fora"
    assert e["contrafactual"]["viavel"] is False
    assert "150 min contínuos" in e["contrafactual"]["motivo"]


def test_prazo_com_horario_e_respeitado():
    ativs = [Atividade("X", "Enviar parecer", 60, "baixa", 0, prazo_hora=h("15:00")),
             Atividade("Y", "Aula", 60, "alta", 0)]
    plano = planejar(ativs, h("14:00"), h("16:00")).melhor
    assert blocos(plano) == [("X", "14:00", "15:00"), ("Y", "15:00", "16:00")]


def test_bloco_menor_que_o_maximo_pode_ser_o_otimo():
    # 90 min no primeiro intervalo deixariam 30 min de X, abaixo do bloco mínimo de 60;
    # 60 + 60 conclui a atividade
    ativs = [Atividade("X", "Relatório", 120, "media", 1, divisivel=True, bloco_minimo=60),
             Atividade("F", "Reunião", 30, "alta", 0, inicio_fixo=h("15:30"))]
    plano = planejar(ativs, h("14:00"), h("17:00")).melhor
    assert plano.minutos["X"] == 120
    assert verificar(list(plano.segmentos), ativs, h("14:00"), h("17:00")) == []


def test_minimo_exigido_inviavel_devolve_none():
    ativs = [Atividade("X", "Longa", 120, "alta", 0, minimo_exigido=120)]
    assert planejar(ativs, h("14:00"), h("15:00")).melhor is None


@pytest.mark.parametrize("ativs, trecho", [
    ([Atividade("C", "Reunião", 60, "alta", 0, inicio_fixo=h("18:00"))], "fora da janela"),
    ([Atividade("C", "R1", 60, "alta", 0, inicio_fixo=h("14:00")),
      Atividade("D", "R2", 60, "alta", 0, inicio_fixo=h("14:30"))], "se sobrepõem"),
])
def test_instancias_mal_definidas(ativs, trecho):
    with pytest.raises(ValueError, match=trecho):
        planejar(ativs, h("14:00"), h("18:00"))


@pytest.mark.parametrize("kwargs", [
    {"duracao": 0}, {"prioridade": "urgente"}, {"prazo_dias": -1},
    {"prazo_dias": 1, "prazo_hora": 900}, {"inicio_fixo": 900, "divisivel": True},
])
def test_atividade_invalida(kwargs):
    base = {"id": "X", "nome": "x", "duracao": 60, "prioridade": "alta", "prazo_dias": 0} | kwargs
    with pytest.raises(ValueError):
        Atividade(**base)


# ---- comparação com força bruta -------------------------------------------------------------

SLOT = 30


def instancia_aleatoria(rng: random.Random, n_slots: int, n_ativ: int):
    inicio = 8 * 60
    fim = inicio + n_slots * SLOT
    ativs = []
    fixa_usada = False
    for i in range(n_ativ):
        dur = rng.randint(1, 3) * SLOT
        prazo = rng.choice([0, 0, 1, 3, 7])
        kwargs = {}
        if not fixa_usada and rng.random() < 0.3 and dur <= fim - inicio:
            kwargs["inicio_fixo"] = inicio + rng.randint(0, (fim - inicio - dur) // SLOT) * SLOT
            fixa_usada = True
        elif rng.random() < 0.4:
            kwargs.update(divisivel=True, bloco_minimo=rng.choice([SLOT, 2 * SLOT]))
        if prazo == 0 and "inicio_fixo" not in kwargs and rng.random() < 0.3:
            kwargs["prazo_hora"] = inicio + rng.randint(1, n_slots) * SLOT
        ativs.append(Atividade(f"T{i}", f"tarefa {i}", dur, rng.choice(["alta", "media", "baixa"]), prazo, **kwargs))
    return ativs, inicio, fim


def forca_bruta(ativs, inicio, fim):
    """Testa toda atribuição slot -> (nada | atividade) e fica com a melhor válida pelo verificador."""
    n = (fim - inicio) // SLOT
    melhor = None
    for atrib in itertools.product([None] + [a.id for a in ativs], repeat=n):
        segs = []
        for k, grupo in itertools.groupby(enumerate(atrib), key=lambda par: par[1]):
            grupo = list(grupo)
            if k is not None:
                segs.append(Segmento(k, inicio + grupo[0][0] * SLOT, inicio + (grupo[-1][0] + 1) * SLOT))
        if verificar(segs, ativs, inicio, fim):
            continue
        minutos = {}
        for s in segs:
            minutos[s.atividade_id] = minutos.get(s.atividade_id, 0) + s.minutos
        u = utilidade(ativs, minutos)
        melhor = u if melhor is None else max(melhor, u)
    return melhor


@pytest.mark.parametrize("semente", range(120))
def test_otimo_igual_a_forca_bruta(semente):
    rng = random.Random(semente)
    ativs, inicio, fim = instancia_aleatoria(rng, n_slots=rng.randint(4, 7), n_ativ=rng.randint(2, 3))
    plano = planejar(ativs, inicio, fim, passo=SLOT).melhor
    assert plano is not None
    assert verificar(list(plano.segmentos), ativs, inicio, fim) == []
    assert plano.utilidade == pytest.approx(forca_bruta(ativs, inicio, fim))


@pytest.mark.parametrize("semente", range(100, 160))
def test_restricoes_sempre_respeitadas(semente):
    rng = random.Random(semente)
    ativs, inicio, fim = instancia_aleatoria(rng, n_slots=rng.randint(6, 12), n_ativ=rng.randint(3, 6))
    r = explicar(ativs, inicio, fim, passo=SLOT)
    assert r["verificacao"]["valido"], r["verificacao"]["violacoes"]
    for d in r["atividades"]:
        if d["contrafactual"] and d["contrafactual"]["viavel"]:
            assert d["contrafactual"]["perda"] >= -1e-9  # forçar uma atividade nunca melhora o ótimo


@pytest.mark.parametrize("semente", range(300, 500))
def test_poda_nao_altera_o_otimo(semente):
    # instâncias maiores que as da força bruta: a busca sem poda é a referência exata
    rng = random.Random(semente)
    ativs, inicio, fim = instancia_aleatoria(rng, n_slots=rng.randint(6, 12), n_ativ=rng.randint(3, 6))
    com_poda = planejar(ativs, inicio, fim, passo=SLOT)
    sem_poda = planejar(ativs, inicio, fim, passo=SLOT, podar=False)
    assert com_poda.melhor.utilidade == pytest.approx(sem_poda.melhor.utilidade)
    assert com_poda.estatisticas["nos_explorados"] <= sem_poda.estatisticas["nos_explorados"]
