"""Mini-Transformer decoder-only em numpy puro (Questão 13).

Cada função corresponde a uma etapa descrita em Vaswani et al. (2017):
embeddings, codificação posicional senoidal, atenção scaled dot-product com
máscara causal, multi-head, FFN, conexões residuais com LayerNorm e a projeção
final para o vocabulário seguida de softmax. O objetivo é didático: os pesos são
aleatórios (semente fixa) e servem para mostrar as contas, não para gerar texto.
"""
import numpy as np


# ---------------------------------------------------------------- tokenização
def build_vocab(sentences):
    """Vocabulário em nível de palavra, na ordem da primeira ocorrência."""
    vocab = []
    for s in sentences:
        for w in s.split():
            if w not in vocab:
                vocab.append(w)
    return vocab


def encode(text, vocab):
    return np.array([vocab.index(w) for w in text.split()])


def decode(ids, vocab):
    return " ".join(vocab[i] for i in ids)


# ------------------------------------------------------------ peças básicas
def softmax(x, axis=-1):
    """Softmax numericamente estável; entradas -inf viram probabilidade 0."""
    z = x - x.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def positional_encoding(n, d_model):
    """PE[pos, 2i] = sin(pos / 10000^(2i/d)), PE[pos, 2i+1] = cos(...). d_model par."""
    pos = np.arange(n)[:, None]
    two_i = np.arange(0, d_model, 2)[None, :]
    ang = pos / 10000 ** (two_i / d_model)
    pe = np.zeros((n, d_model))
    pe[:, 0::2] = np.sin(ang)
    pe[:, 1::2] = np.cos(ang)
    return pe


def causal_mask(n):
    """True onde a posição i NÃO pode olhar a posição j (j > i, o futuro)."""
    return np.triu(np.ones((n, n), dtype=bool), k=1)


def attention(Q, K, V, mask=None):
    """Atenção scaled dot-product: softmax(Q K^T / sqrt(d_k) + máscara) V.

    Aceita eixos extras à esquerda (cabeças, lote). Devolve a saída, os pesos
    de atenção e os scores já escalados (antes da máscara).
    """
    d_k = Q.shape[-1]
    scores = Q @ np.swapaxes(K, -1, -2) / np.sqrt(d_k)
    masked = scores if mask is None else np.where(mask, -np.inf, scores)
    weights = softmax(masked)
    return weights @ V, weights, scores


def layer_norm(x, gamma, beta, eps=1e-5):
    mu = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return gamma * (x - mu) / np.sqrt(var + eps) + beta


# ----------------------------------------------------------------- o modelo
def init_params(vocab_size, d_model=8, n_heads=2, d_ff=32, seed=0):
    rng = np.random.default_rng(seed)

    def mat(fan_in, fan_out):
        return rng.normal(0, 1 / np.sqrt(fan_in), size=(fan_in, fan_out))

    return {
        "n_heads": n_heads,
        "E": rng.normal(0, 1, size=(vocab_size, d_model)),  # também é a saída (pesos amarrados)
        "Wq": mat(d_model, d_model), "Wk": mat(d_model, d_model),
        "Wv": mat(d_model, d_model), "Wo": mat(d_model, d_model),
        "W1": mat(d_model, d_ff), "b1": np.zeros(d_ff),
        "W2": mat(d_ff, d_model), "b2": np.zeros(d_model),
        "g1": np.ones(d_model), "be1": np.zeros(d_model),
        "g2": np.ones(d_model), "be2": np.zeros(d_model),
    }


def multi_head_attention(x, p, mask=None):
    """Projeta x em Q, K, V, divide em h cabeças de d_k = d_model/h e concatena."""
    n, d = x.shape
    h = p["n_heads"]

    def split(m):  # (n, d) -> (h, n, d_k)
        return m.reshape(n, h, d // h).transpose(1, 0, 2)

    Q, K, V = split(x @ p["Wq"]), split(x @ p["Wk"]), split(x @ p["Wv"])
    heads, weights, scores = attention(Q, K, V, mask)
    concat = heads.transpose(1, 0, 2).reshape(n, d)
    return concat @ p["Wo"], {"Q": Q, "K": K, "V": V, "scores": scores,
                              "weights": weights, "heads": heads, "concat": concat}


def feed_forward(x, p):
    """FFN posição a posição: max(0, x W1 + b1) W2 + b2."""
    return np.maximum(0, x @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]


def decoder_block(x, p, mask=None):
    """Bloco pós-LN, como no artigo original: LayerNorm(x + Subcamada(x))."""
    a, trace = multi_head_attention(x, p, mask)
    x1 = layer_norm(x + a, p["g1"], p["be1"])
    f = feed_forward(x1, p)
    x2 = layer_norm(x1 + f, p["g2"], p["be2"])
    trace.update(attn_out=a, x1=x1, ffn_out=f, x2=x2)
    return x2, trace


def forward(ids, p, use_pos=True, causal=True):
    """ids -> (logits, probabilidades, rastro de todas as etapas intermediárias)."""
    n, d = len(ids), p["E"].shape[1]
    emb = p["E"][ids]
    pe = positional_encoding(n, d) if use_pos else np.zeros((n, d))
    x0 = emb + pe
    x2, trace = decoder_block(x0, p, causal_mask(n) if causal else None)
    logits = x2 @ p["E"].T
    trace.update(emb=emb, pe=pe, x0=x0)
    return logits, softmax(logits), trace
