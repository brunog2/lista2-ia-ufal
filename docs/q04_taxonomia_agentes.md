# Lista 2 - Inteligência Artificial

**Dupla:** Bruno Gomes de Barros Filho (21111360); Antônio Rodrigo Lima de Andrade Tenório (23210707)  
**Disciplina:** ECOM031: Inteligência Artificial  
**Professor:** Evandro de Barros Costa  
**Período:** 2026.2

## Questão 4: Taxonomia de agentes, descrição PEAS e propriedades dos ambientes de tarefa

Esta questão usa a taxonomia do Capítulo 2 de Russell e Norvig (*Inteligência Artificial*, 3ª ed.): agente reativo simples, agente reativo baseado em modelo, agente baseado em objetivos, agente baseado em utilidade e agente com aprendizagem (o "agente adaptativo" da aula). Para cada categoria explicamos a estrutura do agente, mostramos o programa do agente em pseudocódigo e apresentamos duas aplicações. Cada aplicação tem a descrição PEAS do ambiente de tarefa e a caracterização do ambiente nas sete dimensões do livro.

### 0. Ferramentas da análise

No livro, um agente é qualquer coisa que percebe o ambiente por sensores e age sobre ele por atuadores, e agente = arquitetura + programa. O ambiente de tarefa é especificado pela descrição **PEAS**:

| Elemento | Pergunta que responde |
| :--- | :--- |
| P (*Performance*): medida de desempenho | Como julgamos se o agente se saiu bem? |
| E (*Environment*): ambiente | Em que mundo o agente opera e com o que ele interage? |
| A (*Actuators*): atuadores | Que ações ele pode executar? |
| S (*Sensors*): sensores | O que ele consegue perceber? |

As propriedades do ambiente de tarefa (Seção 2.3.2) são classificadas em sete dimensões:

| Dimensão | Pergunta |
| :--- | :--- |
| Completamente ou parcialmente observável | Os sensores dão acesso, a cada instante, a tudo o que é relevante para escolher a ação? |
| Agente único ou multiagente | Há outras entidades cujo comportamento é melhor descrito como a maximização de uma medida de desempenho que depende das ações do nosso agente? |
| Determinístico ou estocástico | O próximo estado é completamente determinado pelo estado atual e pela ação? |
| Episódico ou sequencial | A decisão atual afeta as decisões futuras? |
| Estático ou dinâmico | O ambiente pode mudar enquanto o agente delibera? (Semidinâmico: o ambiente não muda, mas o desempenho muda com o tempo.) |
| Discreto ou contínuo | Estados, tempo, percepções e ações assumem valores discretos ou contínuos? |
| Conhecido ou desconhecido | O agente (ou o projetista) conhece os resultados das ações, ou as probabilidades deles? |

O próprio livro avisa que muitas respostas dependem de como a tarefa é definida e que algumas não são definitivas. Por isso cada classificação abaixo vem com a justificativa para aquela aplicação específica.

### 1. Agente reativo simples

O agente reativo simples escolhe a ação olhando só para a percepção atual, por meio de regras condição-ação ("se carro-da-frente-está-freando então começar-a-frear"). Ele não guarda nada sobre o passado e não tem modelo de como o mundo evolui. O programa do agente da Figura 2.10 do livro é:

```text
função AGENTE-REATIVO-SIMPLES(percepção) retorna uma ação
  persistente: regras, um conjunto de regras condição-ação
  estado ← INTERPRETAR-ENTRADA(percepção)
  regra  ← REGRA-CORRESPONDENTE(estado, regras)
  ação   ← AÇÃO-DA-REGRA[regra]
  retornar ação
```

O livro mostra que esse agente só funciona bem se a decisão correta puder ser tomada a partir da percepção atual, isto é, se o ambiente for completamente observável no que importa para a decisão. Com observação parcial ele pode entrar em laços infinitos, como o aspirador sem sensor de posição que não sabe para que lado ir quando percebe [Limpo]. As duas aplicações abaixo foram escolhidas porque a percepção de cada instante já carrega a informação necessária.

#### 1.1 Porta automática de pedestres

O controlador de uma porta deslizante de shopping abre quando detecta alguém na área de aproximação e fecha quando a área fica vazia. As regras são duas: "se há presença na zona de detecção ou na soleira, abrir" e "senão, fechar".

