# Lista 2: Inteligência Artificial (UFAL)

Repositório da Lista de Exercícios 2 da disciplina ECOM031: Inteligência Artificial (Engenharia de Computação / PPGI) na Universidade Federal de Alagoas (UFAL).

* **Professor:** Evandro de Barros Costa
* **Dupla:** Bruno Gomes de Barros Filho (21111360) e Antônio Rodrigo Lima de Andrade Tenório (23210707)
* **Período:** 2026.2

---

## Estrutura do repositório

O projeto separa ensaios conceituais, códigos e materiais de apoio:

```text
lista2-ia-ufal/
├── README.md
├── requirements.txt            # Dependências Python do projeto
├── .gitignore                  # Arquivos ignorados pelo controle de versão
├── resources/                  # Materiais e referências da disciplina
│   ├── Aula2_IA_AM_2026_2_Turma (1).pdf
│   ├── Inteligencia_artificial_3a_ed_russell_st.pdf
│   └── Lista 2_IA_Grad_2026_2.pdf
├── docs/                       # Respostas conceituais e relatórios técnicos
│   ├── lista2_relatorio.md     # Relatório agregado (espelha o PDF LaTeX)
│   ├── q01_ontologias_kg.md
│   ├── q02_knn.md
│   ├── q03_eliza.md
│   ├── q04_taxonomia_agentes.md
│   ├── q05_inferencia_llm.md
│   ├── q10_buscas.md
│   ├── q11_agentes_classicos_vs_llm.md
│   ├── q13_transformers.md
│   └── q14_knowledge_graphs.md
├── lista2_ia_ufal.tex          # Relatório LaTeX (fonte do PDF)
├── lista2_ia_ufal.pdf          # PDF compilado com tectonic
└── src/                        # Implementações práticas e protótipos
    ├── q02_knn/                # KNN sobre a base de 30 instâncias da Lista 1
    ├── q06_fuzzy/              # Fuzzy Mamdani: tempo de irrigação no Agreste alagoano
    ├── q07_cbr/                # CBR: apoio ao diagnóstico de arboviroses e síndromes gripais
    ├── q08_bayes/              # Rede Bayesiana: triagem de dengue vs influenza
    ├── q09_q15_ontologia/      # Ontologia OWL 2 de atividades físicas + recomendador (HermiT/Pellet)
    ├── q10_buscas/             # BFS, DFS, UCS e A* no mapa de entregas
    ├── q12_agente_llm/         # Agente LLM (Gemini, ou Claude) para agenda acadêmica, com planejador explicável
    ├── q13_transformers/       # Mini-Transformer em numpy para o ensaio da Q13
    └── q14_knowledge_graph/    # KG de arboviroses: inferência RDFS/OWL RL, TransE e Neo4j

Cada pasta em `src/` tem um `README.md` com o relatório técnico da questão,
o notebook de exploração já executado, os módulos Python e os testes.
```

---

## Módulos e divisão de trabalho

As 15 questões foram agrupadas em quatro módulos temáticos para dividir o desenvolvimento e permitir revisão cruzada na dupla:

| Módulo | Escopo e questões | Responsável primário | Revisor |
| :--- | :--- | :--- | :--- |
| Módulo A: Busca, algoritmos e agentes clássicos | Q2 (KNN), Q4 (Taxonomia PEAS), Q10 (Buscas BFS/UCS/A*) | Bruno Gomes | Antônio Rodrigo |
| Módulo B: Incerteza e sistemas especialistas | Q6 (Fuzzy Mamdani), Q7 (CBR Médico + Vídeo), Q8 (Redes Bayesianas) | Antônio Rodrigo | Bruno Gomes |
| Módulo C: Ontologias e grafos de conhecimento | Q1 (Comparativo), Q9 (Recomendador OWL), Q14 (KG e Neo4j), Q15 (Protégé/Reasoner) | Bruno Gomes | Antônio Rodrigo |
| Módulo D: NLP, Transformers e agentes LLM | Q3 (ELIZA/PARRY), Q5 (Inferência LLM), Q11 (Planejamento), Q12 (Agente LLM), Q13 (Transformers) | Antônio Rodrigo | Bruno Gomes |

---

## Configuração do ambiente

