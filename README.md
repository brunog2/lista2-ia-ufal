# Lista 2 - Inteligência Artificial (UFAL)

Repositório destinado ao desenvolvimento da **Lista de Exercícios 2** da disciplina **ECOM031 - Inteligência Artificial** (Engenharia de Computação / PPGI) na **Universidade Federal de Alagoas (UFAL)**.

* **Professor:** Evandro de Barros Costa
* **Dupla:** Bruno Gomes e Renato Coca
* **Período:** 2026.2

---

## Estrutura do Repositório

O projeto está organizado separando ensaios conceituais, códigos-fonte e materiais de apoio da disciplina:

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
│   ├── q01_ontologias_kg.md
│   ├── q03_eliza.md
│   ├── q04_taxonomia_agentes.md
│   ├── q05_inferencia_llm.md
│   ├── q10_buscas.md
│   ├── q11_agentes_classicos_vs_llm.md
│   ├── q13_transformers.md
│   └── q14_knowledge_graphs.md
└── src/                        # Implementações práticas e protótipos
    ├── q02_knn/                # Algoritmo KNN sobre base de 30 instâncias
    ├── q06_fuzzy/              # Sistema baseado em regras Fuzzy (Scikit-Fuzzy / Mamdani)
    ├── q07_cbr/                # Diagnóstico Médico Baseado em Casos (CBR)
    ├── q08_bayes/              # Diagnóstico Médico com Redes Bayesianas
    ├── q09_q15_ontologia/      # Recomendador e ontologia OWL 2.0 (Protégé)
    └── q12_agente_llm/         # Agente baseado em LLM com interface natural
```

---

## Módulos e Divisão de Trabalho

As 15 questões foram agrupadas em quatro módulos temáticos para otimizar o desenvolvimento e permitir a revisão cruzada entre os membros da dupla:

| Módulo | Escopo e Questões | Responsável Primário | Revisor |
| :--- | :--- | :--- | :--- |
| **Módulo A: Busca, Algoritmos e Agentes Clássicos** | **Q2** (KNN), **Q4** (Taxonomia PEAS), **Q10** (Buscas BFS/UCS/A*) | Bruno Gomes | Renato Coca |
| **Módulo B: Incerteza e Sistemas Especialistas** | **Q6** (Fuzzy Mamdani), **Q7** (CBR Médico + Vídeo), **Q8** (Redes Bayesianas) | Renato Coca | Bruno Gomes |
| **Módulo C: Ontologias e Grafos de Conhecimento** | **Q1** (Comparativo), **Q9** (Recomendador OWL), **Q14** (KG e Neo4j), **Q15** (Protégé/Reasoner) | Bruno Gomes | Renato Coca |
| **Módulo D: NLP, Transformers e Agentes LLM** | **Q3** (ELIZA/PARRY), **Q5** (Inferência LLM), **Q11** (Planejamento), **Q12** (Agente LLM), **Q13** (Transformers) | Renato Coca | Bruno Gomes |

---

## Configuração do Ambiente

### Pré-requisitos
* Python 3.10 ou superior
* [Protégé 5.x](https://protege.stanford.edu/) (com raciocinador HermiT ou Pellet integrado) para as questões de ontologia (Q9 e Q15)
* [Neo4j Desktop](https://neo4j.com/download/) ou instância Docker comunitária para as atividades de Grafos de Conhecimento (Q14)

### Instalação das dependências Python
Crie e ative um ambiente virtual antes de instalar os pacotes:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Diretrizes de Colaboração e Git Workflow

Para manter a organização do código e garantir que ambos dominem todas as partes da avaliação:

1. **Trabalho por branches:**
   * Crie uma branch específica para cada funcionalidade ou questão:
     ```bash
     git checkout -b feat/q06-fuzzy
     ```
2. **Commits semânticos:**
   * Utilize prefixos padronizados nos commits:
     * `feat:` para novas implementações ou respostas.
     * `docs:` para atualizações na documentação ou relatórios.
     * `fix:` para correções de código ou modelagem.
     * `refactor:` para melhorias sem alteração de comportamento.
3. **Pull Requests com revisão cruzada:**
   * Nenhuma alteração sobe diretamente para a branch `main`.
   * Ao concluir a tarefa na branch, abra um Pull Request.
   * O outro membro da dupla deve rodar o código localmente, revisar a resposta e aprovar o PR antes do merge.
4. **Alinhamento e Demos:**
   * Para a questão prática do CBR (Q7), realizem uma sessão síncrona para validação da base de casos e gravação da demonstração em vídeo.

---

## Status das Atividades

- [x] **Q01:** Ontologias vs Grafos de Conhecimento e Mapeamento (`docs/q01_ontologias_kg.md`)
- [x] **Q02:** Algoritmo KNN sobre as 30 instâncias da Lista 1 (`docs/q02_knn.md`, `src/q02_knn/`)
- [ ] **Q03:** Chatbot ELIZA, PARRY e evolução para AIML (`docs/q03_eliza.md`)
- [ ] **Q04:** Taxonomia de Agentes Inteligentes e Descrição PEAS (`docs/q04_taxonomia_agentes.md`)
- [ ] **Q05:** Resumo Estendido sobre Inferência em LLMs (`docs/q05_inferencia_llm.md`)
- [ ] **Q06:** Sistema Fuzzy com Metodologia de Mamdani (`src/q06_fuzzy/`)
- [ ] **Q07:** Sistema de Apoio ao Diagnóstico com CBR (`src/q07_cbr/`)
- [ ] **Q08:** Diagnóstico Médico com Redes Bayesianas (`src/q08_bayes/`)
- [ ] **Q09:** Sistema de Recomendação Baseado em Ontologias OWL 2.0 (`src/q09_q15_ontologia/`)
- [ ] **Q10:** Resolução de Problemas via Busca Não Informada e Heurística (`docs/q10_buscas.md`)
- [ ] **Q11:** Agentes Clássicos vs Agentes LLM em Planejamento (`docs/q11_agentes_classicos_vs_llm.md`)
- [ ] **Q12:** Sistema de Agente Inteligente Baseado em LLM (`src/q12_agente_llm/`)
- [ ] **Q13:** Ensaio sobre a Arquitetura Transformers (`docs/q13_transformers.md`)
- [ ] **Q14:** Representação, Inferência e Aplicação em Knowledge Graphs (`docs/q14_knowledge_graphs.md`)
- [ ] **Q15:** Aplicação de Ontologia OWL 2.0 e Raciocínio no Protégé (`src/q09_q15_ontologia/`)
