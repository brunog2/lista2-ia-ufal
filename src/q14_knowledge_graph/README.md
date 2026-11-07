# Questão 14: grafo de conhecimento sobre arboviroses

**Dupla:** Bruno Gomes de Barros Filho (21111360); Antônio Rodrigo Lima de Andrade Tenório (23210707)  
**Disciplina:** ECOM031: Inteligência Artificial. Prof. Evandro de Barros Costa. 2026.2

Grafo de conhecimento (KG) pequeno sobre as arboviroses que circulam no Brasil: dengue, Zika,
chikungunya, febre amarela, Oropouche, Mayaro e Nilo Ocidental, com seus vírus, vetores,
hospedeiros, sintomas, complicações, exames, vacinas, medidas de controle vetorial e regiões
de ocorrência. Em cima dele rodam três coisas:

1. inferência dedutiva por materialização (RDFS, um fragmento do OWL 2 RL e duas regras do domínio), implementada em Python como um laço até o ponto fixo;
2. aprendizagem de embeddings TransE em numpy para previsão de links, com avaliação filtrada por MRR e Hits@k;
3. a mesma base no Neo4j, com as consultas reescritas em Cypher e validadas num container.

O ensaio da questão está em [`docs/q14_knowledge_graphs.md`](../../docs/q14_knowledge_graphs.md).
Os fatos são uma simplificação didática e não servem para decisão clínica.

## Como rodar

Da raiz do repositório:

```bash
# testes (materialização, idempotência, conferência com owlrl, métricas de ranking, TransE)
.venv/bin/python -m pytest src/q14_knowledge_graph -q

# regenera o Turtle e o script Cypher a partir das tabelas de kg.py
cd src/q14_knowledge_graph && ../../.venv/bin/python kg.py

# executa o notebook do zero (cerca de 40 s; gera figures/*.png e dados/arboviroses_inferido.ttl)
../../.venv/bin/jupyter nbconvert --to notebook --execute --inplace q14_knowledge_graph.ipynb

# valida no Neo4j (precisa de Docker; sobe e remove um container temporário)
bash neo4j/validar_neo4j.sh
```

Dependências: `rdflib`, `numpy`, `pandas`, `matplotlib`, `networkx`, `scikit-learn` (já no
`.venv`) e `owlrl`, usado só para conferir a materialização. Sem o `owlrl`, o teste
correspondente é pulado e o resto funciona.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `kg.py` | Esquema (classes, propriedades, axiomas OWL) e fatos em tabelas; monta o `rdflib.Graph`, salva em Turtle e gera o Cypher |
| `raciocinio.py` | Regras de inferência, `materializar` (ponto fixo com procedência por regra) e as consultas SPARQL C1 a C9 |
| `transe.py` | TransE em numpy, divisão treino/teste, baselines, ranking filtrado, métricas e o experimento completo |
| `q14_knowledge_graph.ipynb` | Execução e análise, com saídas |
| `dados/arboviroses.ttl` | Grafo assertado (381 triplas), versionado |
| `dados/arboviroses_inferido.ttl` | Grafo materializado (744 triplas), gerado pelo notebook |
| `neo4j/arboviroses.cypher` | Script gerado que cria o grafo assertado no Neo4j |
| `neo4j/consultas.cypher` | Consultas equivalentes em Cypher, incluindo a regra R1 como `MERGE` |
| `neo4j/validar_neo4j.sh` | Sobe `neo4j:5.26-community` sem autenticação, roda os scripts e remove o container |
| `neo4j/saida_validacao.txt` | Saída da última validação |
| `test_q14_inferencia.py`, `test_q14_transe.py` | 29 testes |
| `figures/` | Figuras PNG usadas no ensaio |

## Modelagem

Namespace `arbo: <https://example.org/arbo#>`. O esquema tem 30 classes e 20 propriedades de
objeto. Os papéis `Vetor`, `Arbovirus` e `Arbovirose` nunca aparecem nos dados: um mosquito vira
`Vetor` por estar no alcance de `temVetor`, um vírus vira `Arbovirus` por estar no domínio, e uma
doença vira `Arbovirose` porque a cadeia `causadaPor ∘ temVetor` gera `transmitidaPor`, cujo
domínio é `Arbovirose`.

Regras aplicadas pelo materializador:

| Grupo | Regras |
| --- | --- |
| RDFS | domínio (rdfs2), alcance (rdfs3), subPropertyOf (rdfs5, rdfs7), subClassOf (rdfs9, rdfs11) |
| OWL 2 RL | `inverseOf` (causadaPor/causa, temVetor/vetorDe), `TransitiveProperty` (pertenceATaxon, parteDe), `SymmetricProperty` (diagnosticoDiferencialCom), `propertyChainAxiom` (transmitidaPor = causadaPor ∘ temVetor; ocorreEm ∘ parteDe ⊑ ocorreEm), `sameAs` |
| R1 (SPARQL CONSTRUCT) | se uma medida combate o vetor principal de um vírus, ela previne a doença causada por ele |
| R2 (SPARQL CONSTRUCT) | arboviroses com pelo menos 5 sintomas em comum entram no diagnóstico diferencial uma da outra |

Para testar identidade de entidades, o gênero do vírus chikungunya só existe numa "fonte B"
que usa outra IRI (`arbo:VirusChikungunya owl:sameAs arbo:CHIKV`).

## Resultados

Materialização: 381 → 744 triplas em 4 iterações (+214, +118, +10, +21); os fatos relacionais
entre indivíduos passam de 156 para 338. Rodar de novo sobre o fecho acrescenta 0 triplas, e
inverter a ordem das regras dá o mesmo fecho. Sem R1 e R2, o fecho coincide com o do `owlrl`
(OWL 2 RL) nas 550 triplas do vocabulário `arbo` (fora as reflexivas, que o `owlrl` também gera).

| Consulta SPARQL | Respostas no grafo assertado | Depois da inferência |
| --- | ---: | ---: |
| C1 arboviroses | 0 | 7 |
| C2 vírus da família Flaviviridae | 0 | 4 |
| C3 doenças transmitidas por insetos | 0 | 7 |
| C4 doenças que ocorrem no Nordeste | 2 | 5 |
| C5 medidas que previnem a febre do Oropouche | 0 | 1 |
| C6 vírus da família Togaviridae | 0 | 2 |
| C7 diagnóstico diferencial da febre do Mayaro | 0 | 3 |
| C8 vetores | 0 | 7 |
| C9 arboviroses sem vacina registrada | 0 | 4 |

As versões de C2, C3 e C4 com *property paths* (`pertenceATaxon+`, `parteDe*`,
`a/rdfs:subClassOf*`) dão no grafo assertado a mesma resposta da versão materializada.

Previsão de links: 10 divisões aleatórias, 15% dos 156 fatos no teste (17,4 triplas em média,
cada uma gera uma consulta de cabeça e uma de cauda), ranking filtrado contra 78 entidades.
TransE com dimensão 64 e margem 1,0, escolhidas numa validação tirada do treino.

| Modelo | MRR | Hits@1 | Hits@3 | Hits@10 | MR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aleatório | 0,062 ± 0,014 | 0,006 | 0,043 | 0,131 | 37,6 |
| Frequência por relação | 0,506 ± 0,070 | 0,361 | 0,571 | 0,688 | 14,0 |
| TransE, fatos assertados | 0,602 ± 0,040 | 0,431 | 0,700 | 0,980 | 3,2 |
| TransE, treino materializado | 0,600 ± 0,063 | 0,407 | 0,743 | 0,988 | 3,1 |

O TransE supera o baseline de frequência, mas treinar no grafo materializado (cerca de 285
triplas contra 139) não mudou o MRR de forma mensurável com testes deste tamanho. Em 2 das 10
divisões o raciocinador recuperou sozinho uma tripla de teste (dengue e Zika, dengue e chikungunya
no diagnóstico diferencial, pela regra R2).

Neo4j: validado em `neo4j:5.26-community` (78 entidades, 29 classes, 206 relações). As 8
consultas em Cypher sobre o grafo assertado devolvem os mesmos conjuntos que o SPARQL sobre o
grafo materializado; a saída está em `neo4j/saida_validacao.txt` e o container é removido no fim
do script.

## Limitações

- O grafo é pequeno (78 entidades, 156 fatos). Com cerca de 35 consultas de ranking por divisão, diferenças de 0,05 no MRR ficam dentro do desvio padrão entre divisões.
- O TransE não conhece tipos: para `(FebreMayaro, vetorSecundario, ?)` ele sugere chikungunya e Zika antes do primeiro mosquito.
- O materializador é ingênuo (reaplica todas as regras a cada iteração). Para este tamanho leva cerca de 0,15 s; um grafo grande pediria avaliação seminaive ou um raciocinador dedicado.
- A cadeia de propriedades só aceita tamanho 2, que é o que o esquema usa.