### Pré-requisitos
* Python 3.10 ou superior
* [Protégé 5.x](https://protege.stanford.edu/) (com raciocinador HermiT ou Pellet) para as questões de ontologia (Q9 e Q15)
* [Neo4j Desktop](https://neo4j.com/download/) ou instância Docker comunitária para as atividades de Grafos de Conhecimento (Q14)

### Instalação das dependências Python
Crie e ative um ambiente virtual antes de instalar os pacotes:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Testes

```bash
python -m pytest src -q
```

### Requisitos extras por questão
* Q09 e Q15: Java 11+ para o HermiT e o Pellet embutidos no `owlready2`.
* Q12: chave gratuita do Google AI Studio em um arquivo `.env` na raiz (`GEMINI_API_KEY=...`, o arquivo é ignorado pelo git) para o chat real com o Gemini; sem ela, `python agente_cli.py --demo` roda a demonstração simulada.
* Q14 (opcional): Docker para validar o grafo no Neo4j (`bash src/q14_knowledge_graph/neo4j/validar_neo4j.sh`).

---

## Diretrizes de colaboração e Git

Para manter o código organizado e garantir que ambos acompanhem as partes da avaliação:

1. **Trabalho por branches.**
   Crie uma branch específica para cada funcionalidade ou questão:
     ```bash
     git checkout -b feat/q06-fuzzy
     ```
2. **Commits semânticos.**
   Use prefixos padronizados:
     * `feat:` para novas implementações ou respostas.
     * `docs:` para documentação ou relatórios.
     * `fix:` para correções de código ou modelagem.
     * `refactor:` para melhorias sem mudança de comportamento.
3. **Pull Requests com revisão cruzada.**
   Nenhuma alteração sobe direto para `main`. Ao concluir a tarefa na branch, abra um Pull Request. O outro membro da dupla deve rodar o código, revisar a resposta e aprovar o PR antes do merge.
4. **Alinhamento e demos.**
   Para a questão prática do CBR (Q7), façam uma sessão síncrona para validar a base de casos e gravar a demonstração em vídeo.

---

## Progresso

**15 / 15** questões concluídas (**100%**)

```text
[████████████████████] 100%
```

| Situação | Quantidade | Questões |
| :--- | :---: | :--- |
| Concluídas | 15 | Q01, Q02, Q03, Q04, Q05, Q06, Q07, Q08, Q09, Q10, Q11, Q12, Q13, Q14, Q15 |
| Pendentes | 0 | |

Atualizar este bloco sempre que marcar ou desmarcar uma questão no checklist abaixo.

---

## Status das atividades

- [x] Q01: Ontologias vs Grafos de Conhecimento e Mapeamento (`docs/q01_ontologias_kg.md`)
- [x] Q02: Algoritmo KNN sobre as 30 instâncias da Lista 1 (`docs/q02_knn.md`, `src/q02_knn/`)
- [x] Q03: Chatbot ELIZA, PARRY e evolução para AIML (`docs/q03_eliza.md`)
- [x] Q04: Taxonomia de Agentes Inteligentes e Descrição PEAS (`docs/q04_taxonomia_agentes.md`)
- [x] Q05: Resumo Estendido sobre Inferência em LLMs (`docs/q05_inferencia_llm.md`)
- [x] Q06: Sistema Fuzzy com Metodologia de Mamdani (`src/q06_fuzzy/`)
- [x] Q07: Sistema de Apoio ao Diagnóstico com CBR (`src/q07_cbr/`)
- [x] Q08: Diagnóstico Médico com Redes Bayesianas (`src/q08_bayes/`)
- [x] Q09: Sistema de Recomendação Baseado em Ontologias OWL 2.0 (`src/q09_q15_ontologia/`)
- [x] Q10: Resolução de Problemas via Busca Não Informada e Heurística (`docs/q10_buscas.md`, `src/q10_buscas/`)
- [x] Q11: Agentes Clássicos vs Agentes LLM em Planejamento (`docs/q11_agentes_classicos_vs_llm.md`)
- [x] Q12: Sistema de Agente Inteligente Baseado em LLM (`src/q12_agente_llm/`)
- [x] Q13: Ensaio sobre a Arquitetura Transformers (`docs/q13_transformers.md`, `src/q13_transformers/`)
- [x] Q14: Representação, Inferência e Aplicação em Knowledge Graphs (`docs/q14_knowledge_graphs.md`, `src/q14_knowledge_graph/`)
- [x] Q15: Aplicação de Ontologia OWL 2.0 e Raciocínio no Protégé (`src/q09_q15_ontologia/`)
