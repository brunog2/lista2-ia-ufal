"""Testes da Questão 15: tarefas de raciocínio, OWA e notação."""

import pytest
from owlready2 import OwlReadyInconsistentOntologyError

from ontologia_atividades import ARQUIVO_INCONSISTENTE, ARQUIVO_INSATISFAZIVEL
from raciocinio_owl import (carregar_ontologia, classificacao_hermit, classificacao_pellet,
                            consistente_pellet, explicar_pellet, raciocinar_hermit)
from sintaxe_owl import axiomas, dl, manchester


def test_hermit_e_pellet_detectam_inconsistencia():
    world, _ = carregar_ontologia(ARQUIVO_INCONSISTENTE)
    with pytest.raises(OwlReadyInconsistentOntologyError):
        raciocinar_hermit(world)
    assert consistente_pellet() and not consistente_pellet(ARQUIVO_INCONSISTENTE)
    assert "Functional temImpacto" in explicar_pellet("--inconsistent", caminho=ARQUIVO_INCONSISTENTE)


def test_classe_insatisfazivel_nos_dois_reasoners():
    assert classificacao_hermit(ARQUIVO_INSATISFAZIVEL).insatisfaziveis == {"AtividadeSuaveDeAltoImpacto"}
    assert classificacao_pellet(ARQUIVO_INSATISFAZIVEL).insatisfaziveis == {"AtividadeSuaveDeAltoImpacto"}


def test_hermit_e_pellet_concordam():
    h, p = classificacao_hermit(), classificacao_pellet()
    assert h.superclasses == p.superclasses
    assert h.tipos == p.tipos


def test_axioma_de_fechamento_muda_a_classificacao():
    world, onto = carregar_ontologia()
    raciocinar_hermit(world)
    assert onto.carla not in onto.UsuarioSemCondicaoDeSaude.instances()
    world, onto = carregar_ontologia()
    onto.carla.is_a.append(onto.temCondicao.max(0, onto.CondicaoDeSaude))
    raciocinar_hermit(world)
    assert onto.carla in onto.UsuarioSemCondicaoDeSaude.instances()


def test_notacoes():
    _, onto = carregar_ontologia()
    definicao = onto.AtividadeAdequadaParaIdoso.equivalent_to[0]
    assert manchester(definicao) == ("AtividadeFisica and (temImpacto value impacto_baixo) "
                                     "and (gastoMET some decimal[< 6.0])")
    assert dl(definicao) == "AtividadeFisica ⊓ ∃temImpacto.{impacto_baixo} ⊓ ∃gastoMET.decimal[< 6.0]"
    cadeias = [a["DL"] for a in axiomas(onto) if a["tipo"] == "cadeia"]
    assert "temCondicao ∘ contraindica ⊑ naoDevePraticar" in cadeias
