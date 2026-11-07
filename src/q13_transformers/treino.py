"""Treino minúsculo de um modelo de linguagem só de atenção (uma camada, uma cabeça).

Modelo: X = E[ids] + PE;  Z = X + softmax(mask(Q K^T / sqrt(d))) V Wo;  logits = Z U.
Sem FFN e sem LayerNorm para que o gradiente possa ser escrito à mão em poucas
linhas. A tarefa é prever a próxima palavra em frases como
"o gato sentou no tapete e depois ele dormiu": para acertar "ele"/"ela" a
posição de "depois" precisa olhar para o sujeito, cinco palavras atrás, e
ignorar o "no/na" e o lugar, que também têm gênero.
"""
import itertools

import numpy as np

from transformer_numpy import build_vocab, causal_mask, positional_encoding, softmax

SUJEITOS = [("o gato", "ele"), ("a gata", "ela"), ("o cachorro", "ele"),
            ("a cadela", "ela"), ("o menino", "ele"), ("a menina", "ela")]
VERBOS = ["sentou", "deitou"]
LUGARES = ["no tapete", "no sofá", "na cadeira", "na cama"]
FINAIS = ["dormiu", "saiu"]
POS_DEPOIS = 6  # índice de "depois"; o alvo nessa posição é o pronome


def corpus():
    return [f"{s} {v} {lug} e depois {pron} {fim}"
            for (s, pron), v, lug, fim in itertools.product(SUJEITOS, VERBOS, LUGARES, FINAIS)]


def split_corpus(frases, frac_teste=0.25, seed=0):
    idx = np.random.default_rng(seed).permutation(len(frases))
    corte = int(len(frases) * (1 - frac_teste))
    return [frases[i] for i in idx[:corte]], [frases[i] for i in idx[corte:]]


def vocab_do_corpus():
    return build_vocab(corpus())


def init(vocab_size, d=16, seed=0):
    rng = np.random.default_rng(seed)
    m = lambda a, b: rng.normal(0, 1 / np.sqrt(a), size=(a, b))  # noqa: E731
    return {"E": rng.normal(0, 1, size=(vocab_size, d)), "Wq": m(d, d), "Wk": m(d, d),
            "Wv": m(d, d), "Wo": m(d, d), "U": m(d, vocab_size)}


def forward(ids, p):
    """ids: (B, n). Devolve logits (B, n, V) e o cache para o backward."""
    n, d = ids.shape[1], p["E"].shape[1]
    X = p["E"][ids] + positional_encoding(n, d)
    Q, K, V = X @ p["Wq"], X @ p["Wk"], X @ p["Wv"]
    S = np.where(causal_mask(n), -np.inf, Q @ K.transpose(0, 2, 1) / np.sqrt(d))
    A = softmax(S)
    H = A @ V
    Z = X + H @ p["Wo"]
    return Z @ p["U"], (ids, X, Q, K, V, A, H, Z)


def loss_and_grads(ids, p):
    """Entropia cruzada média da próxima palavra e gradientes calculados à mão."""
    logits, (ids, X, Q, K, V, A, H, Z) = forward(ids, p)
    d = X.shape[-1]
    probs = softmax(logits[:, :-1])
    alvo = ids[:, 1:]
    B, m = alvo.shape
    loss = -np.log(probs[np.arange(B)[:, None], np.arange(m)[None, :], alvo]).mean()

    dlogits = np.zeros_like(logits)
    dlogits[:, :-1] = probs
    dlogits[np.arange(B)[:, None], np.arange(m)[None, :], alvo] -= 1
    dlogits /= B * m

    g = {"U": np.einsum("bnd,bnv->dv", Z, dlogits)}
    dZ = dlogits @ p["U"].T
    g["Wo"] = np.einsum("bnd,bne->de", H, dZ)
    dH = dZ @ p["Wo"].T
    dA = dH @ V.transpose(0, 2, 1)
    dV = A.transpose(0, 2, 1) @ dH
    dS = A * (dA - (dA * A).sum(-1, keepdims=True)) / np.sqrt(d)  # jacobiano da softmax
    dQ, dK = dS @ K, dS.transpose(0, 2, 1) @ Q
    g["Wq"] = np.einsum("bnd,bne->de", X, dQ)
    g["Wk"] = np.einsum("bnd,bne->de", X, dK)
    g["Wv"] = np.einsum("bnd,bne->de", X, dV)
    dX = dZ + dQ @ p["Wq"].T + dK @ p["Wk"].T + dV @ p["Wv"].T
    g["E"] = np.zeros_like(p["E"])
    np.add.at(g["E"], ids, dX)
    return loss, g


def train(ids, p, steps=300, lr=0.02, b1=0.9, b2=0.999, eps=1e-8):
    """Adam em lote completo. Altera p no lugar e devolve a curva de perda."""
    m = {k: np.zeros_like(v) for k, v in p.items()}
    v = {k: np.zeros_like(v) for k, v in p.items()}
    losses = []
    for t in range(1, steps + 1):
        loss, g = loss_and_grads(ids, p)
        losses.append(loss)
        for k in p:
            m[k] = b1 * m[k] + (1 - b1) * g[k]
            v[k] = b2 * v[k] + (1 - b2) * g[k] ** 2
            p[k] -= lr * (m[k] / (1 - b1 ** t)) / (np.sqrt(v[k] / (1 - b2 ** t)) + eps)
    return losses


def pronoun_accuracy(ids, p):
    logits, _ = forward(ids, p)
    return float((logits[:, POS_DEPOIS].argmax(-1) == ids[:, POS_DEPOIS + 1]).mean())


def attention_from_depois(ids, p):
    """Pesos de atenção da posição "depois" sobre as 7 posições visíveis, média no lote."""
    _, cache = forward(ids, p)
    return cache[5][:, POS_DEPOIS, :POS_DEPOIS + 1].mean(0)


def generate(prompt_ids, p, n_new):
    """Decodificação gulosa: a cada passo, roda o modelo e anexa o token mais provável."""
    ids = list(prompt_ids)
    for _ in range(n_new):
        logits, _ = forward(np.array([ids]), p)
        ids.append(int(logits[0, -1].argmax()))
    return ids
