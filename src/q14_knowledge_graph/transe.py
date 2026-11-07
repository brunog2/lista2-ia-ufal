"""TransE em numpy, protocolo de previsão de links e baselines (Questão 14).

TransE (Bordes et al., 2013) representa entidades e relações como vetores e trata cada
relação como uma translação: para uma tripla verdadeira (h, r, t), espera-se h + r ≈ t.
O escore de plausibilidade é -||h + r - t||_2 e o treino minimiza a perda de margem

    L = soma max(0, margem + d(h, r, t) - d(h', r, t'))

em que (h', r, t') é a tripla corrompida trocando a cabeça ou a cauda por uma entidade
sorteada. A avaliação segue o protocolo "filtrado": ao ranquear as candidatas para
(h, r, ?), as outras caudas verdadeiras conhecidas saem da disputa.
"""

import numpy as np
from rdflib import Graph

from kg import ARBO, individuos, local
from raciocinio import materializar


# ----------------------------------------------------------------------------- dados

def triplas_relacionais(g: Graph, entidades=None) -> list:
    """Triplas (h, r, t) entre indivíduos com predicado do namespace arbo, como strings."""
    entidades = individuos(g) if entidades is None else entidades
    return sorted((local(s), local(p), local(o)) for s, p, o in g
                  if s in entidades and o in entidades and str(p).startswith(str(ARBO)))


def dividir(triplas: list, frac_teste: float, seed: int):
    """Separa treino e teste garantindo que toda entidade e relação do teste exista no treino.

    Uma entidade que só aparece no teste não tem embedding treinado, então a tripla volta
    para o treino. Por isso o teste final pode ficar um pouco menor que frac_teste.
    """
    rng = np.random.default_rng(seed)
    ordem = rng.permutation(len(triplas))
    n_teste = int(round(frac_teste * len(triplas)))
    teste = [triplas[i] for i in ordem[:n_teste]]
    treino = [triplas[i] for i in ordem[n_teste:]]
    while True:
        vistos = {x for h, r, t in treino for x in (h, r, t)}
        devolver = [tr for tr in teste if not set(tr) <= vistos]
        if not devolver:
            return treino, teste
        treino += devolver
        teste = [tr for tr in teste if tr not in devolver]


class Indice:
    """Mapeia nomes de entidades e relações para inteiros."""

    def __init__(self, entidades, relacoes):
        self.ent = {e: i for i, e in enumerate(sorted(entidades))}
        self.rel = {r: i for i, r in enumerate(sorted(relacoes))}
        self.nome_ent = sorted(entidades)

    def ids(self, triplas):
        return np.array([(self.ent[h], self.rel[r], self.ent[t]) for h, r, t in triplas], dtype=int)


# ----------------------------------------------------------------------------- TransE

def treinar_transe(treino_ids, n_ent, n_rel, dim=32, margem=1.0, lr=0.01,
                   epocas=500, lote=32, negativos=4, seed=0):
    """Treina TransE com SGD em minilotes. Devolve (E, R, perda_media_por_epoca)."""
    rng = np.random.default_rng(seed)
    lim = 6 / np.sqrt(dim)  # inicialização do artigo original
    E = rng.uniform(-lim, lim, (n_ent, dim))
    R = rng.uniform(-lim, lim, (n_rel, dim))
    R /= np.linalg.norm(R, axis=1, keepdims=True)
    perdas = []

    for _ in range(epocas):
        E /= np.linalg.norm(E, axis=1, keepdims=True)  # restrição ||e|| = 1 do artigo
        pos = np.repeat(treino_ids, negativos, axis=0)[rng.permutation(len(treino_ids) * negativos)]
        neg = pos.copy()
        troca_cabeca = rng.random(len(neg)) < 0.5
        aleatorias = rng.integers(0, n_ent, len(neg))
        neg[troca_cabeca, 0] = aleatorias[troca_cabeca]
        neg[~troca_cabeca, 2] = aleatorias[~troca_cabeca]

        soma = 0.0
        for i in range(0, len(pos), lote):
            p, n = pos[i:i + lote], neg[i:i + lote]
            dp = E[p[:, 0]] + R[p[:, 1]] - E[p[:, 2]]
            dn = E[n[:, 0]] + R[n[:, 1]] - E[n[:, 2]]
            np_, nn_ = np.linalg.norm(dp, axis=1), np.linalg.norm(dn, axis=1)
            viol = margem + np_ - nn_ > 0
            soma += np.maximum(0, margem + np_ - nn_).sum()
            if not viol.any():
                continue
            # gradiente de ||x||_2 é x/||x||; só as triplas que violam a margem contribuem
            gp = dp[viol] / (np_[viol, None] + 1e-9)
            gn = dn[viol] / (nn_[viol, None] + 1e-9)
            pv, nv = p[viol], n[viol]
            gE, gR = np.zeros_like(E), np.zeros_like(R)
            np.add.at(gE, pv[:, 0], gp)
            np.add.at(gE, pv[:, 2], -gp)
            np.add.at(gR, pv[:, 1], gp)
            np.add.at(gE, nv[:, 0], -gn)
            np.add.at(gE, nv[:, 2], gn)
            np.add.at(gR, nv[:, 1], -gn)
            E -= lr * gE
            R -= lr * gR
        perdas.append(soma / len(pos))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    return E, R, perdas


def escores_transe(E, R):
    """Função de escore para o protocolo de ranking: maior é mais plausível."""
    def caudas(h, r):
        return -np.linalg.norm(E[h] + R[r] - E, axis=1)

    def cabecas(r, t):
        return -np.linalg.norm(E + R[r] - E[t], axis=1)
    return caudas, cabecas


