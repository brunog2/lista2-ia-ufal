// Consultas equivalentes às de raciocinio.py, sobre o grafo ASSERTADO carregado por arboviroses.cypher.
// O Neo4j não aplica RDFS/OWL; cada consulta embute a regra que o raciocinador aplicaria.

// C1 arboviroses: domínio de transmitidaPor + cadeia causadaPor o temVetor.
// "Doença cujo vírus tem algum vetor" é a definição que o raciocinador usou.
MATCH (d:Entidade)-[:CAUSADA_POR]->(:Entidade)-[:VETOR_PRINCIPAL|VETOR_SECUNDARIO]->(:Entidade)
RETURN 'C1' AS consulta, collect(DISTINCT d.rotulo) AS respostas;

// C2 vírus da família Flaviviridae: transitividade vira caminho de tamanho variável.
MATCH (d:Entidade)-[:CAUSADA_POR]->(v:Entidade)-[:PERTENCE_A_TAXON*1..]->(:Entidade {nome: 'Flaviviridae'})
RETURN 'C2' AS consulta, collect(DISTINCT v.rotulo) AS respostas;

// C3 doenças transmitidas por insetos: hierarquia de classes percorrida em tempo de consulta.
MATCH (d:Entidade)-[:CAUSADA_POR]->(:Entidade)-[:VETOR_PRINCIPAL|VETOR_SECUNDARIO]->(v:Entidade)
      -[:INSTANCIA_DE]->(:Classe)-[:SUBCLASSE_DE*0..]->(:Classe {nome: 'Inseto'})
RETURN 'C3' AS consulta, collect(DISTINCT d.rotulo) AS respostas;

// C4 doenças que ocorrem no Nordeste: cadeia ocorreEm o parteDe*.
MATCH (d:Entidade)-[:OCORRE_EM]->(:Entidade)-[:PARTE_DE*0..]->(:Entidade {nome: 'RegiaoNordeste'})
RETURN 'C4' AS consulta, collect(DISTINCT d.rotulo) AS respostas;

// C5 regra R1 como escrita (materialização em Cypher): controlar o vetor principal previne a doença.
MATCH (m:Entidade)-[:COMBATE]->(vet:Entidade)<-[:VETOR_PRINCIPAL]-(:Entidade)<-[:CAUSADA_POR]-(d:Entidade)
MERGE (d)-[r:PREVENIDA_POR]->(m)
SET r.inferidaPor = 'R1';

MATCH (:Entidade {nome: 'FebreOropouche'})-[:PREVENIDA_POR|TEM_VACINA]->(m:Entidade)
RETURN 'C5' AS consulta, collect(m.rotulo) AS respostas;

// C6 vírus da família Togaviridae: a identidade (sameAs) também vira caminho, em qualquer sentido.
MATCH (d:Entidade)-[:CAUSADA_POR]->(v:Entidade)-[:MESMO_QUE*0..1]-(:Entidade)
      -[:PERTENCE_A_TAXON*1..]->(:Entidade {nome: 'Togaviridae'})
RETURN 'C6' AS consulta, collect(DISTINCT v.rotulo) AS respostas;

// C7 regra R2 (diagnóstico diferencial por >= 5 sintomas em comum) + simetria + asserções.
MATCH (a:Entidade {nome: 'FebreMayaro'})-[:TEM_SINTOMA]->(s:Entidade)<-[:TEM_SINTOMA]-(b:Entidade)
WITH a, b, count(DISTINCT s) AS comuns
WHERE comuns >= 5
RETURN 'C7' AS consulta, collect(b.rotulo + ' (' + toString(comuns) + ')') AS respostas;

// C9 arboviroses sem vacina registrada: mundo fechado é o comportamento natural do Cypher.
MATCH (d:Entidade)-[:CAUSADA_POR]->(:Entidade)-[:VETOR_PRINCIPAL|VETOR_SECUNDARIO]->(:Entidade)
WHERE NOT (d)-[:TEM_VACINA]->()
RETURN 'C9' AS consulta, collect(DISTINCT d.rotulo) AS respostas;

// Extra: caminho mais curto entre duas doenças (consulta de caminho sem equivalente direto em SPARQL).
MATCH p = shortestPath((a:Entidade {nome: 'FebreDoNiloOcidental'})-[*]-(b:Entidade {nome: 'FebreOropouche'}))
RETURN 'caminho' AS consulta, [n IN nodes(p) | n.rotulo] AS respostas;

// Extra: qualificador na aresta (o equivalente em RDF exigiria reificação ou RDF-star).
MATCH (d:Entidade)-[r:OCORRE_EM]->(l:Entidade) WHERE r.primeiroCasoHumano IS NOT NULL
RETURN 'qualificador' AS consulta, [d.rotulo, l.rotulo, toString(r.primeiroCasoHumano)] AS respostas;
