"""Gráfico de Gantt do plano produzido por ``explicacao.explicar``."""
from __future__ import annotations

import matplotlib.pyplot as plt

from planejador import hhmm_para_min, min_para_hhmm

# paleta categórica em ordem fixa (cor acompanha a atividade, não a posição no plano)
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
TINTA, TINTA_SECUNDARIA, GRADE = "#0b0b0b", "#52514e", "#e4e3df"


def desenhar_gantt(resumo: dict, titulo: str = "", ax=None, caminho: str | None = None):
    atividades = resumo["atividades"]
    inicio, fim = hhmm_para_min(resumo["janela"]["inicio"]), hhmm_para_min(resumo["janela"]["fim"])
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 0.55 * len(atividades) + 1.4))
    ax.set_facecolor("#fcfcfb")
    for linha, a in enumerate(atividades):
        y = len(atividades) - 1 - linha
        cor = CORES[linha % len(CORES)]
        for b in a["blocos"]:
            x0, x1 = hhmm_para_min(b["inicio"]), hhmm_para_min(b["fim"])
            ax.barh(y, x1 - x0, left=x0, height=0.6, color=cor, edgecolor="white", linewidth=2,
                    hatch="//" if a["status"] == "fixa" else None)
            ax.text((x0 + x1) / 2, y, f"{b['inicio']}-{b['fim']}", ha="center", va="center", fontsize=8, color=TINTA)
        if a["status"] == "fora":
            ax.text(inicio + 5, y, "fora do plano", va="center", fontsize=8, color=TINTA_SECUNDARIA, style="italic")
        elif a["status"] == "parcial":
            ultimo = hhmm_para_min(a["blocos"][-1]["fim"])
            ax.text(min(ultimo + 4, fim - 2), y + 0.38, f"{a['minutos']}/{a['duracao']} min", fontsize=7.5,
                    color=TINTA_SECUNDARIA, ha="right" if ultimo + 4 >= fim - 2 else "left")
    ax.set_yticks(range(len(atividades)))
    ax.set_yticklabels([f"{a['id']}  {a['nome']}" for a in reversed(atividades)], fontsize=9, color=TINTA)
    marcas = range(inicio - inicio % 60 + (60 if inicio % 60 else 0), fim + 1, 60)
    ax.set_xticks(list(marcas))
    ax.set_xticklabels([min_para_hhmm(m) for m in marcas], fontsize=8.5, color=TINTA_SECUNDARIA)
    ax.set_xlim(inicio, fim)
    ax.set_ylim(-0.6, len(atividades) - 0.4)
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRADE)
    ax.tick_params(length=0)
    u = f"{resumo['utilidade']:.2f}".replace(".", ",")
    ax.set_title(f"{titulo}  (U = {u})" if titulo else f"U = {u}", fontsize=10, loc="left", color=TINTA)
    if caminho:
        ax.figure.tight_layout()
        ax.figure.savefig(caminho, dpi=150, bbox_inches="tight")
    return ax
