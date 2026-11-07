"""Testes da materialização (python -m pytest src/q14_knowledge_graph -q)."""

import sys
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kg import ARBO, construir_grafo  # noqa: E402
from raciocinio import REGRAS, consultar, materializar  # noqa: E402


@pytest.fixture(scope="module")
def grafos():
    g = construir_grafo()
    fecho, procedencia, iteracoes = materializar(g)
    return g, fecho, procedencia, iteracoes


@pytest.mark.parametrize("s, p, o", [
    ("DENV", RDF.type, "Arbovirus"),            # domínio de temVetor via subPropertyOf
    ("DENV", RDF.type, "AgenteBiologico"),      # subClassOf transitiva
    ("AedesAegypti", RDF.type, "Vetor"),        # alcance
    ("Dengue", RDF.type, "Arbovirose"),         # cadeia + domínio de transmitidaPor
    ("Febre", RDF.type, "ManifestacaoClinica"),
    ("Dengue", "transmitidaPor", "AedesAegypti"),
    ("Dengue", "temManifestacao", "Hemorragia"),
    ("AedesAegypti", "vetorDe", "DENV"),        # inversa de uma propriedade inferida
    ("DENV", "pertenceATaxon", "Flaviviridae"),  # transitiva
    ("Dengue", "ocorreEm", "AmericaDoSul"),     # cadeia ocorreEm o parteDe, 4 saltos
    ("Zika", "diagnosticoDiferencialCom", "Dengue"),  # simétrica
    ("CHIKV", "pertenceATaxon", "Togaviridae"),  # sameAs + transitiva
    ("FebreOropouche", "prevenidaPor", "ManejoDeMateriaOrganica"),  # R1
    ("FebreMayaro", "diagnosticoDiferencialCom", "Chikungunya"),    # R2
])
def test_triplas_esperadas_no_fecho(grafos, s, p, o):
    g, fecho, _, _ = grafos
    t = (ARBO[s], p if isinstance(p, URIRef) else ARBO[p], ARBO[o])
    assert t not in g, "a tripla deveria ser nova, não assertada"
    assert t in fecho


def test_r1_usa_so_vetor_principal(grafos):
    # Aedes aegypti é vetor secundário (urbano) da febre amarela: R1 não deve disparar
    _, fecho, _, _ = grafos
    assert (ARBO.FebreAmarela, ARBO.prevenidaPor, ARBO.EliminacaoDeCriadouros) not in fecho


def test_fecho_contem_entrada_e_nao_altera_original(grafos):
    g, fecho, _, _ = grafos
    n = len(g)
    assert all(t in fecho for t in g)
    assert len(construir_grafo()) == n


def test_ponto_fixo_idempotente(grafos):
    _, fecho, _, _ = grafos
    de_novo, procedencia, iteracoes = materializar(fecho)
    assert len(de_novo) == len(fecho)
    assert procedencia == {} and iteracoes == []


def test_ordem_das_regras_nao_muda_resultado(grafos):
    g, fecho, _, _ = grafos
    invertidas = dict(reversed(list(REGRAS.items())))
    outro, _, _ = materializar(g, invertidas)
    assert set(outro) == set(fecho)


def test_transitiva_em_grafo_minimo():
    g = Graph()
    g.add((ARBO.parteDe, RDF.type, OWL.TransitiveProperty))
    cadeia = ["a", "b", "c", "d"]
    for x, y in zip(cadeia, cadeia[1:]):
        g.add((ARBO[x], ARBO.parteDe, ARBO[y]))
    fecho, _, _ = materializar(g)
    pares = set(fecho.subject_objects(ARBO.parteDe))
    assert len(pares) == 6  # todos os pares i < j
    assert (ARBO.a, ARBO.d) in pares


def test_procedencia_cobre_todas_as_novas(grafos):
    g, fecho, procedencia, iteracoes = grafos
    assert len(procedencia) == len(fecho) - len(g) == sum(iteracoes)


def test_consultas_antes_e_depois(grafos):
    g, fecho, _, _ = grafos
    assert consultar(g, "C1 arboviroses") == []
    assert len(consultar(fecho, "C1 arboviroses")) == 7
    # a versão com property paths responde no grafo assertado o mesmo que a materializada
    assert consultar(g, "C2_caminho") == consultar(fecho, "C2 vírus da família Flaviviridae")
    assert consultar(g, "C4_caminho") == consultar(fecho, "C4 doenças que ocorrem no Nordeste")
    assert consultar(g, "C3_caminho") == consultar(fecho, "C3 doenças transmitidas por insetos")


def test_confere_com_owlrl(grafos):
    """Sem as regras do domínio, o fecho deve bater com o OWL 2 RL do pacote owlrl."""
    owlrl = pytest.importorskip("owlrl")
    g, _, _, _ = grafos
    regras = {k: v for k, v in REGRAS.items() if not k.startswith("R")}
    meu, _, _ = materializar(g, regras)
    ref = Graph()
    for t in g:
        ref.add(t)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(ref)

    base, extras = str(ARBO), (RDF.type, RDFS.subClassOf, RDFS.subPropertyOf, OWL.sameAs)

    def nivel_dominio(gr):
        # owlrl também gera triplas reflexivas (C subClassOf C, x sameAs x) e axiomas
        # sobre o vocabulário OWL; a comparação fica no vocabulário arbo, sem reflexivas
        return {(s, p, o) for s, p, o in gr
                if str(s).startswith(base) and isinstance(o, URIRef) and str(o).startswith(base)
                and s != o and "cadeia_" not in str(s)
                and (str(p).startswith(base) or p in extras)}

    assert nivel_dominio(meu) == nivel_dominio(ref)
