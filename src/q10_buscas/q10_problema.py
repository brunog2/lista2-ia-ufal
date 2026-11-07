"""Q10: dados do mapa de entregas e formulação como problema de busca.

O mapa é um grafo não direcionado com nove localidades (A a I) e custos em
minutos. Duas formulações são oferecidas:

* ``ProblemaRota``: estado = localidade atual; objetivo = chegar a I.
* ``ProblemaRotaDF``: estado = (localidade, visitouD, visitouF); objetivo =
  estar em I depois de ter passado por D e por F, em qualquer ordem.

As ações de um estado são "ir para o vizinho X", geradas em ordem alfabética
do nome do vizinho. Essa ordem é uma convenção e muda o trace das buscas.
"""

from __future__ import annotations

import copy
import heapq
from itertools import count

TRECHOS = [
    ("A", "B", 4), ("A", "D", 3),
    ("B", "C", 5), ("B", "E", 2),
    ("C", "F", 2), ("D", "E", 4),
    ("D", "G", 6), ("E", "F", 3),
    ("E", "H", 5), ("F", "I", 4),
    ("G", "H", 3), ("H", "I", 2),
]

H_ENUNCIADO = {"A": 10, "B": 8, "C": 6, "D": 9, "E": 6, "F": 4, "G": 5, "H": 2, "I": 0}

INICIO, DESTINO = "A", "I"


def montar_grafo(trechos=TRECHOS) -> dict[str, dict[str, int]]:
    """Lista de adjacência simétrica: grafo[u][v] = custo do trecho u-v."""
    grafo: dict[str, dict[str, int]] = {}
    for u, v, c in trechos:
        grafo.setdefault(u, {})[v] = c
        grafo.setdefault(v, {})[u] = c
    return grafo


GRAFO = montar_grafo()


def dijkstra(grafo: dict[str, dict[str, int]], origem: str) -> dict[str, int]:
    """Menor distância de ``origem`` a cada nó. Como o grafo é não direcionado,
    ``dijkstra(GRAFO, 'I')`` dá o custo ótimo h*(n) de cada nó até I."""
    dist = {origem: 0}
    heap, desempate = [(0, next(count()), origem)], count(1)
    while heap:
        d, _, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, c in grafo[u].items():
            if d + c < dist.get(v, float("inf")):
                dist[v] = d + c
                heapq.heappush(heap, (d + c, next(desempate), v))
    return dist


class Problema:
    """Interface de problema de busca no estilo do AIMA (cap. 3)."""

    def __init__(self, inicial):
        self.inicial = inicial

    def acoes(self, estado):
        raise NotImplementedError

    def resultado(self, estado, acao):
        raise NotImplementedError

    def custo_acao(self, estado, acao, novo_estado) -> float:
        raise NotImplementedError

    def eh_objetivo(self, estado) -> bool:
        raise NotImplementedError

    def rotulo(self, estado) -> str:
        return str(estado)

    def com_inicial(self, estado) -> "Problema":
        """Cópia do problema começando em outro estado (usada para calcular h*)."""
        outro = copy.copy(self)
        outro.inicial = estado
        return outro


class ProblemaRota(Problema):
    """Estado: localidade atual. Ação: ir para um vizinho. Custo: minutos do trecho."""

    def __init__(self, grafo=GRAFO, inicial=INICIO, destino=DESTINO):
        super().__init__(inicial)
        self.grafo, self.destino = grafo, destino

    def acoes(self, estado):
        return sorted(self.grafo[estado])

    def resultado(self, estado, acao):
        return acao

    def custo_acao(self, estado, acao, novo_estado):
        return self.grafo[estado][acao]

    def eh_objetivo(self, estado):
        return estado == self.destino


class ProblemaRotaDF(Problema):
    """Variante com paradas obrigatórias em D e F antes de I.

    Estado: tupla (no, visitouD, visitouF). Passar por I antes de cumprir as
    paradas é permitido, só não encerra a busca (não afeta o ótimo deste mapa).
    """

    def __init__(self, grafo=GRAFO, inicio=INICIO, destino=DESTINO, paradas=("D", "F")):
        self.grafo, self.destino, self.paradas = grafo, destino, paradas
        super().__init__(self._marcar(inicio, (False,) * len(paradas)))

    def _marcar(self, no, flags):
        return (no, *(f or no == p for f, p in zip(flags, self.paradas)))

    def acoes(self, estado):
        return sorted(self.grafo[estado[0]])

    def resultado(self, estado, acao):
        return self._marcar(acao, estado[1:])

    def custo_acao(self, estado, acao, novo_estado):
        return self.grafo[estado[0]][acao]

    def eh_objetivo(self, estado):
        return estado[0] == self.destino and all(estado[1:])

    def rotulo(self, estado):
        return f"({estado[0]},{','.join(str(int(f)) for f in estado[1:])})"


# ---------------------------------------------------------------- heurísticas

def h_enunciado(estado) -> int:
    """h(n) dada no enunciado. Para estados aumentados usa só a localidade."""
    no = estado[0] if isinstance(estado, tuple) else estado
    return H_ENUNCIADO[no]


def h_nula(estado) -> int:
    return 0


def criar_h_paradas(grafo=GRAFO, paradas=("D", "F"), h_base=H_ENUNCIADO):
    """Heurística proposta para a variante D/F.

    h_DF(n, flags) = max( h(n),  max_{m pendente} [ d(n, m) + h(m) ] )

    d(n, m) é a menor distância no grafo original (Dijkstra a partir de cada
    parada). Toda rota válida ainda precisa ir de n até a parada pendente m e
    depois de m até I, logo custa pelo menos d(n, m) + h*(m) >= d(n, m) + h(m).
    """
    dist = {m: dijkstra(grafo, m) for m in paradas}

    def h_df(estado):
        no, flags = estado[0], estado[1:]
        termos = [h_base[no]]
        termos += [dist[m][no] + h_base[m] for m, feito in zip(paradas, flags) if not feito]
        return max(termos)

    return h_df