```text
função AGENTE-PORTA([presença_zona, presença_soleira]) retorna uma ação
  se presença_zona ou presença_soleira então retornar Abrir
  senão retornar Fechar
```

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Abrir a tempo de a pessoa passar sem diminuir o passo; nunca fechar sobre alguém; manter a porta aberta o mínimo possível (perda de ar-condicionado, entrada de poeira); evitar aberturas para quem só passa ao lado |
| Ambiente | Entrada do prédio, pedestres, carrinhos de compras, cadeiras de rodas, objetos deixados na passagem, vento e chuva |
| Atuadores | Motor das folhas deslizantes (abrir, fechar), trava eletromecânica |
| Sensores | Sensor de movimento por micro-ondas acima da porta (zona de aproximação), barreira infravermelha na soleira |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | O sensor detecta movimento na zona, não a intenção: quem passa rente à porta sem querer entrar dispara a abertura. Para a regra adotada ("há alguém na zona?"), porém, a percepção atual basta |
| Agentes | Agente único | Os pedestres não tentam maximizar nada que dependa das ações da porta; entram como parte do ambiente |
| Determinismo | Estocástico | A chegada de pessoas não é determinada pelo estado atual nem pela ação da porta |
| Episódico/sequencial | Episódico | Cada decisão depende só da leitura atual dos sensores, e abrir ou fechar agora não muda quem vai aparecer depois |
| Estático/dinâmico | Dinâmico | As pessoas continuam andando enquanto o controlador decide, embora a decisão leve milissegundos |
| Discreto/contínuo | Contínuo no mundo, discreto na interface | Posições e velocidades dos pedestres são contínuas, mas o agente só recebe presença sim/não e só escolhe entre abrir e fechar |
| Conhecido/desconhecido | Conhecido | O efeito de acionar o motor é especificado pelo fabricante |

#### 1.2 Triagem de pacotes por código de barras numa esteira

Num centro de distribuição, cada pacote passa por um leitor de código de barras logo antes de um conjunto de desviadores. A regra é uma tabela: "se o CEP lido está na faixa da região k, acionar o desviador da rampa k; se a leitura falhou, mandar para a rampa de rejeito, onde uma pessoa trata o pacote". Na versão mais simples, o leitor fica imediatamente antes do desviador e a percepção atual basta para agir.

```text
função AGENTE-TRIAGEM([código_lido]) retorna uma ação
  se código_lido = falha então retornar Desviar(rampa_rejeito)
  retornar Desviar(TABELA-CEP[REGIÃO(código_lido)])
```

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Porcentagem de pacotes na rampa correta, pacotes processados por hora, fração de pacotes mandados ao rejeito |
| Ambiente | Esteira, pacotes de tamanhos e formatos variados, etiquetas (algumas amassadas ou molhadas), rampas de destino |
| Atuadores | Desviadores pneumáticos ou sapatas deslizantes de cada rampa |
| Sensores | Leitor de código de barras ou câmera, sensor fotoelétrico que detecta a passagem do pacote, encoder da esteira |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Completamente observável (com etiqueta legível) | O destino do pacote está inteiro no código lido. Quando a etiqueta está danificada a informação falta, e a regra de rejeito cobre esse caso |
| Agentes | Agente único | Não há outro agente cujo desempenho dependa das escolhas do desviador |
| Determinismo | Determinístico (em operação normal) | Acionar o desviador manda o pacote para a rampa. Falhas raras, como um pacote que escorrega, introduzem alguma estocasticidade |
| Episódico/sequencial | Episódico | Cada pacote é um episódio. A decisão sobre um pacote não afeta o destino nem a leitura do próximo, como no robô de seleção de peças do livro |
| Estático/dinâmico | Dinâmico | A esteira continua andando: se o agente demorar, o pacote passa do desviador e a ação vira "não fazer nada" |
| Discreto/contínuo | Discreto | Percepções (códigos) e ações (qual rampa) são discretas. O tempo é contínuo, mas o agente só age nos eventos de passagem |
| Conhecido/desconhecido | Conhecido | A tabela de CEPs e o efeito dos desviadores são dados de projeto |

### 2. Agente reativo baseado em modelo

Quando o ambiente é parcialmente observável, o agente precisa lembrar o que não está vendo agora. O agente baseado em modelo mantém um **estado interno** e o atualiza com dois tipos de conhecimento: como o mundo evolui independentemente do agente e como as ações do agente afetam o mundo. Esse conhecimento é o **modelo do mundo**. A escolha da ação continua sendo feita por regras condição-ação, só que aplicadas ao estado estimado e não à percepção crua. Programa do agente (Figura 2.12):

```text
função AGENTE-REATIVO-BASEADO-EM-MODELOS(percepção) retorna uma ação
  persistente: estado, a concepção do agente do estado atual do mundo
               modelo, como o próximo estado depende do estado atual e da ação
               regras, um conjunto de regras condição-ação
               ação, a ação mais recente, inicialmente nenhuma
  estado ← ATUALIZAR-ESTADO(estado, ação, percepção, modelo)
  regra  ← REGRA-CORRESPONDENTE(estado, regras)
  ação   ← AÇÃO-DA-REGRA[regra]
  retornar ação
```

O estado é o "melhor palpite" do agente. Ele pode estar errado, mas é o que permite agir de forma sensata quando a percepção do momento não basta.

#### 2.1 Robô aspirador que constrói um mapa da casa

