"""Similaridade local-global entre problemas clínicos (Q7).

Cada atributo tem uma similaridade local em [0, 1]; a similaridade global é a
média ponderada das locais pelos pesos de PESOS_ATRIBUTOS.
"""

from __future__ import annotations

from functools import partial
from typing import Callable

from cbr_casos import Problema

# Peso de cada sintoma conforme o quanto ele ajuda a separar doenças na base:
# 1 = inespecífico (aparece em várias doenças), 2 = aponta um grupo de doenças,
# 3 = quase exclusivo de uma doença da base.
PESOS_SINTOMAS: dict[str, float] = {
    "dor_cabeca": 1, "mialgia": 1, "cansaco": 1, "calafrios": 1, "nauseas": 1,
    "vomito": 1, "dor_abdominal": 1, "tosse": 1, "dor_garganta": 1, "congestao_nasal": 1,
    "artralgia": 2, "exantema": 2, "prurido": 2, "conjuntivite": 2, "diarreia": 2,
    "coriza": 2, "espirros": 2, "linfonodos_cervicais": 2, "falta_ar": 2,
    "dor_retroorbital": 3, "edema_articular": 3, "petequias": 3,
    "placas_amigdalas": 3, "anosmia": 3,
}

# Os sintomas carregam a maior parte da informação diagnóstica; a temperatura
# separa quadros febris (dengue, influenza) dos afebris (resfriado, zika); início
# e duração ajudam em pares como influenza x COVID-19; a idade pesa pouco.
PESOS_ATRIBUTOS: dict[str, float] = {
    "sintomas": 0.60,
    "temperatura": 0.15,
    "inicio": 0.10,
    "dias_sintomas": 0.10,
    "idade": 0.05,
}

# Amplitude usada para normalizar a diferença de cada atributo numérico.
AMPLITUDES: dict[str, float] = {"temperatura": 5.0, "dias_sintomas": 14.0, "idade": 100.0}

SimSintomas = Callable[[dict[str, int], dict[str, int]], float]


def sim_numerica(a: float, b: float, amplitude: float) -> float:
    """1 - |a - b| / amplitude, limitada a [0, 1]."""
    return max(0.0, 1.0 - abs(a - b) / amplitude)


def sim_simbolica(a: str, b: str) -> float:
    """Igualdade simples entre valores simbólicos."""
    return 1.0 if a == b else 0.0


def jaccard_simples(a: dict[str, int], b: dict[str, int]) -> float:
    """|A ∩ B| / |A ∪ B| sobre os sintomas presentes, ignorando intensidade."""
    uniao = a.keys() | b.keys()
    return len(a.keys() & b.keys()) / len(uniao) if uniao else 1.0


def jaccard_ponderado(
    a: dict[str, int], b: dict[str, int], pesos: dict[str, float] | None = PESOS_SINTOMAS
) -> float:
    """Jaccard ponderado: Σ w·min(a, b) / Σ w·max(a, b), com intensidade 0 se ausente.

    Com ``pesos=None`` todos os sintomas pesam 1 (só a intensidade conta).
    """
    uniao = a.keys() | b.keys()
    if not uniao:
        return 1.0
    w = pesos or {}
    num = sum(w.get(s, 1.0) * min(a.get(s, 0), b.get(s, 0)) for s in uniao)
    den = sum(w.get(s, 1.0) * max(a.get(s, 0), b.get(s, 0)) for s in uniao)
    return num / den


METRICAS_SINTOMAS: dict[str, SimSintomas] = {
    "simples": jaccard_simples,
    "intensidade": partial(jaccard_ponderado, pesos=None),
    "ponderada": jaccard_ponderado,
}


def similaridades_locais(
    p: Problema, q: Problema, sim_sintomas: SimSintomas = jaccard_ponderado
) -> dict[str, float]:
    """Similaridade local de cada atributo entre dois problemas."""
    return {
        "sintomas": sim_sintomas(p.sintomas, q.sintomas),
        "temperatura": sim_numerica(p.temperatura, q.temperatura, AMPLITUDES["temperatura"]),
        "inicio": sim_simbolica(p.inicio, q.inicio),
        "dias_sintomas": sim_numerica(p.dias_sintomas, q.dias_sintomas, AMPLITUDES["dias_sintomas"]),
        "idade": sim_numerica(p.idade, q.idade, AMPLITUDES["idade"]),
    }


def similaridade(
    p: Problema,
    q: Problema,
    sim_sintomas: SimSintomas = jaccard_ponderado,
    pesos: dict[str, float] = PESOS_ATRIBUTOS,
) -> float:
    """Similaridade global: média ponderada das similaridades locais."""
    locais = similaridades_locais(p, q, sim_sintomas)
    return sum(pesos[a] * v for a, v in locais.items()) / sum(pesos.values())
