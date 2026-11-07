"""Grafo de conhecimento sobre arboviroses no Brasil (Questão 14, Lista 2 de IA, UFAL).

Monta o grafo em RDF com rdflib a partir de tabelas pequenas, define um esquema
RDFS/OWL leve e exporta o resultado em Turtle (para versionar) e em Cypher (para o Neo4j).

Convenções do esquema:
- Classes de papel (Vetor, Arbovirus, Arbovirose) quase nunca são declaradas nos dados;
  elas aparecem por inferência a partir de domínio, alcance e cadeias de propriedades.
- Os tipos taxonômicos (Mosquito, Genero, Estado...) são declarados, porque são fatos.
"""

from pathlib import Path
import re

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

ARBO = Namespace("https://example.org/arbo#")
PASTA = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Esquema (TBox)
# ---------------------------------------------------------------------------

SUBCLASSES = [
    ("Virus", "AgenteBiologico"),
    ("Arbovirus", "Virus"),
    ("Artropode", "AgenteBiologico"),
    ("Inseto", "Artropode"),
    ("Mosquito", "Inseto"),
    ("Maruim", "Inseto"),
    ("Vetor", "AgenteBiologico"),
    ("Hospedeiro", "AgenteBiologico"),
    ("DoencaInfecciosa", "Doenca"),
    ("Arbovirose", "DoencaInfecciosa"),
    ("Sintoma", "ManifestacaoClinica"),
    ("Complicacao", "ManifestacaoClinica"),
    ("Vacina", "MedidaPreventiva"),
    ("ControleVetorial", "MedidaPreventiva"),
    ("MedidaPreventiva", "Intervencao"),
    ("ExameDiagnostico", "Intervencao"),
    ("Genero", "TaxonViral"),
    ("Familia", "TaxonViral"),
    ("Continente", "Regiao"),
    ("Pais", "Regiao"),
    ("MacroRegiao", "Regiao"),
    ("Estado", "Regiao"),
    ("Municipio", "Regiao"),
]

# nome: (domínio, alcance, superpropriedade)
PROPRIEDADES = {
    "causadaPor": ("Doenca", "Virus", None),
    "causa": (None, None, None),
    "temVetor": ("Arbovirus", "Vetor", None),
    "vetorPrincipal": (None, None, "temVetor"),
    "vetorSecundario": (None, None, "temVetor"),
    "vetorDe": (None, None, None),
    "transmitidaPor": ("Arbovirose", "Vetor", None),
    "pertenceATaxon": (None, "TaxonViral", None),
    "hospedeiroAmplificador": ("Arbovirus", "Hospedeiro", None),
    "ambiente": (None, "AmbienteDeTransmissao", None),
    "temManifestacao": ("Doenca", "ManifestacaoClinica", None),
    "temSintoma": (None, "Sintoma", "temManifestacao"),
    "podeEvoluirPara": (None, "Complicacao", "temManifestacao"),
    "diagnosticadaPor": ("Doenca", "ExameDiagnostico", None),
    "prevenidaPor": ("Doenca", "MedidaPreventiva", None),
    "temVacina": (None, "Vacina", "prevenidaPor"),
    "combate": ("ControleVetorial", "Vetor", None),
    "ocorreEm": ("Doenca", "Regiao", None),
    "parteDe": ("Regiao", "Regiao", None),
    "diagnosticoDiferencialCom": ("Doenca", "Doenca", None),
}

INVERSAS = [("causadaPor", "causa"), ("temVetor", "vetorDe")]
TRANSITIVAS = ["pertenceATaxon", "parteDe"]
SIMETRICAS = ["diagnosticoDiferencialCom"]
# propriedade derivada <- (p1, p2):  x p1 y, y p2 z  =>  x derivada z
CADEIAS = [
    ("transmitidaPor", ("causadaPor", "temVetor")),
    ("ocorreEm", ("ocorreEm", "parteDe")),
]

# ---------------------------------------------------------------------------
# Fatos (ABox)
# ---------------------------------------------------------------------------

TIPOS = {
    "Mosquito": ["AedesAegypti", "AedesAlbopictus", "CulexQuinquefasciatus",
                 "HaemagogusJanthinomys", "HaemagogusLeucocelaenus", "SabethesChloropterus"],
    "Maruim": ["CulicoidesParaensis"],
    "Genero": ["Orthoflavivirus", "Alphavirus", "Orthobunyavirus"],
    "Familia": ["Flaviviridae", "Togaviridae", "Peribunyaviridae"],
    "ControleVetorial": ["EliminacaoDeCriadouros", "MetodoWolbachia", "ManejoDeMateriaOrganica"],
    "Continente": ["AmericaDoSul"],
    "Pais": ["Brasil"],
    "MacroRegiao": ["RegiaoNorte", "RegiaoNordeste", "RegiaoCentroOeste", "RegiaoSudeste", "RegiaoSul"],
    "Estado": ["Alagoas", "Piaui"],
    "Municipio": ["Maceio"],
}

