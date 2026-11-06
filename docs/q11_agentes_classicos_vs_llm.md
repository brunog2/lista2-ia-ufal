# Lista 2 - Inteligência Artificial

**Dupla:** Bruno Gomes de Barros Filho (21111360); Antonio Rodrigo Lima de Andrade Tenório (23210707)  
**Disciplina:** ECOM031: Inteligência Artificial  
**Professor:** Evandro de Barros Costa  
**Período:** 2026.2

## Questão 11: Agentes clássicos (AIMA Cap. 2) versus agentes baseados em LLM

Esta questão apresenta uma comparação entre os agentes inteligentes descritos por Russell e Norvig no Capítulo 2 do livro *Artificial Intelligence: A Modern Approach* (AIMA, 3ª edição) e os agentes construídos com base em grandes modelos de linguagem (LLMs).

Para fazer essa comparação, consideramos um problema de organização de atividades acadêmicas. Nele, um agente precisa interpretar as solicitações de um professor, considerar os prazos e as prioridades de cada tarefa e montar uma programação que respeite os horários disponíveis. A partir desse exemplo, analisamos como cada abordagem lida com o planejamento e quais são suas limitações.

### 1. Concepção clássica de agente inteligente (AIMA, Capítulo 2)

No Capítulo 2, Russell e Norvig definem um **agente** como uma entidade capaz de perceber o ambiente por meio de sensores e executar ações sobre ele por meio de atuadores. O comportamento do agente é representado pela **função do agente**, que relaciona as sequências de percepções recebidas às ações que devem ser executadas. Já o **programa do agente** corresponde à implementação dessa função em um sistema computacional.

Um **agente racional** é aquele que escolhe as ações que, considerando as informações disponíveis, têm maior expectativa de contribuir para sua medida de desempenho. Isso não significa que ele conheça todas as informações do ambiente ou que sempre consiga encontrar a melhor solução possível. Sua decisão depende das percepções recebidas, do conhecimento que possui e das alternativas disponíveis naquele momento.

Para organizar o projeto de um agente, os autores apresentam o modelo **PEAS**, que permite descrever o ambiente de tarefa a partir de quatro elementos:

| Elemento | Significado |
| :--- | :--- |
| **P** (*Performance*) | Medida de desempenho: critérios utilizados para avaliar o sucesso do agente |
| **E** (*Environment*) | Ambiente no qual o agente atua |
| **A** (*Actuators*) | Atuadores: mecanismos utilizados para executar ações no ambiente |
| **S** (*Sensors*) | Sensores: meios pelos quais o agente recebe informações do ambiente |

Além desses elementos, as características do ambiente influenciam diretamente o tipo de agente mais adequado. Entre elas estão a observabilidade, o determinismo, a organização episódica ou sequencial, o comportamento estático ou dinâmico, a natureza discreta ou contínua e a presença de um ou mais agentes.

O capítulo também apresenta diferentes arquiteturas de agentes, organizadas de acordo com a complexidade de suas decisões:

1. **Agente reativo simples:** escolhe uma ação com base apenas na percepção atual, utilizando regras condicionais.
2. **Agente reativo baseado em modelo:** mantém uma representação interna do ambiente para considerar informações que não estão disponíveis na percepção atual.
3. **Agente baseado em objetivos:** considera estados desejados e escolhe ações que possam conduzi-lo até eles.
4. **Agente baseado em utilidade:** avalia diferentes resultados por meio de uma função de utilidade, permitindo comparar alternativas quando existem objetivos conflitantes.
5. **Agente com aprendizado:** utiliza a experiência para melhorar seu desempenho ao longo do tempo.

No problema de organização acadêmica apresentado nesta questão, a abordagem mais adequada é a de um **agente baseado em objetivos**, pois ele precisa concluir determinadas atividades e respeitar compromissos. A utilização de uma função de **utilidade** complementa essa estrutura, permitindo priorizar tarefas e escolher entre diferentes planos possíveis quando não há tempo suficiente para realizar tudo.

### 2. Agentes baseados em LLM

Um agente baseado em LLM também recebe informações do ambiente e executa ações, mas utiliza um modelo de linguagem como parte central do processo de interpretação e tomada de decisão.

Em uma aplicação típica, o funcionamento pode ser dividido em algumas etapas:

1. Receber uma solicitação escrita em linguagem natural.
2. Identificar os objetivos, as restrições e as preferências presentes na mensagem.
3. Elaborar um plano de execução ou selecionar ferramentas que possam ajudar a realizar a tarefa.
4. Executar as ações necessárias por meio de ferramentas, como calendário, e-mail, banco de dados ou APIs.
5. Apresentar o resultado ao usuário em linguagem natural.

