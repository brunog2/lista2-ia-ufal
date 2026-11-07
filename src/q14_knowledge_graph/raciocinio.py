"""Inferência dedutiva por materialização (encadeamento para frente até o ponto fixo).

Cada regra é uma função que recebe o grafo atual e devolve as triplas que ela conclui.
O laço aplica todas as regras, junta o que é novo e repete até nenhuma regra produzir
tripla nova. Como as regras só adicionam (são monotônicas) e o conjunto de termos é
finito, o ponto fixo existe e é único: a ordem das regras não muda o resultado.

Regras implementadas:
- RDFS: rdfs2 (domínio), rdfs3 (alcance), rdfs5 (subPropertyOf transitiva),
  rdfs7 (herança de propriedade), rdfs9 (herança de tipo), rdfs11 (subClassOf transitiva);
- OWL 2 RL: prp-inv (inversa), prp-symp (simétrica), prp-trp (transitiva),
  prp-spo2 (cadeia de propriedades de tamanho 2), eq-sym/eq-trans/eq-rep-s/eq-rep-o (sameAs);
- regras do domínio, escritas como SPARQL CONSTRUCT (R1 e R2, ver abaixo).
"""

from collections import Counter

from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

from kg import ARBO


# ----------------------------------------------------------------------------- RDFS

def rdfs2_dominio(g):
    for p, c in g.subject_objects(RDFS.domain):
        for x in g.subjects(p, None):
            yield (x, RDF.type, c)


def rdfs3_alcance(g):
    for p, c in g.subject_objects(RDFS.range):
        for y in g.objects(None, p):
            if isinstance(y, URIRef):  # literal não pode ser sujeito de rdf:type
                yield (y, RDF.type, c)


def rdfs5_subpropriedade_transitiva(g):
    for p, q in g.subject_objects(RDFS.subPropertyOf):
        for r in g.objects(q, RDFS.subPropertyOf):
            yield (p, RDFS.subPropertyOf, r)


def rdfs7_heranca_de_propriedade(g):
    for p, q in g.subject_objects(RDFS.subPropertyOf):
        for x, y in g.subject_objects(p):
            yield (x, q, y)


def rdfs9_heranca_de_tipo(g):
    for c, d in g.subject_objects(RDFS.subClassOf):
        for x in g.subjects(RDF.type, c):
            yield (x, RDF.type, d)


def rdfs11_subclasse_transitiva(g):
    for c, d in g.subject_objects(RDFS.subClassOf):
        for e in g.objects(d, RDFS.subClassOf):
            yield (c, RDFS.subClassOf, e)


# ----------------------------------------------------------------------------- OWL 2 RL

def owl_inversa(g):
    for p, q in g.subject_objects(OWL.inverseOf):
        for x, y in g.subject_objects(p):
            yield (y, q, x)
        for x, y in g.subject_objects(q):
            yield (y, p, x)


def owl_simetrica(g):
    for p in g.subjects(RDF.type, OWL.SymmetricProperty):
        for x, y in g.subject_objects(p):
            yield (y, p, x)


def owl_transitiva(g):
    for p in g.subjects(RDF.type, OWL.TransitiveProperty):
        for x, y in g.subject_objects(p):
            for z in g.objects(y, p):
                yield (x, p, z)


def owl_cadeia(g):
    for p, lista in g.subject_objects(OWL.propertyChainAxiom):
        p1, p2 = list(Collection(g, lista))  # shortcut: só cadeias de tamanho 2, as únicas do esquema
        for x, y in g.subject_objects(p1):
            for z in g.objects(y, p2):
                yield (x, p, z)


def owl_sameas(g):
    pares = list(g.subject_objects(OWL.sameAs))
    for a, b in pares:
        yield (b, OWL.sameAs, a)
        for c in g.objects(b, OWL.sameAs):
            if c != a:
                yield (a, OWL.sameAs, c)
        for p, o in g.predicate_objects(a):  # eq-rep-s: b herda o que se diz de a
            if p != OWL.sameAs:
                yield (b, p, o)
        for s, p in g.subject_predicates(a):  # eq-rep-o
            if p != OWL.sameAs:
                yield (s, p, b)


# ----------------------------------------------------------------------------- regras do domínio

# R1: controlar o vetor principal de um vírus previne a doença que ele causa.
R1_CONTROLE_PREVINE = """
CONSTRUCT { ?doenca arbo:prevenidaPor ?medida }
WHERE {
  ?medida  arbo:combate ?vetor .
  ?virus   arbo:vetorPrincipal ?vetor .
  ?doenca  arbo:causadaPor ?virus .
}"""

# R2: duas arboviroses que compartilham pelo menos 5 sintomas entram no diagnóstico
# diferencial uma da outra. É monotônica: mais sintomas nunca removem a conclusão.
R2_DIAGNOSTICO_DIFERENCIAL = """
CONSTRUCT { ?d1 arbo:diagnosticoDiferencialCom ?d2 }
WHERE {
  { SELECT ?d1 ?d2 (COUNT(DISTINCT ?s) AS ?comuns)
    WHERE {
      ?d1 a arbo:Arbovirose ; arbo:temSintoma ?s .
      ?d2 a arbo:Arbovirose ; arbo:temSintoma ?s .
      FILTER (?d1 != ?d2)
    }
    GROUP BY ?d1 ?d2 }
  FILTER (?comuns >= 5)
}"""