Diferente do aspirador de dois quadrados do livro, um robô aspirador doméstico atual mapeia o apartamento enquanto limpa. O estado interno guarda um mapa de ocupação (paredes, móveis), a posição estimada do robô, as regiões já limpas e o nível de bateria. As regras são aplicadas sobre esse estado: "se bateria < 15%, voltar para a base", "se a região atual já foi limpa, seguir para a fronteira não limpa mais próxima", "se o sensor de sujeira acusa muita sujeira, passar de novo no mesmo lugar".

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Fração da área livre que foi limpa, tempo total, energia gasta, número de colisões, nunca cair de escadas, terminar na base |
| Ambiente | Apartamento com cômodos, móveis, tapetes, fios no chão, portas que abrem e fecham, pessoas e animais, base de recarga |
| Atuadores | Rodas com tração diferencial, escovas, motor de sucção, aviso sonoro |
| Sensores | LiDAR ou câmera para mapear, para-choque com chave de contato, sensores de desnível (anti-queda), encoders das rodas (odometria), sensor de sujeira, medidor de bateria |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | O robô não vê os outros cômodos nem o que está atrás do sofá, e sua posição é uma estimativa (a odometria acumula erro quando as rodas patinam no tapete). Por isso precisa do mapa e da posição estimada como estado |
| Agentes | Agente único | Pessoas e animais mudam o ambiente, mas não agem em função do desempenho do robô |
| Determinismo | Estocástico | As rodas patinam, a sujeira aparece, um animal empurra um objeto para o caminho |
| Episódico/sequencial | Sequencial | O trajeto de agora determina o que falta limpar e quanto de bateria sobra para o resto |
| Estático/dinâmico | Dinâmico | Pessoas e animais se movem e portas são fechadas durante a limpeza |
| Discreto/contínuo | Contínuo | Posição, orientação e velocidade são contínuas; o mapa costuma ser discretizado em células para facilitar o raciocínio |
| Conhecido/desconhecido | Conhecido quanto às ações, desconhecido quanto ao mapa | O efeito de girar as rodas é conhecido, mas a planta da casa não é dada; o robô precisa construí-la durante a operação |

#### 2.2 Monitor de sinais vitais em UTI com alarme filtrado

Monitores multiparamétricos de UTI disparam muitos alarmes falsos, por exemplo quando o paciente mexe a mão e o oxímetro perde o sinal. Um agente baseado em modelo reduz esse problema mantendo como estado as tendências recentes de cada sinal, uma estimativa da qualidade do sinal (há artefato de movimento?) e os alarmes já emitidos e reconhecidos pela equipe. As regras olham para esse estado. Um exemplo de regra: "se a SpO2 estimada está abaixo de 90% há mais de 15 segundos e a qualidade do sinal é boa, emitir alarme de alta prioridade". Os limiares aqui são ilustrativos; na prática são definidos pela equipe clínica.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Detectar deterioração real rapidamente (sensibilidade), reduzir alarmes falsos e a fadiga de alarme da equipe, nunca suprimir um evento crítico |
| Ambiente | Paciente no leito, equipe de enfermagem e médica, cabos e eletrodos, outros equipamentos do quarto |
| Atuadores | Alarmes sonoros e visuais com níveis de prioridade, mensagens na central de enfermagem, registro no prontuário eletrônico |
| Sensores | Oxímetro de pulso (SpO2), ECG, pressão arterial invasiva ou não invasiva, frequência respiratória, detecção de cabo desconectado |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | O agente mede sinais indiretos e ruidosos. O estado fisiológico real não é medido, e um valor baixo isolado pode ser artefato. Daí a necessidade da tendência como estado |
| Agentes | Agente único | O "processo" da doença não é modelado como agente (o livro faz a mesma escolha para o diagnóstico médico). A equipe recebe os alarmes, mas não compete nem coopera com o agente no sentido do livro |
| Determinismo | Estocástico | A evolução do paciente e o ruído dos sensores não são determinados pelo estado e pela ação |
| Episódico/sequencial | Sequencial | Um alarme emitido agora e reconhecido pela equipe muda o que deve ser feito em seguida (não repetir o mesmo alarme), e a decisão depende do histórico recente |
| Estático/dinâmico | Dinâmico | O paciente continua evoluindo enquanto o agente decide |
| Discreto/contínuo | Contínuo | Os sinais são grandezas contínuas amostradas ao longo do tempo; só as ações (níveis de alarme) são discretas |
| Conhecido/desconhecido | Conhecido | O efeito das ações (soar um alarme, enviar mensagem) é conhecido, e a fisiologia dos sinais está documentada na literatura clínica |

### 3. Agente baseado em objetivos