# Cada doença: vírus causador e listas de objetos por propriedade.
DOENCAS = {
    "Dengue": dict(
        causadaPor="DENV",
        temSintoma=["Febre", "Cefaleia", "DorRetroOrbital", "Mialgia", "Artralgia",
                    "Exantema", "Nausea", "Prurido"],
        podeEvoluirPara=["ChoqueHipovolemico", "Hemorragia"],
        diagnosticadaPor=["RTqPCR", "AntigenoNS1", "SorologiaIgM"],
        temVacina=["VacinaQdenga"],
        ocorreEm=["Maceio", "RegiaoNorte", "RegiaoCentroOeste", "RegiaoSudeste", "RegiaoSul"],
    ),
    "Zika": dict(
        causadaPor="ZIKV",
        temSintoma=["Exantema", "Prurido", "Conjuntivite", "Febre", "Artralgia",
                    "Cefaleia", "Mialgia", "EdemaArticular"],
        podeEvoluirPara=["SindromeCongenitaDoZika", "SindromeDeGuillainBarre"],
        diagnosticadaPor=["RTqPCR", "SorologiaIgM", "PRNT"],
        ocorreEm=["RegiaoNordeste", "RegiaoSudeste"],
    ),
    "Chikungunya": dict(
        causadaPor="CHIKV",
        temSintoma=["Febre", "Artralgia", "EdemaArticular", "Exantema", "Mialgia", "Cefaleia"],
        podeEvoluirPara=["ArtralgiaCronica"],
        diagnosticadaPor=["RTqPCR", "SorologiaIgM"],
        temVacina=["VacinaChikungunyaVLA1553"],
        ocorreEm=["Alagoas", "RegiaoSudeste"],
    ),
    "FebreAmarela": dict(
        causadaPor="YFV",
        temSintoma=["Febre", "Calafrios", "Cefaleia", "Mialgia", "Nausea", "Ictericia"],
        podeEvoluirPara=["Hemorragia", "InsuficienciaHepatica", "InsuficienciaRenal"],
        diagnosticadaPor=["RTqPCR", "SorologiaIgM", "Imunohistoquimica"],
        temVacina=["VacinaFebreAmarela17DD"],
        ocorreEm=["RegiaoNorte", "RegiaoCentroOeste", "RegiaoSudeste"],
    ),
    "FebreOropouche": dict(
        causadaPor="OROV",
        temSintoma=["Febre", "Cefaleia", "Mialgia", "Artralgia", "Calafrios", "Fotofobia", "Nausea"],
        podeEvoluirPara=["Meningoencefalite"],
        diagnosticadaPor=["RTqPCR"],
        ocorreEm=["RegiaoNorte", "RegiaoNordeste"],
    ),
    "FebreMayaro": dict(
        causadaPor="MAYV",
        temSintoma=["Febre", "Artralgia", "EdemaArticular", "Exantema", "Mialgia", "Cefaleia"],
        podeEvoluirPara=["ArtralgiaCronica"],
        diagnosticadaPor=["RTqPCR", "SorologiaIgM"],
        ocorreEm=["RegiaoNorte", "RegiaoCentroOeste"],
    ),
    "FebreDoNiloOcidental": dict(
        causadaPor="WNV",
        temSintoma=["Febre", "Cefaleia", "Mialgia", "Exantema", "Nausea"],
        podeEvoluirPara=["Meningoencefalite", "ParalisiaFlacidaAguda"],
        diagnosticadaPor=["RTqPCR", "SorologiaIgM"],
        ocorreEm=["Piaui"],
    ),
}

