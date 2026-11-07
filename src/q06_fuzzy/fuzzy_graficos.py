"""Figuras da Q6 (controlador fuzzy de irrigação)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

import fuzzy_irrigacao as fi

PASTA_FIGURAS = Path(__file__).parent / "figures"

# Ordem fixa de cores por termo (azul, laranja, verde-água, amarelo, magenta).
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
METODOS = {"centroid": "Centroide", "bisector": "Bissetor", "mom": "Média dos máximos",
           "som": "Menor dos máximos", "lom": "Maior dos máximos"}

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 10,
})


def _br(valor: float) -> str:
    """Número com duas casas e vírgula decimal."""
    return f"{valor:.2f}".replace(".", ",")


def salvar(fig: plt.Figure, nome: str) -> Path:
    """Salva a figura em PNG na pasta ``figures``."""
    PASTA_FIGURAS.mkdir(exist_ok=True)
    caminho = PASTA_FIGURAS / f"{nome}.png"
    fig.savefig(caminho)
    return caminho


def _desenhar_termos(ax: plt.Axes, variavel: str) -> None:
    x = fi.UNIVERSOS[variavel]
    for cor, termo in zip(CORES, fi.TERMOS[variavel]):
        ax.plot(x, fi.funcao_pertinencia(variavel, termo), color=cor, lw=2, label=termo)
    ax.set_xlabel(fi.NOMES[variavel])
    ax.set_ylabel("Grau de pertinência μ")
    ax.set_ylim(-0.03, 1.08)
    ax.legend(loc="center right", fontsize=8, framealpha=0.9)


def figura_pertinencias() -> plt.Figure:
    """Funções de pertinência das três entradas e da saída."""
    fig, axs = plt.subplots(2, 2, figsize=(11, 7))
    for ax, var in zip(axs.flat, (*fi.ENTRADAS, "tempo")):
        _desenhar_termos(ax, var)
        ax.set_title(fi.NOMES[var].split(" (")[0])
    fig.suptitle("Funções de pertinência do controlador de irrigação", fontsize=13)
    fig.tight_layout()
    return fig


def figura_matriz_regras() -> plt.Figure:
    """Base de 27 regras desenhada como três matrizes (uma por nível de chuva)."""
    saidas = list(fi.TERMOS["tempo"])
    cmap = ListedColormap(plt.cm.Blues(np.linspace(0.12, 0.9, len(saidas))))
    norm = BoundaryNorm(np.arange(len(saidas) + 1) - 0.5, len(saidas))
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, chuva in zip(axs, fi.TERMOS["chuva"]):
        m = np.array([[saidas.index(s) for s in linha] for linha in fi.MATRIZ_REGRAS[chuva]])
        ax.imshow(m, cmap=cmap, norm=norm)
        for (i, j), k in np.ndenumerate(m):
            ax.text(j, i, saidas[k], ha="center", va="center", fontsize=9,
                    color="white" if k >= 3 else "#222")
        ax.set_xticks(range(3), list(fi.TERMOS["temperatura"]))
        ax.set_yticks(range(3), list(fi.TERMOS["umidade"]))
        ax.set_xlabel("Temperatura")
        ax.set_ylabel("Umidade do solo")
        ax.set_title(f"Chuva prevista {chuva}")
        ax.grid(False)
    fig.suptitle("Base de regras: tempo de irrigação para cada combinação", fontsize=13)
    fig.tight_layout()
    return fig


def figura_fuzzificacao(entradas: dict[str, float]) -> plt.Figure:
    """Fuzzificação de um caso concreto: valor de cada entrada e seus graus."""
    graus = fi.fuzzificar(**entradas)
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
    for ax, var in zip(axs, fi.ENTRADAS):
        _desenhar_termos(ax, var)
        v = entradas[var]
        ax.axvline(v, color="#444", ls="--", lw=1)
        for cor, (termo, g) in zip(CORES, graus[var].items()):
            if g > 0.005:
                ax.plot(v, g, "o", color=cor, ms=8, mec="white", mew=1.5)
                ax.annotate(_br(g), (v, g), xytext=(6, 4), textcoords="offset points",
                            fontsize=9)
        ax.set_title(f"{var} = {v:g} {fi.UNIDADES[var]}")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8)
    fig.suptitle("Etapa 1: fuzzificação das entradas", fontsize=13)
    fig.tight_layout()
    return fig


def figura_agregacao(resultado: fi.ResultadoMamdani, metodos: bool = True) -> plt.Figure:
    """Conjuntos de saída cortados, agregação por máximo e valores defuzzificados."""
    x = fi.UNIVERSOS["tempo"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.2), sharey=True)
    for cor, termo in zip(CORES, fi.TERMOS["tempo"]):
        axs[0].plot(x, fi.funcao_pertinencia("tempo", termo), color=cor, lw=1, ls=":")
        a = resultado.ativacao[termo]
        if a > 0:
            axs[0].fill_between(x, resultado.cortes[termo], color=cor, alpha=0.3)
            axs[0].plot(x, resultado.cortes[termo], color=cor, lw=2,
                        label=f"{termo} (corte em {_br(a)})")
    axs[0].set_title("Etapa 3: consequentes cortados (implicação min)")
    axs[0].legend(fontsize=8, loc="upper right")
    axs[1].fill_between(x, resultado.agregado, color="#9ec5f4")
    axs[1].plot(x, resultado.agregado, color="#1c5cab", lw=2)
    if metodos:
        for cor, (m, nome) in zip(CORES, METODOS.items()):
            v = fi.defuzzificar(resultado.agregado, m)
            axs[1].axvline(v, color=cor, lw=2, label=f"{nome}: {_br(v)} min")
        axs[1].legend(fontsize=8, loc="upper right")
    axs[1].set_title("Etapas 4 e 5: agregação (max) e defuzzificação")
    for ax in axs:
        ax.set_xlabel(fi.NOMES["tempo"])
    axs[0].set_ylabel("Grau de pertinência μ")
    axs[0].set_ylim(-0.03, 1.08)
    fig.tight_layout()
    return fig


def figura_superficie_3d(chuva: float) -> plt.Figure:
    """Superfície de controle tempo = f(umidade, temperatura) com chuva fixa."""
    X, Y, Z = fi.superficie("umidade", "temperatura", {"chuva": chuva})
    fig = plt.figure(figsize=(9, 6.5))
    ax = fig.add_subplot(projection="3d")
    # vmin abaixo de 0 evita que os tempos mais baixos fiquem brancos e sumam no fundo.
    ax.plot_surface(X, Y, Z, cmap="Blues", vmin=-20, vmax=60, edgecolor="#1c5cab", lw=0.15)
    ax.set_xlabel("Umidade do solo (%)")
    ax.set_ylabel("Temperatura (°C)")
    ax.set_zlabel("Tempo (min)")
    ax.view_init(elev=28, azim=-130)
    ax.set_title(f"Superfície de controle (chuva prevista = {chuva:g} %)")
    return fig


def figura_mapas_calor(pares: list[tuple[str, str, dict[str, float]]]) -> plt.Figure:
    """Mapas de calor da saída para pares de entradas, com a outra entrada fixa."""
    fig, axs = plt.subplots(1, len(pares), figsize=(5.2 * len(pares), 4.6), layout="constrained")
    for ax, (vx, vy, fixo) in zip(np.atleast_1d(axs), pares):
        X, Y, Z = fi.superficie(vx, vy, fixo, n=61)
        im = ax.pcolormesh(X, Y, Z, cmap="Blues", vmin=0, vmax=60, shading="auto")
        cs = ax.contour(X, Y, Z, levels=[10, 20, 30, 40, 50], colors="#333", linewidths=0.7)
        ax.clabel(cs, fmt="%d", fontsize=8)
        ax.set_xlabel(fi.NOMES[vx])
        ax.set_ylabel(fi.NOMES[vy])
        (var, val), = fixo.items()
        ax.set_title(f"{fi.NOMES[var].split(' (')[0]} fixa em {val:g} {fi.UNIDADES[var]}",
                     fontsize=10)
        ax.grid(False)
    fig.colorbar(im, ax=axs, label="Tempo de irrigação (min)", shrink=0.9)
    fig.suptitle("Mapas de calor da saída sobre o espaço de entradas", fontsize=13)
    return fig


def figura_sensibilidade(base: dict[str, float], n: int = 201) -> plt.Figure:
    """Varia uma entrada por vez em todo o universo, mantendo as outras na base."""
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
    for ax, cor, var in zip(axs, CORES, fi.ENTRADAS):
        xs = np.linspace(fi.UNIVERSOS[var][0], fi.UNIVERSOS[var][-1], n)
        ys = [fi.tempo_irrigacao(**{**base, var: x}) for x in xs]
        ax.plot(xs, ys, color=cor, lw=2)
        ax.axvline(base[var], color="#444", ls="--", lw=1)
        ax.set_xlabel(fi.NOMES[var])
        ax.set_title(f"Variando {var}")
    axs[0].set_ylabel("Tempo de irrigação (min)")
    fig.suptitle("Sensibilidade: uma entrada por vez (demais no caso base)", fontsize=13)
    fig.tight_layout()
    return fig


def figura_metodos_defuzz(base: dict[str, float], var: str = "umidade",
                          n: int = 201) -> plt.Figure:
    """Saída de cada método de defuzzificação enquanto ``var`` percorre o universo."""
    xs = np.linspace(fi.UNIVERSOS[var][0], fi.UNIVERSOS[var][-1], n)
    agregados = [fi.inferir(**{**base, var: x}).agregado for x in xs]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for cor, (m, nome) in zip(CORES, METODOS.items()):
        ax.plot(xs, [fi.defuzzificar(a, m) for a in agregados], color=cor, lw=2, label=nome)
    ax.set_xlabel(fi.NOMES[var])
    ax.set_ylabel("Tempo de irrigação (min)")
    outras = ", ".join(f"{k} = {v:g} {fi.UNIDADES[k]}" for k, v in base.items() if k != var)
    ax.set_title(f"Comparação dos métodos de defuzzificação ({outras})")
    ax.legend()
    fig.tight_layout()
    return fig