Apesar de ambos seguirem a lógica de perceber o ambiente e agir sobre ele, existem diferenças importantes entre a abordagem clássica e a baseada em LLM:

| Dimensão | Agente clássico (AIMA Cap. 2) | Agente baseado em LLM |
| :--- | :--- | :--- |
| Representação | Estados, ações e objetivos definidos explicitamente | Conhecimento representado principalmente nos parâmetros do modelo e no contexto recebido |
| Interpretação da entrada | Geralmente trabalha com informações estruturadas ou previamente formalizadas | Interpreta solicitações em linguagem natural, inclusive quando são ambíguas ou incompletas |
| Racionalidade | Pode ser analisada em relação a uma medida de desempenho definida | Não possui garantia formal de que a resposta maximize uma função de utilidade |
| Tratamento de restrições | Pode utilizar regras, busca ou problemas de satisfação de restrições (CSP) | Pode interpretar restrições em texto, mas precisa de mecanismos de verificação para garantir seu cumprimento |
| Interação com ferramentas | Definida diretamente na implementação do agente | Frequentemente realizada por meio de *function calling* ou *tool use* |
| Explicação | Pode apresentar o caminho percorrido, as regras aplicadas e as decisões tomadas | Consegue produzir explicações em linguagem natural, mas elas precisam corresponder ao processo realmente executado |
| Adaptação | Mudanças no domínio podem exigir alterações na modelagem ou no programa | Consegue lidar com novas solicitações e contextos sem necessariamente modificar o modelo |

Uma das principais vantagens dos LLMs está na flexibilidade para interpretar solicitações e lidar com diferentes formas de comunicação. Entretanto, essa flexibilidade não significa que todas as decisões estejam corretas. Sem mecanismos adicionais, o modelo pode propor horários incompatíveis, ignorar uma restrição importante ou apresentar como viável um plano que não cabe no tempo disponível.

### 3. Problema de aplicação: assistente de organização acadêmica

Para comparar as duas abordagens, utilizamos um cenário em que um professor precisa organizar suas atividades entre **14h e 18h**, totalizando quatro horas disponíveis.

A solicitação envolve preparar uma aula de Inteligência Artificial, corrigir trabalhos e participar de uma reunião de pesquisa. As atividades possuem durações, prioridades e prazos diferentes, conforme apresentado na tabela:

| Atividade | Duração | Prioridade | Prazo |
| :--- | ---: | :--- | :--- |
| A — Preparar aula de IA | 90 min | Alta | Hoje |
| B — Corrigir trabalhos | 120 min | Média | Amanhã |
| C — Reunião de pesquisa | 60 min | Alta | Hoje, às 16h |
| D — Revisar artigo | 60 min | Baixa | Próxima semana |

Além das informações da tabela, o agente precisa considerar as seguintes condições:

- A reunião **C** deve acontecer obrigatoriamente das **16h às 17h**.
- Nenhuma atividade pode ocupar o mesmo intervalo de outra.
- Uma atividade iniciada deve ser concluída, exceto quando o plano indicar explicitamente que ela será dividida.
- As atividades mais urgentes devem receber prioridade, sem comprometer os compromissos fixos.
- Quando uma tarefa não puder ser realizada, o agente deve apresentar uma justificativa.
- O objetivo é respeitar as restrições e aproveitar o tempo disponível da melhor maneira possível.

#### 3.1. Descrição PEAS do ambiente de tarefa

Aplicando o modelo PEAS ao cenário, temos:

| Elemento | Descrição neste problema |
| :--- | :--- |
| **Desempenho (P)** | Cumprir os compromissos fixos, concluir tarefas urgentes dentro do prazo, aproveitar o tempo disponível e justificar atividades adiadas |
| **Ambiente (E)** | Agenda do professor, tarefas com duração, prioridade e prazo, além da janela disponível entre 14h e 18h |
| **Atuadores (A)** | Criar ou alterar eventos na agenda, apresentar o planejamento e registrar atividades adiadas e suas justificativas |
| **Sensores (S)** | Solicitação do professor, informações das tarefas, calendário atual e horário corrente |

Também é possível classificar as propriedades desse ambiente com base no vocabulário do AIMA:

