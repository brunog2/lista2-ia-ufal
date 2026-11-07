"""Figuras das Questões 9 e 15 (hierarquias, grafo de propriedades, cadeias)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from owlready2 import Ontology, Thing, ThingClass

PASTA_FIGURAS = Path(__file__).resolve().parent / "figures"
SUPERFICIE, TEXTO, TEXTO_2, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#c9c8c2"
AZUL, LARANJA, VERDE = "#2a78d6", "#eb6834", "#1baf7a"  # slots 1-3 da paleta categórica

plt.rcParams.update({"figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
                     "font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXTO,
                     "savefig.dpi": 150, "savefig.bbox": "tight"})


def pais_diretos(onto: Ontology) -> dict[str, set[str]]:
    """Superclasses nomeadas diretas de cada classe no estado atual do World."""
    return {c.name: {p.name for p in c.is_a if isinstance(p, ThingClass) and p is not Thing}
            for c in onto.classes()}


def _fecho(pais: dict[str, set[str]], c: str) -> set[str]:
    acc: set[str] = set()
    for p in pais.get(c, ()):
        acc |= {p} | _fecho(pais, p)
    return acc


def desenhar_hierarquia(ax, pais: dict[str, set[str]], titulo: str,
                        referencia: dict[str, set[str]] | None = None) -> None:
    """Árvore indentada; arestas ausentes no fecho de ``referencia`` saem em laranja."""
    filhos: dict[str, list[str]] = {}
    for c, ps in pais.items():
        for p in ps or {"Thing"}:
            filhos.setdefault(p, []).append(c)
    linhas: list[tuple[int, str, str, int]] = []  # (nível, classe, pai, linha do pai)

    def visitar(no: str, nivel: int, pai: str, linha_pai: int) -> None:
        linhas.append((nivel, no, pai, linha_pai))
        minha = len(linhas) - 1
        for f in sorted(filhos.get(no, [])):
            visitar(f, nivel + 1, no, minha)

    visitar("Thing", 0, "", -1)
    vistos: set[str] = set()
    for n, (nivel, no, pai, linha_pai) in enumerate(linhas):
        y, x = -n, nivel * 0.6
        novo = referencia is not None and pai not in ("", "Thing") and pai not in _fecho(referencia, no)
        repetido = no in vistos
        vistos.add(no)
        cor = LARANJA if novo else TEXTO_2
        if linha_pai >= 0:
            xp = linhas[linha_pai][0] * 0.6
            ax.plot([xp + 0.15, xp + 0.15, x], [-linha_pai - 0.3, y, y], color=cor, lw=2 if novo else 1)
        ax.text(x + 0.05, y, no, va="center", fontsize=8,
                color=LARANJA if novo else (TEXTO_2 if repetido else TEXTO),
                style="italic" if repetido else "normal", fontweight="bold" if novo else "normal")
    ax.set_title(titulo, loc="left", fontsize=11, color=TEXTO)
    ax.set_xlim(-0.2, 6.5)
    ax.set_ylim(-len(linhas), 1)
    ax.axis("off")


def figura_hierarquias(declarada: dict[str, set[str]], inferida: dict[str, set[str]],
                       arquivo: str) -> Path:
    """Hierarquia declarada e inferida lado a lado."""
    altura = 0.21 * (max(len(declarada), len(inferida)) + 8)
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, altura))
    desenhar_hierarquia(a, declarada, "Hierarquia declarada (antes do reasoner)")
    desenhar_hierarquia(b, inferida, "Hierarquia inferida pelo HermiT (laranja = subsunção nova)",
                        referencia=declarada)
    fig.text(0.5, 0.005, "Itálico cinza: a classe aparece de novo por ter mais de uma superclasse.",
             ha="center", color=TEXTO_2)
    return _salvar(fig, arquivo)


def _caixa(ax, x: float, y: float, texto: str):
    return ax.text(x, y, texto, ha="center", va="center", fontsize=8.5, color=TEXTO, zorder=3,
                   bbox=dict(boxstyle="round,pad=0.4", fc="#eef4fc", ec=AZUL, lw=1.2))


def _recuo(caixa, dx: float, dy: float) -> float:
    """Distância, em pontos, do centro da caixa até a borda na direção (dx, dy)."""
    ext = caixa.get_bbox_patch().get_window_extent()
    escala = 72 / caixa.figure.dpi
    w, h = ext.width * escala / 2, ext.height * escala / 2
    return min(w / abs(dx) if dx else float("inf"), h / abs(dy) if dy else float("inf")) + 3


def _seta(ax, origem, destino, cor: str, tracejada: bool = False, rad: float = 0.0):
    """Seta entre duas caixas de texto, começando e terminando nas bordas."""
    (x0, y0), (x1, y1) = (ax.transData.transform(c.get_position()) for c in (origem, destino))
    norma = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    dx, dy = (x1 - x0) / norma, (y1 - y0) / norma
    ax.annotate("", xy=destino.get_position(), xytext=origem.get_position(), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=cor, lw=1.4, linestyle="--" if tracejada else "-",
                                shrinkA=_recuo(origem, dx, dy), shrinkB=_recuo(destino, dx, dy),
                                connectionstyle=f"arc3,rad={rad}"))


def _rotulo_aresta(ax, x: float, y: float, texto: str, cor: str = TEXTO) -> None:
    ax.text(x, y, texto, ha="center", va="center", fontsize=7.5, color=cor, zorder=4,
            bbox=dict(boxstyle="round,pad=0.15", fc=SUPERFICIE, ec="none"))


def figura_grafo_propriedades(onto: Ontology, arquivo: str) -> Path:
    """Classes principais, propriedades de dados (na caixa) e de objeto (setas)."""
    pos = {"Usuario": (0, 0), "AtividadeFisica": (5, 0), "Objetivo": (2.5, 3.2),
           "Beneficio": (7.5, 3.2), "CondicaoDeSaude": (2.5, -3.2), "ParteDoCorpo": (7.5, -3.2),
           "Local": (10.5, 0), "NivelDeImpacto": (10, 2.0), "NivelTecnico": (10, -2.0)}
    dados: dict[str, list[str]] = {}
    for p in onto.data_properties():
        dados.setdefault(p.domain[0].name, []).append(p.name)
    fig, ax = plt.subplots(figsize=(13, 8))
    caixas = {n: _caixa(ax, x, y, n + "".join(f"\n· {d}" for d in dados.get(n, [])))
              for n, (x, y) in pos.items()}
    fig.canvas.draw()  # posiciona as caixas antes de recortar as setas
    arestas: dict[tuple[str, str], list[str]] = {}
    for p in onto.object_properties():
        if p.domain and p.range:
            arestas.setdefault((p.domain[0].name, p.range[0].name), []).append(
                p.name + (" *" if p.property_chain else ""))
    for (u, v), nomes in arestas.items():
        cor = LARANJA if all(n.endswith("*") for n in nomes) else TEXTO_2
        if u == v:
            x, y = pos[u]
            ax.annotate("", xy=(x + 0.45, y - 0.3), xytext=(x - 0.45, y - 0.3),
                        arrowprops=dict(arrowstyle="-|>", color=cor, lw=1.4,
                                        connectionstyle="arc3,rad=1.0"))
            _rotulo_aresta(ax, x, y - 1.05, "\n".join(nomes))
            continue
        _seta(ax, caixas[u], caixas[v], cor, tracejada=cor == LARANJA)
        (x0, y0), (x1, y1) = pos[u], pos[v]
        _rotulo_aresta(ax, (x0 + x1) / 2, (y0 + y1) / 2, "\n".join(nomes))
    ax.set_title("Grafo de propriedades (domínio → imagem). Laranja tracejado e *: propriedade "
                 "definida por cadeia", loc="left", fontsize=11)
    ax.set_xlim(-1.8, 11.8)
    ax.set_ylim(-4.6, 4.2)
    ax.axis("off")
    return _salvar(fig, arquivo)


def figura_contraindicacoes(onto: Ontology, usuarios: list, sobrecarga_declarada: dict,
                            arquivo: str) -> Path:
    """Fatos declarados (cinza) e naoDevePraticar deduzida pelo HermiT (laranja)."""
    condicoes = [c for u in usuarios for c in u.temCondicao]
    atividades = sorted({a for u in usuarios for a in u.naoDevePraticar}, key=lambda a: a.name)
    afetadas = {p for c in condicoes for p in c.afeta}
    partes = sorted(afetadas | {q for a in atividades for q in sobrecarga_declarada[a]
                                if set(q.INDIRECT_parteDe) & afetadas}, key=lambda p: p.name)
    colunas = [usuarios, condicoes, partes, atividades]
    altura = max(map(len, colunas))
    pos = {ind: (x * 3.4, (len(col) - 1) / 2 - i) for x, col in enumerate(colunas)
           for i, ind in enumerate(col)}
    fig, ax = plt.subplots(figsize=(13, 0.75 * altura + 2))
    caixas = {ind: _caixa(ax, x, y, str(ind.label[0])) for ind, (x, y) in pos.items()}
    fig.canvas.draw()

    def ligar(a, b, texto: str, cor: str = TEXTO_2, tracejada: bool = False, rad: float = 0.0):
        _seta(ax, caixas[a], caixas[b], cor, tracejada, rad)
        if texto:
            (x0, y0), (x1, y1) = pos[a], pos[b]
            _rotulo_aresta(ax, (x0 + x1) / 2, (y0 + y1) / 2, texto, cor)

    for u in usuarios:
        for c in u.temCondicao:
            ligar(u, c, "")
        for a in u.naoDevePraticar:
            ligar(u, a, "", LARANJA, tracejada=True, rad=0.18 if pos[a][1] < pos[u][1] else -0.18)
    for c in condicoes:
        for p in c.afeta:
            ligar(c, p, "")
    for p in partes:
        for q in p.parteDe:
            if q in caixas:
                ligar(p, q, "parteDe", rad=0.6)
    for a in atividades:
        for p in sobrecarga_declarada[a]:
            if p in caixas:
                ligar(a, p, "")
    topo = max(y for _, y in pos.values()) + 1
    for x, cabecalho in enumerate(["Usuário  —temCondicao→", "Condição  —afeta→", "Parte do corpo",
                                     "←sobrecarrega—  Atividade"]):
        ax.text(x * 3.4, topo, cabecalho, ha="center", fontsize=10, color=TEXTO_2, fontweight="bold")
    ax.plot([], [], color=TEXTO_2, label="fato declarado")
    ax.plot([], [], color=LARANJA, ls="--", label="naoDevePraticar (deduzida pelo HermiT)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=False)
    ax.set_title("Contraindicações deduzidas pelas cadeias sobrecarrega ∘ afetadaPor e "
                 "temCondicao ∘ contraindica", loc="left", fontsize=11)
    ax.set_xlim(-1.5, 3 * 3.4 + 1.5)
    ax.set_ylim(-altura / 2 - 0.5, topo + 0.5)
    ax.axis("off")
    return _salvar(fig, arquivo)


def _salvar(fig, arquivo: str) -> Path:
    PASTA_FIGURAS.mkdir(exist_ok=True)
    destino = PASTA_FIGURAS / arquivo
    fig.savefig(destino)
    plt.close(fig)
    return destino