Saber como o mundo está não diz o que fazer quando há várias ações possíveis e só algumas levam aonde se quer chegar. O agente baseado em objetivos tem, além do estado e do modelo, uma descrição das situações desejáveis, e usa o modelo para prever o resultado de sequências de ações ("o que acontece se eu fizer isso?") até encontrar uma que atinja o objetivo. Busca (Capítulos 3 a 5) e planejamento (Capítulos 10 e 11) são as técnicas para isso. O livro mostra esse agente só em diagrama (Figura 2.13); um programa no mesmo estilo seria:

```text
função AGENTE-BASEADO-EM-OBJETIVOS(percepção) retorna uma ação
  persistente: estado, modelo, objetivo
               plano, uma sequência de ações, inicialmente vazia
               ação, a ação mais recente, inicialmente nenhuma
  estado ← ATUALIZAR-ESTADO(estado, ação, percepção, modelo)
  se plano está vazio ou não é mais válido para estado então
      plano ← BUSCA(estado, objetivo, modelo)
  ação  ← PRIMEIRO(plano)
  plano ← RESTO(plano)
  retornar ação
```

A vantagem que o livro aponta é a flexibilidade: o conhecimento está explícito, então basta trocar o objetivo para o agente ir a outro destino, enquanto um agente reativo precisaria de outro conjunto de regras.

#### 3.1 Navegação por GPS em aplicativo de rotas

O agente recebe o destino digitado pelo usuário, localiza o carro no mapa e busca no grafo da malha viária um caminho até o destino, usando, por exemplo, A* com o tempo estimado de cada trecho como custo. O agente não dirige: ele age por meio das instruções dadas ao motorista. Quando o motorista não segue a instrução, o estado (posição) deixa de ser compatível com o plano e o agente recalcula a rota, que é exatamente o teste "plano não é mais válido" do pseudocódigo.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Chegar ao destino; tempo e distância da rota; respeitar mão de via e conversões proibidas; recalcular rápido quando o motorista sai da rota; instruções dadas com antecedência suficiente |
| Ambiente | Malha viária (grafo de ruas e cruzamentos), trânsito, obras e bloqueios, motorista |
| Atuadores | Instruções por voz e na tela ("em 200 m, vire à direita"), desenho da rota no mapa |
| Sensores | Receptor GPS, acelerômetro e giroscópio do celular, base de mapas, dados de trânsito do servidor, tela de toque para o destino |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | O GPS tem erro de alguns metros e perde sinal em túneis; o trânsito à frente é conhecido só de forma agregada e atrasada |
| Agentes | Agente único | Os outros motoristas aparecem como condição de trânsito, não como adversários ou parceiros do aplicativo. O motorista funciona como atuador, um atuador que às vezes desobedece |
| Determinismo | Estocástico, planejado como determinístico | Na busca, cada trecho tem custo fixo e a ação "seguir pela rua X" leva ao cruzamento seguinte. Na prática o tempo de viagem varia e o motorista pode errar, por isso o replanejamento |
| Episódico/sequencial | Sequencial | Cada conversão restringe as rotas possíveis dali em diante |
| Estático/dinâmico | Dinâmico | O carro continua andando enquanto a rota é recalculada; se o cálculo demorar, a saída indicada já passou |
| Discreto/contínuo | Discreto no planejamento, contínuo no mundo | A busca trabalha num grafo finito de cruzamentos, mas posição e tempo são contínuos |
| Conhecido/desconhecido | Conhecido | O mapa e as regras de circulação são dados ao agente |

A fronteira com o agente baseado em utilidade aparece aqui. Enquanto o objetivo for "chegar ao destino" e o custo for um único número somado ao longo do caminho, o agente é de objetivos com custo de caminho, como nos problemas de busca do Capítulo 3. Se o aplicativo passar a pesar tempo, pedágio, risco de congestionamento e preferência do usuário por vias expressas, ele vira um agente baseado em utilidade.

#### 3.2 Robô móvel de armazém

Em armazéns automatizados, robôs pequenos andam sobre uma grade marcada no piso, entram embaixo de uma prateleira móvel, levantam-na e a levam até a estação onde um operador separa os itens do pedido. O objetivo de cada missão é "prateleira P na estação E, depois prateleira P de volta a uma posição livre". O robô planeja um caminho na grade com A*, reservando as células que vai ocupar junto ao servidor central, e replaneja quando o caminho é bloqueado.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Pedidos atendidos por hora, tempo médio por missão, nenhuma colisão, nenhum impasse (robôs bloqueando uns aos outros), consumo de energia |
| Ambiente | Piso do armazém dividido em células com marcadores, prateleiras móveis, dezenas de outros robôs, estações de separação com operadores, estações de recarga |
| Atuadores | Rodas (avançar, girar 90°), elevador que levanta a prateleira, rádio para pedir e liberar reservas de células |
| Sensores | Câmera inferior que lê os marcadores do piso (posição), câmera superior que identifica a prateleira, sensores de obstáculo, encoders, mensagens do servidor com as reservas dos outros robôs |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Completamente observável (no nível da grade) | Os marcadores dão a posição exata na grade, e as posições e reservas dos outros robôs chegam pelo servidor. Isso cobre tudo o que importa para o planejamento |
| Agentes | Multiagente cooperativo | Os outros robôs também estão maximizando o desempenho do armazém, e as escolhas de um afetam as dos outros (disputa por células e corredores) |
| Determinismo | Determinístico (praticamente) | "Avançar uma célula" leva à célula seguinte; falhas mecânicas são raras e tratadas como exceção. Pela definição do livro, a incerteza causada só pelas ações dos outros agentes não torna o ambiente estocástico |
| Episódico/sequencial | Sequencial | Cada movimento muda as opções seguintes e a missão só termina com a sequência completa |
| Estático/dinâmico | Dinâmico | Os outros robôs se movem enquanto este planeja |
| Discreto/contínuo | Discreto | Estados são células e orientações; ações são movimentos de uma célula e giros de 90° |
| Conhecido/desconhecido | Conhecido | A planta do armazém e o efeito de cada movimento são definidos no projeto |