- **Observável:** pode ser considerado totalmente observável se o agente tiver acesso à agenda e a todas as informações das tarefas.
- **Determinístico:** as durações e o horário da reunião são conhecidos, de modo que o resultado do planejamento pode ser previsto, desconsiderando imprevistos externos.
- **Sequencial:** a ordem das atividades influencia o resultado, pois uma decisão pode limitar as opções disponíveis posteriormente.
- **Estático:** durante a elaboração do plano, o ambiente pode ser considerado estático. Entretanto, novas solicitações ou alterações na agenda podem torná-lo dinâmico.
- **Discreto:** as atividades e os intervalos de tempo são tratados como unidades definidas.
- **Monoagente:** o planejamento é realizado por um único agente, embora outras pessoas e sistemas possam interagir com ele posteriormente.

### 4. Solução clássica: planejamento explícito com objetivos e utilidade

Na abordagem clássica, a solicitação do professor precisa ser transformada em uma representação estruturada do problema. Diferentemente de um LLM, o agente não interpreta diretamente uma frase em linguagem natural. As tarefas, os horários e as restrições devem ser previamente organizados para que o algoritmo consiga trabalhar com essas informações.

#### 4.1. Modelo do problema

O planejamento pode ser representado pelos seguintes elementos:

- **Estado:** cada atividade recebe um intervalo de início e fim dentro da janela de 14h às 18h ou é marcada como adiada. Também deve existir uma indicação de quais atividades podem ser divididas.
- **Ações:** alocar uma atividade em um intervalo livre, adiar uma tarefa com justificativa ou dividir uma atividade quando isso estiver explicitamente autorizado.
- **Restrições obrigatórias:** a reunião C deve permanecer entre 16h e 17h; não pode haver sobreposição; as durações precisam ser respeitadas; e uma divisão só pode ocorrer quando estiver prevista no plano.
- **Preferências:** priorizar atividades urgentes, cumprir os prazos e aproveitar o tempo restante para realizar as demais tarefas.

Para representar a preferência entre diferentes resultados, podemos utilizar uma função de utilidade simplificada:

\[
U = 5\cdot\mathbb{I}(A) + 3\cdot f(B) + 5\cdot\mathbb{I}(C) + 1\cdot\mathbb{I}(D) - 10\cdot\mathbb{I}(\text{violação de C}) - 4\cdot\mathbb{I}(A\text{ fora de hoje})
\]

Nessa expressão, \(\mathbb{I}\) representa uma função indicadora, que assume valor 1 quando a condição é verdadeira e 0 caso contrário. A função \(f(B)\) representa a fração da atividade B concluída, variando entre 0 e 1 quando sua divisão estiver autorizada. Caso contrário, B só pode ser considerada concluída ou não concluída.

Os pesos atribuídos às atividades representam suas prioridades no exemplo. A preparação da aula e a reunião recebem valores maiores por terem prioridade alta e prazo para o mesmo dia. A correção dos trabalhos possui peso intermediário, enquanto a revisão do artigo recebe um valor menor por ter prazo mais distante.

Assim, o agente combina dois critérios: alcançar os objetivos definidos e escolher, entre os planos possíveis, aquele que oferece maior utilidade.

#### 4.2. Análise da janela de tempo

Antes de elaborar o plano, é necessário verificar quanto tempo realmente está disponível.

Como a reunião C ocupa obrigatoriamente o intervalo das 16h às 17h, a janela de quatro horas fica dividida em dois períodos livres:

- **14:00–16:00:** 120 minutos disponíveis.
- **17:00–18:00:** 60 minutos disponíveis.

Isso representa 180 minutos para as atividades que podem ser organizadas livremente. Entretanto, as tarefas A, B e D somam 270 minutos:

\[
90 + 120 + 60 = 270 \text{ minutos}
\]

Portanto, não é possível concluir todas as atividades flexíveis no mesmo dia. O agente precisa decidir quais tarefas serão realizadas, quais poderão ser parcialmente executadas e quais deverão ser adiadas.

#### 4.3. Plano proposto pelo agente clássico

Para este exemplo, consideramos que a divisão da atividade B está autorizada, desde que seja indicada explicitamente no planejamento. Dessa forma, é possível antecipar parte da correção dos trabalhos sem comprometer a preparação da aula ou a reunião.

| Horário | Atividade | Observação |
| :--- | :--- | :--- |
| 14:00–15:30 | A — Preparar aula de IA | Alta prioridade; prazo hoje; atividade concluída em 90 minutos |
| 15:30–16:00 | Reserva / folga operacional | Intervalo de 30 minutos, insuficiente para concluir B ou D |
| 16:00–17:00 | C — Reunião de pesquisa | Compromisso fixo |
| 17:00–18:00 | B — Corrigir trabalhos (parte 1/2) | Divisão explícita: 60 dos 120 minutos necessários |
| Amanhã (a definir) | B — Corrigir trabalhos (parte 2/2) | 60 minutos restantes, dentro do prazo |
| Adiada | D — Revisar artigo | Prioridade baixa; prazo na próxima semana |

