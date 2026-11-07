"""Avaliação leave-one-out do sistema CBR sobre a própria base de casos (Q7)."""

from __future__ import annotations

import pandas as pd

from cbr_casos import Caso
from cbr_ciclo import SistemaCBR
from cbr_similaridade import SimSintomas, jaccard_ponderado


def diagnosticos_mais_proximos(sistema: SistemaCBR, caso: Caso, n: int = 3) -> list[str]:
    """Os n diagnósticos distintos na ordem em que aparecem no ranking completo."""
    ranking = sistema.recuperar(caso.problema, k=len(sistema.casos))
    return list(dict.fromkeys(c.diagnostico for c, _ in ranking))[:n]


def avaliar_loo(
    casos: list[Caso], k: int = 3, sim_sintomas: SimSintomas = jaccard_ponderado
) -> pd.DataFrame:
    """Para cada caso, consulta o sistema construído com os demais casos.

    Colunas: caso, real, previsto, confianca, sim_max, acerto_top1 e acerto_top3
    (diagnóstico real entre os três diagnósticos distintos mais próximos).
    """
    linhas = []
    for i, caso in enumerate(casos):
        sistema = SistemaCBR(casos[:i] + casos[i + 1 :], k=k, sim_sintomas=sim_sintomas)
        sugestao = sistema.consultar(caso.problema)
        linhas.append({
            "caso": caso.id,
            "real": caso.diagnostico,
            "previsto": sugestao.diagnostico,
            "confianca": sugestao.confianca,
            "sim_max": sugestao.vizinhos[0][1],
            "acerto_top1": sugestao.diagnostico == caso.diagnostico,
            "acerto_top3": caso.diagnostico in diagnosticos_mais_proximos(sistema, caso),
        })
    return pd.DataFrame(linhas)