### 4. Agente baseado em utilidade

Objetivos dão só uma distinção binária entre estados "felizes" e "infelizes". Quando há objetivos conflitantes (rapidez e segurança, por exemplo) ou quando nenhum objetivo pode ser atingido com certeza, o agente precisa de uma forma de comparar estados pelo grau de preferência. A **função utilidade** $U$ é, nas palavras do livro, uma internalização da medida de desempenho. Em ambiente estocástico ou parcialmente observável, o agente racional escolhe a ação de maior **utilidade esperada**:

$$a^* = \arg\max_{a} \sum_{s'} P(s' \mid s, a)\, U(s')$$

Como para o agente de objetivos, o livro mostra esse agente em diagrama (Figura 2.14). Um programa no mesmo estilo:

```text
função AGENTE-BASEADO-EM-UTILIDADE(percepção) retorna uma ação
  persistente: estado, modelo (inclui P(s' | s, a)), U, a função utilidade
               ação, a ação mais recente, inicialmente nenhuma
  estado ← ATUALIZAR-ESTADO(estado, ação, percepção, modelo)
  para cada a em AÇÕES(estado) faça
      UE[a] ← Σ sobre s' de P(s' | estado, a) × U(s')
  ação ← a com maior UE[a]
  retornar ação
```

#### 4.1 Agente de negociação e rebalanceamento de carteira

Um agente que administra uma carteira de ações não pode ter como objetivo apenas "ganhar dinheiro": quase toda estratégia pode ganhar ou perder, e as que rendem mais em média costumam ser as mais arriscadas. Uma função utilidade clássica é a de média e variância de Markowitz, $U = \mathbb{E}[R] - \lambda\,\text{Var}[R]$, em que $\lambda$ expressa a aversão do investidor ao risco. Antes de cada ordem, o agente estima a distribuição de retornos da carteira resultante, desconta os custos de transação e escolhe a operação (comprar, vender, não fazer nada) de maior utilidade esperada.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Retorno ajustado ao risco (por exemplo, índice de Sharpe), perda máxima acumulada dentro do limite, custos de corretagem e de impacto no preço, respeito às regras de exposição definidas pelo cliente e pela regulação |
| Ambiente | Bolsa de valores, livro de ofertas, outros investidores e robôs de negociação, notícias e indicadores econômicos |
| Atuadores | Envio, alteração e cancelamento de ordens de compra e venda; tamanho de cada posição |
| Sensores | Cotações em tempo real, livro de ofertas, saldo e posições da conta, notícias e calendário de indicadores |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | O agente não vê as intenções nem as ordens ocultas dos outros participantes, nem a informação que eles têm |
| Agentes | Multiagente competitivo | Do outro lado de cada negociação há outro agente tentando lucrar, e muitos deles reagem às ordens que aparecem no livro |
| Determinismo | Estocástico | Uma ordem enviada pode ser executada ou não, e a preços diferentes; o preço seguinte não é determinado pelo estado e pela ação |
| Episódico/sequencial | Sequencial | A posição montada hoje limita o que se pode fazer amanhã e determina o risco acumulado |
| Estático/dinâmico | Dinâmico | Os preços mudam enquanto o agente calcula; atraso de milissegundos muda o preço obtido |
| Discreto/contínuo | Discreto em sentido estrito, tratado como contínuo | Preços variam em incrementos mínimos e as quantidades são lotes inteiros, mas a granularidade é tão fina que os modelos tratam preço e tempo como contínuos |
| Conhecido/desconhecido | Desconhecido | As "leis" do mercado não são dadas: a distribuição de retornos e o impacto das próprias ordens precisam ser estimados a partir de dados, e mudam com o tempo |

#### 4.2 Despacho de ambulâncias (central de regulação do SAMU)

O agente decide qual viatura atende cada chamado e onde as viaturas livres devem esperar. A regra "mandar sempre a mais próxima" atinge o objetivo de atender o chamado, mas pode deixar uma região inteira descoberta. Um exemplo com valores hipotéticos: chega um chamado grave no centro. A viatura A está a 6 minutos, mas é a única cobrindo a zona norte; a viatura B está a 11 minutos. Suponha que a chance de sobrevida do paciente atual seja 0,80 com resposta em 6 minutos e 0,70 em 11 minutos, que a probabilidade de surgir outro chamado grave na zona norte enquanto A estiver fora seja 0,3, e que esse segundo paciente tenha sobrevida 0,78 se A estiver disponível e 0,40 se o socorro vier de longe. Tomando como utilidade o número esperado de sobreviventes:

$$UE(\text{mandar A}) = 0{,}80 + 0{,}3 \times 0{,}40 = 0{,}92 \qquad UE(\text{mandar B}) = 0{,}70 + 0{,}3 \times 0{,}78 = 0{,}934$$

Com esses números, mandar a viatura mais distante é a melhor decisão. O resultado muda se a probabilidade do segundo chamado for menor, e é justamente esse tipo de compromisso entre resultados incertos que um agente só de objetivos não consegue representar.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Tempo de resposta ponderado pela gravidade, sobrevida e sequelas esperadas, cobertura da cidade (fração da população a menos de X minutos de uma viatura livre), quilometragem e custo |
| Ambiente | Cidade com vias e trânsito, bases das viaturas, hospitais e sua lotação, chamados, equipe de regulação médica |
| Atuadores | Designar viatura a um chamado, reposicionar viaturas ociosas, indicar o hospital de destino |
| Sensores | Chamados com classificação de gravidade feita na triagem telefônica, GPS e status das viaturas (livre, em deslocamento, ocupada), dados de trânsito, ocupação dos hospitais |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | A gravidade real só é conhecida quando a equipe chega, e os chamados futuros, que definem o valor da cobertura, são desconhecidos |
| Agentes | Agente único | As viaturas são atuadores do mesmo agente; os pacientes e o trânsito não otimizam nada que dependa do despacho |
| Determinismo | Estocástico | O tempo de deslocamento varia com o trânsito, e o surgimento de chamados é aleatório |
| Episódico/sequencial | Sequencial | Mandar uma viatura agora muda a cobertura disponível para os próximos chamados, como o exemplo mostra |
| Estático/dinâmico | Dinâmico | Novos chamados chegam e as viaturas se movem enquanto o agente decide; demora na decisão é tempo de resposta perdido |
| Discreto/contínuo | Contínuo no mundo, discreto nas ações | Posições e tempos são contínuos; as ações são escolhas discretas (qual viatura, qual hospital) |
| Conhecido/desconhecido | Conhecido (em grande parte) | O efeito de despachar uma viatura é conhecido; as probabilidades de chamados por região e horário são estimadas do histórico e tratadas como dadas |

### 5. Agente com aprendizagem (adaptativo)

Qualquer um dos quatro tipos anteriores pode ser transformado em um agente com aprendizagem. O livro divide esse agente em quatro componentes (Figura 2.15):

- o **elemento de desempenho**, que é o agente "completo" das seções anteriores, recebe percepções e escolhe ações;
- o **crítico** compara o comportamento do agente com um **padrão de desempenho fixo**, externo ao agente, e gera realimentação;
- o **elemento de aprendizado** usa essa realimentação para modificar o elemento de desempenho;
- o **gerador de problemas** sugere ações exploratórias, que podem não ser ótimas agora mas trazem informação útil para depois.

A aprendizagem é o que permite operar em ambientes desconhecidos ou que mudam com o tempo. Um programa no espírito do livro:

```text
função AGENTE-COM-APRENDIZAGEM(percepção) retorna uma ação
  persistente: elemento_desempenho, o programa que escolhe as ações
               padrão, o padrão de desempenho (fixo, externo ao agente)
  realimentação ← CRÍTICO(percepção, padrão)
  elemento_desempenho ← ELEMENTO-DE-APRENDIZADO(elemento_desempenho, realimentação)
  ação ← elemento_desempenho(percepção)
  se GERADOR-DE-PROBLEMAS sugere experimento então
      ação ← AÇÃO-EXPLORATÓRIA()
  retornar ação
```

A Aula 2 da disciplina mostra um caso desse esquema: a base de conhecimento de um agente de análise de risco de crédito é construída automaticamente, por indução de árvore de decisão, a partir de exemplos rotulados. O algoritmo de indução faz o papel do elemento de aprendizado, e a árvore (ou as regras extraídas dela) vira o elemento de desempenho.

#### 5.1 Filtro de spam que aprende com o usuário

O elemento de desempenho é um classificador, por exemplo Naive Bayes sobre as palavras e os cabeçalhos da mensagem. O crítico é o próprio usuário: cada vez que ele marca uma mensagem como spam ou tira uma mensagem da pasta de spam, o crítico registra um erro do classificador. O elemento de aprendizado atualiza as contagens de palavras ou os pesos do modelo com esses rótulos. O gerador de problemas é fraco nesta aplicação, porque mandar de propósito um e-mail legítimo para o spam só para aprender custaria caro ao usuário. O máximo de exploração aceitável é deixar mensagens duvidosas na caixa de entrada com um aviso de "possível spam", o que obtém o rótulo do usuário sem esconder a mensagem.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Porcentagem de spam bloqueado; taxa de falsos positivos (e-mail legítimo na pasta de spam), que pesa mais que deixar passar um spam; manutenção da taxa de acerto à medida que os spammers mudam as mensagens |
| Ambiente | Fluxo de e-mails recebidos, remetentes legítimos, spammers, o usuário |
| Atuadores | Entregar na caixa de entrada, mover para spam, marcar como suspeito, bloquear remetente |
| Sensores | Texto, anexos e cabeçalhos da mensagem, reputação do remetente e do servidor de origem, ações do usuário (marcar como spam, "não é spam") |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | A intenção do remetente não é visível, e o usuário só rotula uma fração das mensagens, então boa parte dos erros nunca chega ao crítico |
| Agentes | Multiagente competitivo | Os spammers mudam o texto das mensagens para passar pelo filtro: o desempenho deles depende de enganar o agente |
| Determinismo | Estocástico | O próximo e-mail não é determinado pela decisão atual, e a reação do usuário também não |
| Episódico/sequencial | Episódico na decisão, sequencial no aprendizado | Classificar uma mensagem não muda a próxima, mas cada rótulo altera o modelo e as decisões seguintes, e os spammers reagem ao que é bloqueado |
| Estático/dinâmico | Estático | A mensagem não muda enquanto é classificada |
| Discreto/contínuo | Discreto | Texto, tokens e ações (entregar, mover) são discretos |
| Conhecido/desconhecido | Desconhecido | O que distingue spam de mensagem legítima não é dado de antemão e muda com o tempo; precisa ser aprendido e reaprendido |

#### 5.2 Sistema de recomendação de vídeos

O elemento de desempenho é um modelo que pontua os itens do catálogo para o usuário (por exemplo, filtragem colaborativa) e monta a tela inicial. O crítico compara a reação do usuário com o padrão de desempenho: assistir até o fim conta como sucesso, abandonar em segundos conta como falha. O elemento de aprendizado atualiza as representações do usuário e dos itens. Aqui o gerador de problemas tem papel central: se o sistema só mostrar o que já sabe que agrada, nunca vai descobrir o interesse do usuário por um gênero novo, nem quanto vale um lançamento ainda sem histórico. Por isso parte das posições da tela é reservada para exploração, com estratégias como $\varepsilon$-greedy ou bandidos multibraço.

O cuidado que o livro pede com o padrão de desempenho aparece de forma concreta. Se o crítico medir só cliques, o agente aprende a recomendar títulos chamativos que não satisfazem o usuário, e a métrica sobe enquanto o desempenho real cai.

| PEAS | Descrição |
| :--- | :--- |
| Desempenho | Tempo assistido, taxa de conclusão, avaliações, retenção do assinante ao longo dos meses, diversidade e novidade das recomendações, não recomendar conteúdo impróprio para o perfil |
| Ambiente | Catálogo de títulos, usuários e perfis, contexto (horário, dispositivo), lançamentos |
| Atuadores | Escolher e ordenar os títulos de cada fileira da tela inicial, enviar notificações, sugerir o próximo episódio |
| Sensores | Histórico de reprodução, pausas e abandonos, buscas, avaliações, metadados dos títulos |

| Propriedade | Classificação | Justificativa |
| :--- | :--- | :--- |
| Observabilidade | Parcialmente observável | A preferência do usuário não é observada diretamente, só inferida do comportamento; numa conta compartilhada nem se sabe quem está assistindo |
| Agentes | Agente único | Há muitos usuários, mas eles não competem nem cooperam com o agente; cada um é tratado como parte do ambiente |
| Determinismo | Estocástico | O mesmo usuário reage de forma diferente à mesma recomendação em dias diferentes |
| Episódico/sequencial | Sequencial | As recomendações de hoje moldam o histórico que alimenta as de amanhã e podem até mudar o gosto do usuário |
| Estático/dinâmico | Dinâmico | O catálogo muda, os gostos mudam, e a tela precisa ser montada em milissegundos |
| Discreto/contínuo | Discreto | Itens, cliques e posições na tela são discretos (as representações internas são vetores contínuos, mas isso é escolha do agente, não propriedade do ambiente) |
| Conhecido/desconhecido | Desconhecido | O efeito de recomendar um título a um usuário não é conhecido de antemão, sobretudo para usuários e títulos novos |

### 6. Comparação das dez aplicações

| Aplicação | Categoria | Observável | Agentes | Determinístico | Episódico | Estático | Discreto | Conhecido |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Porta automática | Reativo simples | Parcial (basta para a regra) | Único | Estocástico | Episódico | Dinâmico | Contínuo / interface discreta | Conhecido |
| Triagem de pacotes | Reativo simples | Completo | Único | Determinístico | Episódico | Dinâmico | Discreto | Conhecido |
| Robô aspirador com mapa | Baseado em modelo | Parcial | Único | Estocástico | Sequencial | Dinâmico | Contínuo | Ações conhecidas, mapa não |
| Monitor de UTI | Baseado em modelo | Parcial | Único | Estocástico | Sequencial | Dinâmico | Contínuo | Conhecido |
| Navegação GPS | Baseado em objetivos | Parcial | Único | Estocástico (planejado como determinístico) | Sequencial | Dinâmico | Discreto no plano | Conhecido |
| Robô de armazém | Baseado em objetivos | Completo (na grade) | Multi (cooperativo) | Determinístico | Sequencial | Dinâmico | Discreto | Conhecido |
| Negociação de ações | Baseado em utilidade | Parcial | Multi (competitivo) | Estocástico | Sequencial | Dinâmico | Tratado como contínuo | Desconhecido |
| Despacho de ambulâncias | Baseado em utilidade | Parcial | Único | Estocástico | Sequencial | Dinâmico | Contínuo / ações discretas | Conhecido |
| Filtro de spam | Com aprendizagem | Parcial | Multi (competitivo) | Estocástico | Episódico (decisão) | Estático | Discreto | Desconhecido |
| Recomendação de vídeos | Com aprendizagem | Parcial | Único | Estocástico | Sequencial | Dinâmico | Discreto | Desconhecido |

### 7. Por que a categoria depende das propriedades do ambiente

A tabela mostra um padrão. Os dois agentes reativos simples estão em ambientes episódicos em que a informação necessária para decidir está na percepção do momento. Os agentes que precisam de estado interno aparecem exatamente onde o ambiente é parcialmente observável e sequencial. Os agentes de objetivo e de utilidade trabalham em ambientes sequenciais, em que é preciso pensar à frente. Os agentes com aprendizagem estão onde o ambiente é desconhecido ou muda.

Cada propriedade do ambiente cria uma exigência para o programa do agente:

| Propriedade do ambiente | O que ela exige do agente | Categoria mínima |
| :--- | :--- | :--- |
| Completamente observável e episódico | Mapear a percepção atual na ação | Reativo simples |
| Parcialmente observável | Lembrar o que não está sendo visto agora e estimar o estado | Baseado em modelo |
| Sequencial, com muitas sequências possíveis e um destino explícito | Prever o efeito de sequências de ações e buscar uma que atinja o objetivo | Baseado em objetivos |
| Estocástico, com objetivos conflitantes ou sem garantia de sucesso | Comparar resultados incertos por grau de preferência | Baseado em utilidade |
| Desconhecido ou não estacionário | Melhorar o próprio programa a partir da experiência | Com aprendizagem |

As categorias são cumulativas. O agente de objetivos usa o modelo do agente baseado em modelo, e o de utilidade também mantém estado e modelo. A aprendizagem pode ser acrescentada a qualquer uma delas: o robô aspirador aprende o mapa, o agente de negociação reestima a distribuição de retornos todos os dias. Nos sistemas reais as categorias aparecem misturadas. O próprio robô aspirador tem um componente de objetivo ("voltar à base"), e o aplicativo de rotas vira um agente de utilidade quando passa a pesar pedágio e risco de congestionamento.

A escolha certa é a categoria mais simples que atinge a medida de desempenho no ambiente dado. Uma porta automática com função utilidade e planejamento seria mais cara, mais lenta e mais difícil de certificar, sem abrir a porta melhor. Por outro lado, aplicar um agente reativo ao despacho de ambulâncias ("sempre a mais próxima") ignora a natureza sequencial e estocástica da tarefa e, como mostrou o exemplo da seção 4.2, pode levar a decisões piores. O livro resume a questão ao apresentar as dimensões: "Em grande parte, essas dimensões determinam o projeto apropriado de agentes". Analisar o ambiente de tarefa com PEAS e as sete propriedades antes de escolher a arquitetura evita tanto o agente simples demais quanto o complexo demais.

### Referências (Q4)

1. RUSSELL, Stuart J.; NORVIG, Peter. *Inteligência Artificial*. 3. ed. Rio de Janeiro: Elsevier, 2013. Capítulo 2 (Agentes inteligentes).
2. COSTA, Evandro de Barros. *Aprendizagem de Máquina e Construção de Base de Conhecimento: Indução de Árvore de Decisão* (Aula 2). Slides da disciplina ECOM031, UFAL, 2026.
3. MARKOWITZ, Harry. Portfolio Selection. *The Journal of Finance*, v. 7, n. 1, p. 77-91, 1952.
