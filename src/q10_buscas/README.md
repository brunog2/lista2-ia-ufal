# Questão 10: buscas no mapa de entregas

Rota de menor tempo de A até I num grafo de nove localidades, resolvida com BFS, DFS, UCS e A*, mais a variante em que o entregador precisa passar por D e F antes de I. A resposta escrita, com todas as tabelas de trace, está em [`docs/q10_buscas.md`](../../docs/q10_buscas.md).

**Dupla:** Bruno Gomes de Barros Filho (21111360); Antônio Rodrigo Lima de Andrade Tenório (23210707). ECOM031: Inteligência Artificial. Prof. Evandro de Barros Costa. 2026.2.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `q10_problema.py` | Trechos e heurística do enunciado, `dijkstra`, a interface `Problema` (estilo AIMA), `ProblemaRota` (estado = localidade), `ProblemaRotaDF` (estado = (localidade, visitouD, visitouF)) e as heurísticas `h_enunciado`, `h_nula` e `criar_h_paradas` (h_DF) |
| `q10_algoritmos.py` | `bfs`, `dfs`, `ucs` e `a_estrela` sobre um núcleo comum de busca em grafo que registra cada passo (nó retirado, g, h, sucessores gerados e o que aconteceu com cada um, fronteira e explorados). Também tem `verificar_heuristica` (admissibilidade contra h* e consistência em cada transição), `tabela_trace` (Markdown) e `resumo` |
| `test_q10_buscas.py` | 15 testes: rotas, custos e ordens de expansão de cada algoritmo, A* com h = 0 igual à UCS, verificação das heurísticas, variante D/F |
| `q10_buscas.ipynb` | Notebook executado com todas as tabelas e figuras |
| `figures/` | `q10_grafo.png`, `q10_heuristica.png`, `q10_rotas.png`, `q10_expansoes.png`, `q10_variante_df.png` |

## Como rodar

Da raiz do repositório:

```bash
.venv/bin/python -m pytest src/q10_buscas -q
cd src/q10_buscas && ../../.venv/bin/jupyter nbconvert --to notebook --execute --inplace q10_buscas.ipynb
```

Uso direto (de dentro de `src/q10_buscas`):

```python
from q10_problema import ProblemaRota, h_enunciado
from q10_algoritmos import a_estrela, tabela_trace

r = a_estrela(ProblemaRota(), h_enunciado)
print(r.rota, r.custo, r.expandidos)
print(tabela_trace(r))
```

## Convenções

Busca em grafo com conjunto de explorados (AIMA, fig. 3.7); sucessores em ordem alfabética; BFS testa o objetivo na geração e os demais na expansão; DFS empilha os filhos em ordem inversa; UCS e A* substituem a entrada da fronteira quando acham g menor; desempate FIFO na fila de prioridade (`desempate_por_h=True` usa (f, h, inserção)). O enunciado escreve "Busca em Profundidade (BFS)"; por isso rodamos BFS e DFS.

## Resultados

| Algoritmo | Rota | Custo | Expandidos | Gerados |
| --- | --- | --- | --- | --- |
| BFS | A → B → C → F → I | 15 | 7 | 20 |
| DFS | A → B → C → F → I | 15 | 4 | 11 |
| UCS | A → B → E → F → I | 13 | 8 | 23 |
| A* | A → B → E → F → I | 13 | 6 | 19 |
| A* (desempate por h) | A → B → E → H → I | 13 | 5 | 16 |

- A heurística do enunciado é admissível e consistente. h*(n) por Dijkstra: A 13, B 9, C 6, D 11, E 7, F 4, G 5, H 2, I 0. Cinco arestas dirigidas têm folga zero (B→E, C→F, F→I, G→H, H→I).
- Há duas rotas ótimas de 13 minutos; qual aparece depende do desempate.
- A* com h = 0 reproduz exatamente a ordem de expansão da UCS.
- Variante D/F: rota ótima A → D → E → F → I, 14 minutos. UCS expande 20 estados, A* com h(n) expande 12 e A* com a heurística proposta h_DF(n, vD, vF) = max(h(n), δ(n, m) + h(m) para cada parada m pendente) expande 4. h_DF foi provada e verificada admissível e consistente nos 32 estados alcançáveis.
