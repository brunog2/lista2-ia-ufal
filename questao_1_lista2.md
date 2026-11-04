# Lista 2 - Inteligência Artificial
**Dupla:** [Seu Nome] e Renato Coca

## Questão 1

Ontologias e Grafos de Conhecimento (KGs) são abordagens para representação de conhecimento, mas operam com focos distintos.

As **ontologias** definem o esquema e a semântica de um domínio. Elas usam lógicas descritivas (como a linguagem OWL) para estabelecer restrições rigorosas, hierarquias de classes e propriedades. O objetivo principal é permitir que máquinas de inferência (reasoners) validem a consistência dos dados e deduzam novas informações. Devido a essa complexidade lógica, ontologias têm dificuldade em escalar para bilhões de instâncias.

Os **Grafos de Conhecimento** focam nos dados instanciados. Eles organizam um grande volume de informações do mundo real em uma rede de entidades (nós) e suas relações (arestas). Enquanto a ontologia é o "molde" teórico, o KG é o repositório prático em larga escala. Atualmente, KGs costumam ser implementados sobre Grafos de Propriedades (como o Neo4j), priorizando flexibilidade, rápida travessia de dados e consultas ágeis, abrindo mão de parte do rigor lógico formal em favor do desempenho.

### Exemplo de Aplicação
Um sistema de recomendação para um catálogo de filmes.
- A ontologia define as regras gerais: "Todo `Diretor` é uma `Pessoa`", "A relação `dirigiu` só ocorre entre `Pessoa` e `Filme`".
- O Grafo de Conhecimento contém os dados reais: o nó "Steven Spielberg" ligado ao nó "Jurassic Park" pela aresta "dirigiu". O sistema usa o grafo para encontrar rapidamente filmes similares cruzando diretores, atores e gêneros.

### Mapeamento de Ontologia para Grafo de Conhecimento
Para transformar um modelo ontológico formal em um grafo de propriedades instanciado, aplica-se o seguinte mapeamento básico:

1. **Classes da ontologia** (ex: `Filme`, `Diretor`) tornam-se **Rótulos (Labels)** dos nós no grafo.
2. **Propriedades de Objeto** (relações entre entidades, ex: `dirigiu`) tornam-se **Arestas direcionadas**.
3. **Propriedades de Tipos de Dados** (atributos literais, ex: `anoLancamento`, `titulo`) tornam-se **Propriedades/Atributos internos** armazenados dentro dos nós ou arestas.

O diagrama abaixo ilustra essa transição:

```mermaid
graph TD
    subgraph Ontologia (Esquema Lógico)
        C1[Classe: Diretor]
        C2[Classe: Filme]
        C1 -- Object Property: dirigiu --> C2
        C2 -- Data Property: anoLancamento --> Literal[Inteiro]
    end

    subgraph Grafo de Conhecimento (Instâncias)
        N1([Diretor: Steven Spielberg])
        N2([Filme: Jurassic Park <br> anoLancamento: 1993])
        N1 -- dirigiu --> N2
    end
```