A preparação da aula é realizada integralmente antes da reunião, garantindo o cumprimento de uma atividade de alta prioridade. A reunião permanece no horário estabelecido e, após seu término, uma hora é destinada à correção dos trabalhos.

A atividade B não é concluída no mesmo dia, mas sua divisão permite adiantar metade do trabalho e finalizar o restante no dia seguinte. Já a revisão do artigo é adiada porque possui menor prioridade e um prazo mais distante.

Caso a divisão de tarefas não fosse permitida, o planejamento precisaria ser diferente. Nesse cenário, seria possível realizar A das 14h às 15h30 e manter C das 16h às 17h, mas não haveria um intervalo contínuo de 120 minutos para concluir B. Assim, a correção dos trabalhos seria adiada integralmente para o dia seguinte, com justificativa baseada na disponibilidade de tempo.

A solução pode ser obtida por diferentes técnicas, como busca com verificação de restrições, programação por restrições (CSP/CP) ou algoritmos de escalonamento. Essas abordagens permitem avaliar as combinações possíveis e descartar aquelas que violam as condições definidas para o problema.

### 5. Solução com agente baseado em LLM

Na abordagem baseada em LLM, o processo começa com a solicitação do professor em linguagem natural. O modelo precisa identificar as atividades mencionadas, extrair suas durações, prioridades e prazos e reconhecer que a reunião das 16h é um compromisso fixo.

A partir dessas informações, o agente pode elaborar um plano e, caso tenha acesso a ferramentas externas, consultar ou modificar a agenda. Algumas chamadas possíveis seriam:

- `listar_eventos(data=hoje)`
- `criar_evento(titulo, inicio, fim)`
- `consultar_carga_trabalhos()`

O resultado esperado seria um planejamento semelhante ao apresentado na abordagem clássica: reservar o horário da reunião, realizar a preparação da aula antes dela e organizar a correção dos trabalhos de acordo com o tempo restante.

A principal diferença está na forma como o modelo recebe e interpreta as informações. Em vez de depender exclusivamente de uma estrutura previamente preenchida, o LLM consegue compreender solicitações escritas de maneira informal, identificar informações relevantes e interagir com o usuário para resolver dúvidas.

Entre as vantagens dessa abordagem, podemos destacar:

- Interpretar solicitações incompletas ou pouco estruturadas, como "organize minhas atividades da melhor maneira possível".
- Identificar informações ausentes e pedir esclarecimentos, por exemplo, perguntando se a correção dos trabalhos pode ser dividida.
- Apresentar o planejamento em linguagem natural, explicando as escolhas realizadas.
- Adaptar o plano quando o professor acrescentar novas atividades ou alterar alguma condição.

Entretanto, essas capacidades não eliminam os riscos. O modelo pode interpretar incorretamente uma duração, esquecer um compromisso fixo ou sugerir atividades em horários que já estão ocupados. Também pode dividir uma tarefa sem autorização ou apresentar uma justificativa convincente para uma programação que, na prática, não é viável.

Por isso, uma solução mais confiável combina o LLM com mecanismos tradicionais de planejamento. O modelo pode interpretar a solicitação e propor alternativas, enquanto um verificador de restrições confere os horários, as durações e as possíveis sobreposições antes de qualquer alteração na agenda. Um algoritmo de otimização também pode avaliar os planos gerados e selecionar aquele que melhor atende aos critérios definidos.

### 6. Comparação lado a lado no mesmo problema

A aplicação das duas abordagens ao mesmo cenário permite observar diferenças na maneira como as decisões são tomadas:

| Aspecto | Abordagem clássica | Abordagem LLM |
| :--- | :--- | :--- |
| Entrada | Informações estruturadas, como tabelas de tarefas e restrições | Texto livre, que pode ser convertido em estruturas por meio da interpretação do modelo |
| Interpretação dos objetivos | Definida durante a modelagem do problema | Realizada pelo modelo a partir de cada solicitação |
| Respeito à reunião das 16h | Pode ser garantido quando a restrição é aplicada pelo algoritmo | Pode ser interpretado corretamente, mas precisa de verificação para oferecer garantia |
| Maximização da utilidade | Utiliza uma função de utilidade explícita | Depende da avaliação gerada pelo modelo, sem garantia formal de otimização |
| Justificativas | Podem ser relacionadas diretamente às restrições e aos critérios de utilidade | São apresentadas em linguagem natural, mas precisam corresponder às decisões efetivamente tomadas |
| Interação com ferramentas | Implementada diretamente no programa do agente | Pode ocorrer por meio de *tool use* e chamadas de funções |
| Mudança de política | Exige atualizar as regras ou restrições do modelo | Pode ser informada em linguagem natural, mas o plano precisa ser reavaliado |

