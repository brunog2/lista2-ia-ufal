import pytest

from explicacao import avaliar_proposta
from planejador import Atividade, Segmento, hhmm_para_min as h, verificar

INICIO, FIM = h("14:00"), h("18:00")
ATIVS = [
    Atividade("A", "Preparar aula de IA", 90, "alta", 0),
    Atividade("B", "Corrigir trabalhos", 120, "media", 1, divisivel=True, bloco_minimo=30),
    Atividade("C", "Reunião de pesquisa", 60, "alta", 0, inicio_fixo=h("16:00")),
    Atividade("D", "Enviar parecer", 30, "baixa", 0, prazo_hora=h("15:00")),
]


def seg(i, a, b):
    return Segmento(i, h(a), h(b))


def test_plano_valido_nao_tem_violacoes():
    plano = [seg("A", "14:00", "15:30"), seg("B", "15:30", "16:00"), seg("C", "16:00", "17:00"),
             seg("B", "17:00", "18:00")]
    assert verificar(plano, ATIVS, INICIO, FIM) == []


@pytest.mark.parametrize("plano, trecho", [
    ([seg("A", "14:00", "15:30"), seg("C", "15:00", "16:00")], "compromisso fixo deve ocupar"),
    ([seg("A", "15:30", "17:00"), seg("C", "16:00", "17:00")], "sobreposição"),
    ([seg("A", "14:00", "15:00"), seg("A", "17:00", "17:30"), seg("C", "16:00", "17:00")], "interrompida"),
    ([seg("A", "14:00", "15:00"), seg("C", "16:00", "17:00")], "60 de 90 min"),
    ([seg("B", "14:00", "14:15"), seg("C", "16:00", "17:00")], "menor que o mínimo"),
    ([seg("B", "13:00", "15:00"), seg("C", "16:00", "17:00")], "fora da janela"),
    ([seg("D", "15:00", "15:30"), seg("C", "16:00", "17:00")], "depois do prazo"),
    ([seg("C", "16:00", "17:00"), seg("Z", "14:00", "15:00")], "desconhecida"),
    ([], "compromisso fixo deve ocupar"),
])
def test_violacoes_detectadas(plano, trecho):
    violacoes = verificar(plano, ATIVS, INICIO, FIM)
    assert any(trecho in v for v in violacoes), violacoes


def test_minimo_exigido():
    ativs = [Atividade("X", "x", 60, "alta", 0, minimo_exigido=60)]
    assert any("mínimo exigido" in v for v in verificar([], ativs, INICIO, FIM))


def test_avaliar_proposta_compara_com_o_otimo():
    # proposta "intuitiva" válida: B primeiro, sem A
    proposta = [seg("B", "14:00", "16:00"), seg("C", "16:00", "17:00")]
    r = avaliar_proposta(proposta, ATIVS, INICIO, FIM)
    assert r["valido"] is True
    assert r["utilidade_proposta"] < r["utilidade_otima"]
    assert {m["atividade"] for m in r["diferenca_para_otimo"]} >= {"A", "B"}


def test_avaliar_proposta_invalida_nao_recebe_utilidade():
    r = avaliar_proposta([seg("A", "15:30", "17:00"), seg("C", "16:00", "17:00")], ATIVS, INICIO, FIM)
    assert r["valido"] is False and r["utilidade_proposta"] is None
