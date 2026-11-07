"""Testes do recomendador da Questão 9."""

import pytest

from recomendador_atividades import PerfilUsuario, formatar, recomendar


def _perfil(**ajustes) -> PerfilUsuario:
    base = dict(nome="Teste", idade=30, peso_kg=70, altura_m=1.75, minutos_ativos_por_semana=200,
                meses_de_experiencia=24, objetivos=["melhorar_condicionamento"], condicoes=[],
                orcamento_mensal=300.0)
    return PerfilUsuario(**{**base, **ajustes})


@pytest.fixture(scope="module")
def idosa():
    return recomendar(_perfil(idade=68, peso_kg=72, altura_m=1.60, minutos_ativos_por_semana=40,
                              meses_de_experiencia=0, objetivos=["prevenir_quedas", "socializar"],
                              condicoes=["artrose_no_joelho"], orcamento_mensal=200.0,
                              prefere_ambiente="ar livre"))


def test_idosa_recebe_so_atividades_seguras(idosa):
    nomes = [i.atividade for i in idosa.recomendadas]
    assert nomes[0] == "tai_chi_chuan"
    assert not {"corrida", "zumba", "crossfit"} & set(nomes)
    assert all("AtividadeAdequadaParaIdoso" in i.classes_inferidas for i in idosa.recomendadas)
    assert "Zumba" in idosa.contraindicacoes


def test_pontuacao_soma_os_motivos(idosa):
    for item in idosa.recomendadas:
        parcelas = [int(m.split()[0]) for m in item.motivos if m[0] in "+-"]
        assert item.pontuacao == sum(parcelas)


def test_hipertenso_nao_recebe_atividade_vigorosa():
    rec = recomendar(_perfil(condicoes=["hipertensao_nao_controlada"]))
    assert all("AtividadeVigorosa" not in i.classes_inferidas for i in rec.recomendadas)
    assert "AtividadeVigorosa" in rec.contraindicacoes["Spinning"][0]


def test_mundo_aberto_versus_fechado():
    aberto = recomendar(_perfil(condicoes=None))
    fechado = recomendar(_perfil(condicoes=[]))
    assert any("mundo aberto" in a for a in aberto.avisos)
    assert not any(p.startswith("UsuarioSemCondicaoDeSaude") for p in aberto.perfis)
    assert any(p.startswith("UsuarioSemCondicaoDeSaude") for p in fechado.perfis)


@pytest.mark.parametrize("ajuste", [{"objetivos": []}, {"objetivos": ["voar"]},
                                    {"condicoes": ["Usuario"]}, {"idade": -3},
                                    {"prefere_ambiente": "lua"}])
def test_entrada_invalida(ajuste):
    with pytest.raises(ValueError):
        recomendar(_perfil(**ajuste))


def test_relatorio_exibe_elementos_da_decisao(idosa):
    texto = formatar(idosa)
    for trecho in ("Perfis inferidos", "Exigências de segurança", "Contraindicações deduzidas",
                   "Recomendações", "Candidatas descartadas"):
        assert trecho in texto