No exemplo, a abordagem clássica oferece maior controle sobre as restrições, pois elas fazem parte da própria representação do problema. Já o LLM facilita a interação com o professor e a adaptação a novas solicitações, mas precisa de mecanismos adicionais para garantir que o planejamento seja válido.

### 7. Quando o LLM oferece vantagens e o que ainda depende de mecanismos explícitos

#### 7.1. Situações em que o agente LLM tende a ser vantajoso

1. **Interpretação de solicitações em linguagem natural:** o professor pode descrever suas atividades em texto corrido, sem precisar preencher previamente uma estrutura rígida. O modelo consegue extrair as informações necessárias e organizá-las para o planejamento.

2. **Diálogo e negociação:** quando existe alguma informação ausente ou uma decisão que depende da preferência do usuário, o agente pode fazer perguntas e apresentar alternativas. No exemplo, poderia perguntar se a correção dos trabalhos pode ser dividida em dois períodos.

3. **Integração com diferentes ferramentas:** o modelo pode interagir com calendário, e-mail, ambiente virtual de aprendizagem e outros sistemas, reunindo informações que seriam consultadas separadamente.

4. **Adaptação a mudanças:** novas solicitações podem ser incorporadas durante a conversa. Se o professor informar que precisa conversar com a coordenação por 15 minutos após a reunião, o agente pode considerar essa alteração e propor um novo planejamento.

5. **Comunicação dos resultados:** além de elaborar o plano, o LLM consegue explicar as decisões, resumir as atividades realizadas e produzir mensagens ou relatórios para o usuário.

#### 7.2. Capacidades que ainda dependem de raciocínio, planejamento e verificação explícitos

1. **Cumprimento de restrições obrigatórias:** horários fixos, durações e ausência de sobreposição precisam ser verificados por mecanismos confiáveis. Não basta que o modelo reconheça essas condições no texto.

2. **Otimização da utilidade:** quando o objetivo é maximizar uma função de utilidade definida, é necessário utilizar critérios explícitos para comparar os planos e identificar qual apresenta o melhor resultado.

3. **Consistência e reprodutibilidade:** em sistemas institucionais, é importante que as mesmas informações e restrições produzam resultados consistentes, que possam ser analisados posteriormente.

4. **Segurança na execução de ferramentas:** antes de criar ou alterar eventos, o sistema precisa verificar se a operação é válida e se não existem conflitos com a agenda real.

5. **Planejamento de problemas maiores:** quando há muitas atividades, restrições e combinações possíveis, algoritmos de busca e técnicas como CSP oferecem mecanismos mais adequados para explorar e validar as alternativas.

6. **Justificativa das decisões:** as explicações precisam estar relacionadas a critérios verificáveis. No exemplo, dizer que B foi parcialmente realizada porque não havia um intervalo contínuo de 120 minutos disponível é uma justificativa mais consistente do que simplesmente afirmar que a tarefa foi menos importante.

A comparação mostra que os agentes clássicos e os agentes baseados em LLM apresentam características diferentes. O Capítulo 2 do AIMA fornece os fundamentos para estruturar um agente racional, definindo como ele percebe o ambiente, escolhe ações e avalia seu desempenho. Já os LLMs ampliam as possibilidades de interação, principalmente pela capacidade de interpretar linguagem natural e lidar com solicitações variadas.

No problema apresentado, o LLM facilita a comunicação com o professor e a elaboração inicial do planejamento. Entretanto, garantir que a reunião ocorra no horário correto, que as atividades não se sobreponham e que as durações sejam respeitadas exige mecanismos de verificação mais precisos.

Por isso, a combinação das duas abordagens apresenta uma solução mais adequada: o LLM pode interpretar as solicitações, interagir com o usuário e sugerir planos, enquanto algoritmos de planejamento e verificadores de restrições ficam responsáveis por avaliar a viabilidade das decisões antes de executá-las.

### Referências

1. RUSSELL, Stuart J.; NORVIG, Peter. *Inteligência Artificial: uma abordagem moderna*. 3. ed. Rio de Janeiro: Elsevier / Campus, 2013. Cap. 2 (Agentes inteligentes).
2. RUSSELL, Stuart J.; NORVIG, Peter. *Inteligência Artificial: uma abordagem moderna*. 3. ed. Rio de Janeiro: Elsevier / Campus, 2013. Cap. 3 (Resolução de problemas por meio de busca).