def escores_frequencia(treino_ids, n_ent):
    """Baseline: a candidata mais frequente naquela posição da relação, no treino."""
    n_rel = treino_ids[:, 1].max() + 1
    freq_cauda = np.zeros((n_rel, n_ent))
    freq_cabeca = np.zeros((n_rel, n_ent))
    np.add.at(freq_cauda, (treino_ids[:, 1], treino_ids[:, 2]), 1)
    np.add.at(freq_cabeca, (treino_ids[:, 1], treino_ids[:, 0]), 1)
    return (lambda h, r: freq_cauda[r].copy()), (lambda r, t: freq_cabeca[r].copy())


def escores_aleatorios(n_ent, seed=0):
    rng = np.random.default_rng(seed)
    return (lambda h, r: rng.random(n_ent)), (lambda r, t: rng.random(n_ent))


# ----------------------------------------------------------------------------- avaliação

def posto(escores: np.ndarray, alvo: int, excluir) -> float:
    """Posto da resposta certa entre as candidatas, com empates contados pela média.

    excluir: índices das outras respostas verdadeiras (protocolo filtrado).
    Com empate entre a resposta e k candidatas, o posto é a média entre o otimista e o
    pessimista; assim um modelo que dá o mesmo escore a tudo não ganha posto 1.
    """
    s = escores.astype(float).copy()
    s[list(excluir)] = -np.inf
    s_alvo = s[alvo]
    maiores = np.sum(s > s_alvo)
    empates = np.sum(s == s_alvo) - 1
    return 1 + maiores + empates / 2


def avaliar(teste_ids, conhecidas_ids, f_caudas, f_cabecas) -> np.ndarray:
    """Postos filtrados de cada tripla de teste, prevendo a cauda e a cabeça (2 por tripla)."""
    conhecidas = {tuple(t) for t in conhecidas_ids}
    caudas_de, cabecas_de = {}, {}
    for h, r, t in conhecidas:
        caudas_de.setdefault((h, r), set()).add(t)
        cabecas_de.setdefault((r, t), set()).add(h)
    postos = []
    for h, r, t in teste_ids:
        postos.append(posto(f_caudas(h, r), t, caudas_de.get((h, r), set()) - {t}))
        postos.append(posto(f_cabecas(r, t), h, cabecas_de.get((r, t), set()) - {h}))
    return np.array(postos)


def metricas(postos: np.ndarray) -> dict:
    return {
        "MRR": float(np.mean(1 / postos)),
        "Hits@1": float(np.mean(postos <= 1)),
        "Hits@3": float(np.mean(postos <= 3)),
        "Hits@10": float(np.mean(postos <= 10)),
        "MR": float(np.mean(postos)),
    }


# ----------------------------------------------------------------------------- experimento

def preparar_divisao(g: Graph, seed: int, frac_teste: float = 0.15):
    """Uma rodada do experimento: separa teste e materializa só o que sobrou.

    Devolve (treino_assertado, treino_materializado, teste, deduzidas), em que
    `deduzidas` são as triplas de teste que o raciocinador recupera a partir do treino.
    Elas saem do treino materializado para que a avaliação meça só a parte indutiva.
    """
    ents = individuos(g)
    treino, teste = dividir(triplas_relacionais(g, ents), frac_teste, seed)
    g_treino = Graph()
    for t in g:
        g_treino.add(t)
    for h, r, t in teste:
        g_treino.remove((ARBO[h], ARBO[r], ARBO[t]))
    fecho, _, _ = materializar(g_treino)
    teste_set = set(teste)
    treino_mat = triplas_relacionais(fecho, ents)
    deduzidas = sorted(teste_set & set(treino_mat))
    treino_mat = [x for x in treino_mat if x not in teste_set]
    return treino, treino_mat, teste, deduzidas


def experimento(g: Graph, seeds, cfg: dict, frac_teste: float = 0.15):
    """Roda aleatório, frequência, TransE no grafo assertado e TransE no grafo materializado.

    O filtro do ranking usa o fecho do grafo completo: uma resposta que é verdadeira por
    dedução (por exemplo, ocorreEm Brasil) não conta como erro do modelo.
    Devolve (linhas com métricas por rodada, postos por relação do TransE assertado).
    """
    ents = individuos(g)
    fecho_total, _, _ = materializar(g)
    todas = triplas_relacionais(fecho_total, ents)
    idx = Indice({local(e) for e in ents}, {r for _, r, _ in todas})
    conhecidas = idx.ids(todas)
    linhas, por_relacao = [], {}
    for seed in seeds:
        treino, treino_mat, teste, deduzidas = preparar_divisao(g, seed, frac_teste)
        teste_ids = idx.ids(teste)
        comuns = dict(seed=seed, n_teste=len(teste), n_deduzidas=len(deduzidas))
        modelos = {
            "Aleatório": escores_aleatorios(len(idx.ent), seed),
            "Frequência": escores_frequencia(idx.ids(treino), len(idx.ent)),
        }
        for nome, trs in [("TransE (assertado)", treino), ("TransE (materializado)", treino_mat)]:
            E, R, _ = treinar_transe(idx.ids(trs), len(idx.ent), len(idx.rel), seed=seed, **cfg)
            modelos[nome] = escores_transe(E, R)
        for nome, (fc, fh) in modelos.items():
            postos = avaliar(teste_ids, conhecidas, fc, fh)
            linhas.append({**comuns, "modelo": nome, "n_treino": len(treino_mat if "mater" in nome else treino),
                           **metricas(postos)})
            if nome == "TransE (assertado)":
                for (h, r, t), par in zip(teste, postos.reshape(-1, 2)):
                    por_relacao.setdefault(r, []).extend(par)
    return linhas, por_relacao