def _regra_sparql(consulta):
    def regra(g):
        yield from g.query(consulta, initNs={"arbo": ARBO})
    return regra


REGRAS = {
    "rdfs2 domínio": rdfs2_dominio,
    "rdfs3 alcance": rdfs3_alcance,
    "rdfs5 subPropertyOf trans.": rdfs5_subpropriedade_transitiva,
    "rdfs7 subPropertyOf": rdfs7_heranca_de_propriedade,
    "rdfs9 subClassOf": rdfs9_heranca_de_tipo,
    "rdfs11 subClassOf trans.": rdfs11_subclasse_transitiva,
    "owl inverseOf": owl_inversa,
    "owl SymmetricProperty": owl_simetrica,
    "owl TransitiveProperty": owl_transitiva,
    "owl propertyChainAxiom": owl_cadeia,
    "owl sameAs": owl_sameas,
    "R1 controle previne": _regra_sparql(R1_CONTROLE_PREVINE),
    "R2 diag. diferencial": _regra_sparql(R2_DIAGNOSTICO_DIFERENCIAL),
}


def materializar(g: Graph, regras: dict = REGRAS, verbose: bool = False):
    """Devolve (fecho, procedência, novas_por_iteração) sem alterar o grafo de entrada.

    procedência[tripla] = nome da primeira regra que a derivou (usada para contar o
    efeito de cada regra e para desenhar as arestas inferidas).
    """
    fecho = Graph()
    for prefixo, ns in g.namespaces():
        fecho.bind(prefixo, ns)
    for t in g:
        fecho.add(t)

    procedencia, por_iteracao = {}, []
    while True:
        novas = {}
        for nome, regra in regras.items():
            for t in regra(fecho):
                if t not in fecho and t not in novas:
                    novas[t] = nome
        if not novas:
            break
        for t, nome in novas.items():
            fecho.add(t)
            procedencia[t] = nome
        por_iteracao.append(len(novas))
        if verbose:
            print(f"iteração {len(por_iteracao)}: +{len(novas)} triplas")
    return fecho, procedencia, por_iteracao


def contagem_por_regra(procedencia: dict) -> Counter:
    return Counter(procedencia.values())


# ----------------------------------------------------------------------------- consultas

PREFIXOS = "PREFIX arbo: <https://example.org/arbo#>\n"

# Cada consulta é escrita como um usuário escreveria, sem conhecer as regras.
# Nas versões "_caminho", a dedução é feita na hora da consulta com property paths
# sobre o grafo assertado (encadeamento para trás, embutido na consulta).
CONSULTAS = {
    "C1 arboviroses": """
SELECT ?x WHERE { ?x a arbo:Arbovirose }""",
    "C2 vírus da família Flaviviridae": """
SELECT ?x WHERE { ?x arbo:pertenceATaxon arbo:Flaviviridae ; a arbo:Virus }""",
    "C2_caminho": """
SELECT ?x WHERE { ?x arbo:pertenceATaxon+ arbo:Flaviviridae .
                  ?d arbo:causadaPor ?x }""",
    "C3 doenças transmitidas por insetos": """
SELECT DISTINCT ?x WHERE { ?x arbo:transmitidaPor ?v . ?v a arbo:Inseto }""",
    "C3_caminho": """
SELECT DISTINCT ?x WHERE {
  ?x arbo:causadaPor/(arbo:vetorPrincipal|arbo:vetorSecundario) ?v .
  ?v a/rdfs:subClassOf* arbo:Inseto }""",
    "C4 doenças que ocorrem no Nordeste": """
SELECT ?x WHERE { ?x arbo:ocorreEm arbo:RegiaoNordeste }""",
    "C4_caminho": """
SELECT DISTINCT ?x WHERE { ?x arbo:ocorreEm/arbo:parteDe* arbo:RegiaoNordeste }""",
    "C5 medidas que previnem a febre do Oropouche": """
SELECT ?x WHERE { arbo:FebreOropouche arbo:prevenidaPor ?x }""",
    "C6 vírus da família Togaviridae": """
SELECT ?x WHERE { ?x arbo:pertenceATaxon arbo:Togaviridae ; a arbo:Virus }""",
    "C7 diagnóstico diferencial da febre do Mayaro": """
SELECT ?x WHERE { arbo:FebreMayaro arbo:diagnosticoDiferencialCom ?x }""",
    "C8 vetores (papel inferido pelo alcance)": """
SELECT ?x WHERE { ?x a arbo:Vetor }""",
    "C9 arboviroses sem vacina registrada no grafo": """
SELECT ?x WHERE { ?x a arbo:Arbovirose .
                  FILTER NOT EXISTS { ?x arbo:prevenidaPor ?v . ?v a arbo:Vacina } }""",
}


def consultar(g: Graph, nome: str) -> list:
    """Executa uma consulta de CONSULTAS e devolve os rótulos das respostas, ordenados."""
    rotulos = []
    for (x,) in g.query(PREFIXOS + CONSULTAS[nome]):
        rotulos.append(str(min(g.objects(x, RDFS.label), default=x)))  # min: determinístico com sameAs
    return sorted(set(rotulos))