# Vírus: gênero, vetores e hospedeiro amplificador.
# O CHIKV fica sem gênero de propósito: essa informação vem da "fonte B" (ver ALIAS).
VIRUS = {
    "DENV": dict(pertenceATaxon=["Orthoflavivirus"], vetorPrincipal=["AedesAegypti"],
                 vetorSecundario=["AedesAlbopictus"], hospedeiroAmplificador=["SerHumano"]),
    "ZIKV": dict(pertenceATaxon=["Orthoflavivirus"], vetorPrincipal=["AedesAegypti"],
                 vetorSecundario=["AedesAlbopictus"], hospedeiroAmplificador=["SerHumano"]),
    "CHIKV": dict(vetorPrincipal=["AedesAegypti"], vetorSecundario=["AedesAlbopictus"],
                  hospedeiroAmplificador=["SerHumano"]),
    "YFV": dict(pertenceATaxon=["Orthoflavivirus"],
                vetorPrincipal=["HaemagogusJanthinomys", "HaemagogusLeucocelaenus"],
                vetorSecundario=["SabethesChloropterus", "AedesAegypti"],
                hospedeiroAmplificador=["PrimatasNaoHumanos"]),
    "OROV": dict(pertenceATaxon=["Orthobunyavirus"], vetorPrincipal=["CulicoidesParaensis"],
                 vetorSecundario=["CulexQuinquefasciatus"],
                 hospedeiroAmplificador=["BichoPreguica", "PrimatasNaoHumanos"]),
    "MAYV": dict(pertenceATaxon=["Alphavirus"], vetorPrincipal=["HaemagogusJanthinomys"],
                 hospedeiroAmplificador=["PrimatasNaoHumanos"]),
    "WNV": dict(pertenceATaxon=["Orthoflavivirus"], vetorPrincipal=["CulexQuinquefasciatus"],
                hospedeiroAmplificador=["Aves"]),
}

OUTROS_FATOS = [
    # taxonomia viral: gênero -> família
    ("Orthoflavivirus", "pertenceATaxon", "Flaviviridae"),
    ("Alphavirus", "pertenceATaxon", "Togaviridae"),
    ("Orthobunyavirus", "pertenceATaxon", "Peribunyaviridae"),
    # ambiente típico de cada vetor
    ("AedesAegypti", "ambiente", "Urbano"),
    ("AedesAlbopictus", "ambiente", "Periurbano"),
    ("CulexQuinquefasciatus", "ambiente", "Urbano"),
    ("HaemagogusJanthinomys", "ambiente", "Silvestre"),
    ("HaemagogusLeucocelaenus", "ambiente", "Silvestre"),
    ("SabethesChloropterus", "ambiente", "Silvestre"),
    ("CulicoidesParaensis", "ambiente", "Periurbano"),
    # controle vetorial
    ("EliminacaoDeCriadouros", "combate", "AedesAegypti"),
    ("EliminacaoDeCriadouros", "combate", "AedesAlbopictus"),
    ("EliminacaoDeCriadouros", "combate", "CulexQuinquefasciatus"),
    ("MetodoWolbachia", "combate", "AedesAegypti"),
    ("ManejoDeMateriaOrganica", "combate", "CulicoidesParaensis"),
    # geografia (cadeia usada pela regra ocorreEm o parteDe)
    ("Maceio", "parteDe", "Alagoas"),
    ("Alagoas", "parteDe", "RegiaoNordeste"),
    ("Piaui", "parteDe", "RegiaoNordeste"),
    ("RegiaoNorte", "parteDe", "Brasil"),
    ("RegiaoNordeste", "parteDe", "Brasil"),
    ("RegiaoCentroOeste", "parteDe", "Brasil"),
    ("RegiaoSudeste", "parteDe", "Brasil"),
    ("RegiaoSul", "parteDe", "Brasil"),
    ("Brasil", "parteDe", "AmericaDoSul"),
    # diagnóstico diferencial declarado (a simetria completa o outro sentido)
    ("Dengue", "diagnosticoDiferencialCom", "Zika"),
    ("Dengue", "diagnosticoDiferencialCom", "Chikungunya"),
]

# Identidade: a "fonte B" chama o vírus chikungunya por outro IRI e traz o gênero.
ALIAS = ("VirusChikungunya", "CHIKV")
FATOS_ALIAS = [("VirusChikungunya", "pertenceATaxon", "Alphavirus")]

