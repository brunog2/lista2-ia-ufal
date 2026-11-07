"""Testes da ontologia da Questão 9: arquivo, requisitos mínimos e inferências."""

from io import BytesIO

import pytest
import rdflib
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

from ontologia_atividades import ARQUIVO_OWL, IRI, construir_ontologia
from raciocinio_owl import carregar_ontologia, raciocinar_hermit


@pytest.fixture(scope="module")
def inferida():
    world, onto = carregar_ontologia()
    raciocinar_hermit(world)
    return world, onto


def test_arquivo_versionado_corresponde_ao_script():
    buffer = BytesIO()
    construir_ontologia().save(file=buffer, format="ntriples")
    gerado = rdflib.Graph().parse(data=buffer.getvalue(), format="nt")
    versionado = rdflib.Graph().parse(ARQUIVO_OWL, format="xml")
    assert isomorphic(gerado, versionado)


def test_rdflib_le_o_arquivo_com_rotulos_em_portugues():
    g = rdflib.Graph().parse(ARQUIVO_OWL, format="xml")
    assert (rdflib.URIRef(IRI), RDF.type, OWL.Ontology) in g
    classes = set(g.subjects(RDF.type, OWL.Class)) - set(g.subjects(RDF.type, RDFS.Datatype))
    nomeadas = {c for c in classes if isinstance(c, rdflib.URIRef)}
    for c in nomeadas:
        assert any((l.language or "").lower() == "pt-br" for l in g.objects(c, RDFS.label)), c


def test_requisitos_minimos_da_questao():
    _, onto = carregar_ontologia()
    propriedades = list(onto.object_properties()) + list(onto.data_properties())
    assert len(list(onto.classes())) >= 10
    assert len(propriedades) >= 15
    assert len(list(onto.AtividadeFisica.instances())) >= 15


def test_ontologia_consistente_e_coerente(inferida):
    world, onto = inferida
    assert set(world.inconsistent_classes()) <= {onto.world["http://www.w3.org/2002/07/owl#Nothing"]}


def test_classificacao_de_usuarios_por_restricao_de_dado(inferida):
    _, onto = inferida
    assert onto.maria in onto.UsuarioIdoso.instances()
    assert onto.joao in onto.UsuarioComObesidade.instances()
    assert onto.pedro not in onto.UsuarioIdoso.instances()


def test_relacionamentos_implicitos_por_cadeia(inferida):
    _, onto = inferida
    assert {onto.corrida, onto.zumba} <= set(onto.maria.naoDevePraticar)
    assert onto.spinning in onto.joao.naoDevePraticar  # via AtividadeVigorosa
    assert onto.coluna_vertebral in onto.crossfit.sobrecarrega  # via parteDe transitiva
    assert onto.pilates in onto.maria.temAtividadeCandidata


def test_subsuncao_inferida(inferida):
    _, onto = inferida
    assert issubclass(onto.AtividadeAdequadaParaIdoso, onto.AtividadeAdequadaParaSedentario)
    assert issubclass(onto.AtividadeAdequadaParaObesidade, onto.AtividadeDeBaixoImpacto)
