# Q13: mini-Transformer em numpy

Código de apoio ao ensaio [`docs/q13_transformers.md`](../../docs/q13_transformers.md). Tudo é numpy puro, sem PyTorch.

## Arquivos

| Arquivo | Conteúdo |
| :--- | :--- |
| `transformer_numpy.py` | Tokenização por palavra, softmax estável, codificação posicional senoidal, máscara causal, atenção scaled dot-product, multi-head, LayerNorm, FFN, um bloco decoder-only (pós-LN, como no artigo original) e a projeção para o vocabulário com pesos amarrados à matriz de embeddings. |
| `treino.py` | Corpus de brinquedo (96 frases do tipo "o gato sentou no tapete e depois ele dormiu"), um modelo de uma camada só de atenção com gradiente escrito à mão, otimizador Adam e geração gulosa. |
| `q13_transformers.ipynb` | Notebook executado. Segue a frase "o gato sentou no tapete" por todas as etapas, mede o efeito de $\sqrt{d_k}$ e roda o treino. |
| `test_q13_transformer.py` | 15 testes: softmax soma 1, máscara zera o futuro, mudar o último token não altera as posições anteriores, equivariância à permutação sem posição, valores da codificação posicional, shapes, LayerNorm e conferência do gradiente manual por diferenças finitas. |
| `figures/` | Figuras PNG geradas pelo notebook e usadas no ensaio. |

## Como rodar

A partir da raiz do repositório:

```bash
.venv/bin/python -m pytest src/q13_transformers -q
cd src/q13_transformers && ../../.venv/bin/jupyter nbconvert --to notebook --execute --inplace q13_transformers.ipynb
```

O notebook leva cerca de 25 segundos (a maior parte é o treino com 10 sementes). Todas as sementes são fixas, então os números se repetem.

## Resultados principais

- Demonstração com pesos aleatórios ($d_{model}=8$, 2 cabeças, $d_k=4$): os pesos de atenção da última posição ("tapete") na cabeça 1 são 0,21, 0,15, 0,26, 0,13 e 0,25, e a conta manual bate com a do código. A máscara zera tudo acima da diagonal.
- Com máscara causal, as saídas do prefixo "o gato sentou no" não mudam quando "tapete" é acrescentado, e a atenção calculada só com a linha nova mais K e V guardados é idêntica à completa (é o que o KV cache explora).
- Sem codificação posicional e sem máscara, permutar a entrada só permuta a saída. Com a codificação posicional, não.
- Escala: sem dividir por $\sqrt{d_k}$, o peso máximo médio da softmax sobre 8 chaves sobe de 0,52 ($d_k=4$) para 0,97 ($d_k=1024$) e a norma do jacobiano cai de 0,34 para 0,04. Com a divisão, ficam em torno de 0,36 e 0,37 para qualquer $d_k$.
- Treino (semente 0): perda de 4,16 para 0,46 em 1500 passos. A acurácia em prever "ele"/"ela" nas 24 frases de teste vai de 50% para 100%, e a posição "depois" passa a pôr 0,58 do peso no artigo "o/a" do sujeito. Em 10 sementes, 7 chegam a 100% no teste; 2 ficam presas num mínimo em que a atenção olha só para si mesma (50%) e 1 chega a 75%.

## Limitações

Os pesos da demonstração são aleatórios, então as previsões da Parte 6 não têm sentido linguístico. O modelo treinado não tem FFN nem LayerNorm (para o gradiente caber em poucas linhas), usa vocabulário de 22 palavras e decora parte do treino: a perda de teste (0,83) fica acima da de treino (0,46).