ROTULOS = {
    "AedesAegypti": "Aedes aegypti", "AedesAlbopictus": "Aedes albopictus",
    "CulexQuinquefasciatus": "Culex quinquefasciatus",
    "HaemagogusJanthinomys": "Haemagogus janthinomys",
    "HaemagogusLeucocelaenus": "Haemagogus leucocelaenus",
    "SabethesChloropterus": "Sabethes chloropterus", "CulicoidesParaensis": "Culicoides paraensis",
    "FebreAmarela": "Febre amarela", "FebreOropouche": "Febre do Oropouche",
    "FebreMayaro": "Febre do Mayaro", "FebreDoNiloOcidental": "Febre do Nilo Ocidental",
    "DorRetroOrbital": "Dor retro-orbital", "Nausea": "Náusea", "Cefaleia": "Cefaleia",
    "Ictericia": "Icterícia", "Fotofobia": "Fotofobia",
    "ChoqueHipovolemico": "Choque hipovolêmico", "SindromeCongenitaDoZika": "Síndrome congênita do Zika",
    "SindromeDeGuillainBarre": "Síndrome de Guillain-Barré", "ArtralgiaCronica": "Artralgia crônica",
    "InsuficienciaHepatica": "Insuficiência hepática", "InsuficienciaRenal": "Insuficiência renal",
    "ParalisiaFlacidaAguda": "Paralisia flácida aguda",
    "RTqPCR": "RT-qPCR", "AntigenoNS1": "Antígeno NS1", "SorologiaIgM": "Sorologia IgM",
    "PRNT": "PRNT (neutralização)", "Imunohistoquimica": "Imuno-histoquímica",
    "VacinaQdenga": "Qdenga (TAK-003)", "VacinaChikungunyaVLA1553": "Vacina chikungunya VLA1553",
    "VacinaFebreAmarela17DD": "Vacina febre amarela 17DD",
    "EliminacaoDeCriadouros": "Eliminação de criadouros", "MetodoWolbachia": "Método Wolbachia",
    "ManejoDeMateriaOrganica": "Manejo de matéria orgânica",
    "AmericaDoSul": "América do Sul", "RegiaoNorte": "Região Norte", "RegiaoNordeste": "Região Nordeste",
    "RegiaoCentroOeste": "Região Centro-Oeste", "RegiaoSudeste": "Região Sudeste", "RegiaoSul": "Região Sul",
    "Maceio": "Maceió", "Piaui": "Piauí", "SerHumano": "Ser humano",
    "PrimatasNaoHumanos": "Primatas não humanos", "BichoPreguica": "Bicho-preguiça",
    "VirusChikungunya": "vírus chikungunya (fonte B)",
    "DENV": "DENV (vírus da dengue)", "ZIKV": "ZIKV (vírus Zika)", "CHIKV": "CHIKV (vírus chikungunya)",
    "YFV": "YFV (vírus da febre amarela)", "OROV": "OROV (vírus Oropouche)",
    "MAYV": "MAYV (vírus Mayaro)", "WNV": "WNV (vírus do Nilo Ocidental)",
}


def rotulo(nome: str) -> str:
    """Rótulo legível: usa a tabela ou separa o CamelCase."""
    return ROTULOS.get(nome) or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nome).capitalize()


def local(iri) -> str:
    """Parte local de um IRI do namespace arbo (ou o próprio texto)."""
    return str(iri).split("#")[-1]


def construir_grafo() -> Graph:
    """Monta o grafo assertado: esquema RDFS/OWL + fatos. Nada aqui é inferido."""
    g = Graph()
    g.bind("arbo", ARBO)
    g.bind("owl", OWL)

    classes = {c for par in SUBCLASSES for c in par} | {"AmbienteDeTransmissao"}
    for c in sorted(classes):
        g.add((ARBO[c], RDF.type, OWL.Class))
    for sub, sup in SUBCLASSES:
        g.add((ARBO[sub], RDFS.subClassOf, ARBO[sup]))

    for p, (dom, alc, sup) in PROPRIEDADES.items():
        g.add((ARBO[p], RDF.type, OWL.ObjectProperty))
        if dom:
            g.add((ARBO[p], RDFS.domain, ARBO[dom]))
        if alc:
            g.add((ARBO[p], RDFS.range, ARBO[alc]))
        if sup:
            g.add((ARBO[p], RDFS.subPropertyOf, ARBO[sup]))
    for p, q in INVERSAS:
        g.add((ARBO[p], OWL.inverseOf, ARBO[q]))
    for p in TRANSITIVAS:
        g.add((ARBO[p], RDF.type, OWL.TransitiveProperty))
    for p in SIMETRICAS:
        g.add((ARBO[p], RDF.type, OWL.SymmetricProperty))
    for derivada, cadeia in CADEIAS:
        lista = URIRef(f"{ARBO}cadeia_{derivada}_{'_'.join(cadeia)}")
        Collection(g, lista, [ARBO[p] for p in cadeia])
        g.add((ARBO[derivada], OWL.propertyChainAxiom, lista))

    fatos = []
    for classe, membros in TIPOS.items():
        fatos += [(m, RDF.type, ARBO[classe]) for m in membros]
    for doenca, props in DOENCAS.items():
        for p, objs in props.items():
            fatos += [(doenca, ARBO[p], o) for o in ([objs] if isinstance(objs, str) else objs)]
    for virus, props in VIRUS.items():
        fatos += [(virus, ARBO[p], o) for p, objs in props.items() for o in objs]
    fatos += [(s, ARBO[p], o) for s, p, o in OUTROS_FATOS + FATOS_ALIAS]
    fatos.append((ALIAS[0], OWL.sameAs, ALIAS[1]))

    nomes = set()
    for s, p, o in fatos:
        o = o if isinstance(o, URIRef) else ARBO[o]
        g.add((ARBO[s], p, o))
        nomes.add(s)
        if o.startswith(str(ARBO)) and p != RDF.type:
            nomes.add(local(o))
    for n in nomes:
        g.add((ARBO[n], RDFS.label, Literal(rotulo(n), lang="pt")))
    return g


