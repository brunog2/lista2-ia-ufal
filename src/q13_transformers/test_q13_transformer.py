import numpy as np
import pytest

import transformer_numpy as tf
import treino as T

VOCAB = T.vocab_do_corpus()
IDS = tf.encode("o gato sentou no tapete", VOCAB)
P = tf.init_params(len(VOCAB), d_model=8, n_heads=2, d_ff=32, seed=0)


def test_softmax_soma_um_e_ignora_menos_infinito():
    x = np.array([[1.0, 2.0, -np.inf], [1000.0, 1000.0, 999.0]])
    w = tf.softmax(x)
    assert np.allclose(w.sum(-1), 1)
    assert w[0, 2] == 0
    assert np.all(np.isfinite(w))


def test_pesos_de_atencao_somam_um():
    _, _, tr = tf.forward(IDS, P)
    assert np.allclose(tr["weights"].sum(-1), 1)


def test_mascara_causal_zera_o_futuro():
    _, _, tr = tf.forward(IDS, P)
    assert np.all(tr["weights"][:, tf.causal_mask(5)] == 0)


def test_mudar_o_futuro_nao_muda_o_passado():
    outra = tf.encode("o gato sentou no sofá", VOCAB)
    a, _, _ = tf.forward(IDS, P)
    b, _, _ = tf.forward(outra, P)
    assert np.allclose(a[:4], b[:4])
    assert not np.allclose(a[4], b[4])


def test_equivariancia_a_permutacao_sem_posicao_e_sem_mascara():
    x = P["E"][IDS]
    perm = np.array([4, 2, 0, 3, 1])
    y, _ = tf.decoder_block(x, P)
    y_perm, _ = tf.decoder_block(x[perm], P)
    assert np.allclose(y_perm, y[perm])


def test_codificacao_posicional_quebra_a_equivariancia():
    perm = np.array([4, 2, 0, 3, 1])
    a, _, _ = tf.forward(IDS, P, causal=False)
    b, _, _ = tf.forward(IDS[perm], P, causal=False)
    assert not np.allclose(b, a[perm])
    a0, _, _ = tf.forward(IDS, P, use_pos=False, causal=False)
    b0, _, _ = tf.forward(IDS[perm], P, use_pos=False, causal=False)
    assert np.allclose(b0, a0[perm])


def test_codificacao_posicional_valores_conhecidos():
    pe = tf.positional_encoding(50, 16)
    assert np.allclose(pe[0, 0::2], 0) and np.allclose(pe[0, 1::2], 1)
    assert np.isclose(pe[1, 0], np.sin(1)) and np.isclose(pe[1, 1], np.cos(1))
    assert np.abs(pe).max() <= 1


def test_shapes_do_forward():
    logits, probs, tr = tf.forward(IDS, P)
    assert logits.shape == probs.shape == (5, len(VOCAB))
    assert tr["Q"].shape == tr["K"].shape == tr["V"].shape == (2, 5, 4)
    assert tr["weights"].shape == (2, 5, 5)
    assert tr["x2"].shape == (5, 8)
    assert np.allclose(probs.sum(-1), 1)


def test_layer_norm_media_zero_desvio_um():
    _, _, tr = tf.forward(IDS, P)
    assert np.allclose(tr["x1"].mean(-1), 0, atol=1e-7)
    assert np.allclose(tr["x1"].std(-1), 1, atol=1e-3)


@pytest.mark.parametrize("nome", ["E", "Wq", "Wk", "Wv", "Wo", "U"])
def test_gradiente_manual_bate_com_diferencas_finitas(nome):
    ids = np.array([tf.encode(s, VOCAB) for s in T.corpus()[:4]])
    p = T.init(len(VOCAB), d=8, seed=1)
    _, g = T.loss_and_grads(ids, p)
    rng = np.random.default_rng(0)
    for _ in range(5):
        idx = tuple(rng.integers(0, s) for s in p[nome].shape)
        if nome == "E":  # só linhas de tokens que aparecem no lote têm gradiente
            idx = (ids[0, rng.integers(0, ids.shape[1])], idx[1])
        old, h = p[nome][idx], 1e-5
        p[nome][idx] = old + h
        lp, _ = T.loss_and_grads(ids, p)
        p[nome][idx] = old - h
        lm, _ = T.loss_and_grads(ids, p)
        p[nome][idx] = old
        assert np.isclose(g[nome][idx], (lp - lm) / (2 * h), rtol=1e-4, atol=1e-8)