def individuos(g: Graph) -> set:
    """IRIs com rótulo: são as entidades do domínio (classes e propriedades não têm rótulo)."""
    return set(g.subjects(RDFS.label, None))


def salvar_turtle(g: Graph, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=caminho, format="turtle")


# ---------------------------------------------------------------------------
# Exportação para Neo4j (grafo de propriedades)
# ---------------------------------------------------------------------------

def _rel(p: str) -> str:
    """camelCase -> MAIUSCULO_COM_UNDERSCORE, convenção de tipos de relação no Cypher."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", p).upper()


def _txt(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def exportar_cypher(g: Graph) -> str:
    """Gera um script Cypher que recria o grafo ASSERTADO no Neo4j.

    Mapeamento: cada indivíduo vira um nó :Entidade {iri, nome, rotulo}; o tipo declarado
    vira rótulo extra e também uma aresta :INSTANCIA_DE para um nó :Classe, porque o Neo4j
    não raciocina sobre subClassOf e as consultas precisam percorrer :SUBCLASSE_DE.
    Propriedades OWL (inversa, transitiva, cadeia) não têm equivalente nativo; as consultas
    em consultas.cypher reproduzem o efeito delas com padrões e caminhos de tamanho variável.
    """
    ents = individuos(g)
    linhas = [
        "// Gerado por kg.py a partir de dados/arboviroses.ttl (grafo assertado). Não editar à mão.",
        "MATCH (n) DETACH DELETE n;",
        "CREATE CONSTRAINT entidade_iri IF NOT EXISTS FOR (e:Entidade) REQUIRE e.iri IS UNIQUE;",
        "CREATE CONSTRAINT classe_nome IF NOT EXISTS FOR (c:Classe) REQUIRE c.nome IS UNIQUE;",
    ]
    for s, _, o in sorted(g.triples((None, RDFS.subClassOf, None))):
        linhas.append(f"MERGE (a:Classe {{nome: {_txt(local(s))}}}) "
                      f"MERGE (b:Classe {{nome: {_txt(local(o))}}}) MERGE (a)-[:SUBCLASSE_DE]->(b);")
    for e in sorted(ents):
        nome = local(e)
        tipos = sorted(local(t) for t in g.objects(e, RDF.type))
        labels = "".join(f":{t}" for t in tipos)
        linhas.append(f"CREATE (:Entidade{labels} {{iri: {_txt(str(e))}, nome: {_txt(nome)}, "
                      f"rotulo: {_txt(str(g.value(e, RDFS.label)))}}});")
        for t in tipos:
            linhas.append(f"MATCH (e:Entidade {{nome: {_txt(nome)}}}), (c:Classe {{nome: {_txt(t)}}}) "
                          f"MERGE (e)-[:INSTANCIA_DE]->(c);")
    for s, p, o in sorted(g):
        if s in ents and o in ents and p != RDF.type:
            tipo = "MESMO_QUE" if p == OWL.sameAs else _rel(local(p))
            linhas.append(f"MATCH (a:Entidade {{nome: {_txt(local(s))}}}), (b:Entidade {{nome: {_txt(local(o))}}}) "
                          f"CREATE (a)-[:{tipo}]->(b);")
    # qualificador em aresta, algo que o grafo de propriedades representa direto
    linhas.append("MATCH (:Entidade {nome: 'FebreDoNiloOcidental'})-[r:OCORRE_EM]->(:Entidade {nome: 'Piaui'}) "
                  "SET r.primeiroCasoHumano = 2014;")
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    grafo = construir_grafo()
    salvar_turtle(grafo, PASTA / "dados" / "arboviroses.ttl")
    (PASTA / "neo4j" / "arboviroses.cypher").write_text(exportar_cypher(grafo), encoding="utf-8")
    print(f"{len(grafo)} triplas assertadas salvas em dados/arboviroses.ttl")
