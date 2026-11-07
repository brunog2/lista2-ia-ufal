"""Q10: BFS, DFS, UCS e A* em busca em grafo, com registro do trace completo.

Convenções (todas mudam a ordem de expansão, por isso ficam explícitas):

* Busca em grafo (AIMA 3a ed., fig. 3.7): há conjunto de explorados, e um
  filho só entra na fronteira se não estiver nem nela nem nos explorados.
* Sucessores gerados na ordem de ``problema.acoes`` (alfabética aqui).
* BFS testa o objetivo na geração do filho, como no AIMA (fig. 3.11).
  DFS, UCS e A* testam na expansão, isto é, quando o nó sai da fronteira.
* DFS empilha os filhos em ordem inversa, para que o primeiro em ordem
  alfabética seja o próximo a sair da pilha.
* UCS e A*: se um estado já está na fronteira e surge um caminho com g menor,
  a entrada é substituída (recebe novo número de inserção).
* Desempate na fila de prioridade: ordem de inserção (FIFO). Com
  ``desempate_por_h=True`` o critério vira (f, h, inserção).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Callable

from q10_problema import Problema


@dataclass(eq=False)  # identidade: fronteira.remove não deve comparar a cadeia de pais
class No:
    estado: object
    pai: "No | None" = None
    g: float = 0
    h: float = 0
    ordem: int = 0  # contador de inserção na fronteira, usado no desempate

    @property
    def f(self):
        return self.g + self.h

    def caminho(self) -> list:
        no, estados = self, []
        while no:
            estados.append(no.estado)
            no = no.pai
        return estados[::-1]


@dataclass
class Passo:
    """Uma iteração: o nó retirado da fronteira e o estado após processá-lo."""
    numero: int
    estado: object
    g: float
    h: float
    gerados: list[tuple[object, float, str]]  # (estado filho, g, o que aconteceu)
    fronteira: list[No]  # na ordem em que sairiam
    explorados: list


@dataclass
class Resultado:
    algoritmo: str
    problema: Problema
    solucao: No | None
    passos: list[Passo] = field(default_factory=list)
    expandidos: int = 0  # nós cujos sucessores foram gerados
    gerados: int = 1  # nós criados, contando a raiz

    @property
    def rota(self) -> list:
        return self.solucao.caminho() if self.solucao else []

    @property
    def custo(self):
        return self.solucao.g if self.solucao else None

    @property
    def ordem_expansao(self) -> list:
        """Estados retirados da fronteira, na ordem. Quando o teste é na
        expansão, o último é o objetivo (retirado, mas não expandido)."""
        return [p.estado for p in self.passos]

    def rota_str(self) -> str:
        return " → ".join(self.problema.rotulo(s) for s in self.rota)


def _busca_em_grafo(problema: Problema, algoritmo: str, disciplina: str,
                    h: Callable = lambda s: 0, teste_na_geracao=False,
                    desempate_por_h=False) -> Resultado:
    """Núcleo comum. ``disciplina``: 'fila' (FIFO), 'pilha' (LIFO) ou 'prioridade'."""
    contador = count()
    raiz = No(problema.inicial, h=h(problema.inicial), ordem=next(contador))
    res = Resultado(algoritmo, problema, None)
    if teste_na_geracao and problema.eh_objetivo(raiz.estado):
        res.solucao = raiz
        return res

    def chave(no):
        return (no.f, no.h, no.ordem) if desempate_por_h else (no.f, no.ordem)

    def ordem_de_saida(fronteira):
        if disciplina == "fila":
            return list(fronteira)
        if disciplina == "pilha":
            return fronteira[::-1]
        return sorted(fronteira, key=chave)

    fronteira: list[No] = [raiz]
    explorados: list = []
    # shortcut: fronteira em lista com busca linear O(n); para grafos grandes usar heap + dict.
    while fronteira:
        no = ordem_de_saida(fronteira)[0]
        fronteira.remove(no)
        passo = Passo(len(res.passos) + 1, no.estado, no.g, no.h, [], [], [])
        res.passos.append(passo)

        if not teste_na_geracao and problema.eh_objetivo(no.estado):
            res.solucao = no
            passo.fronteira, passo.explorados = ordem_de_saida(fronteira), list(explorados)
            return res

        explorados.append(no.estado)
        res.expandidos += 1
        filhos = []
        for acao in problema.acoes(no.estado):
            s = problema.resultado(no.estado, acao)
            g = no.g + problema.custo_acao(no.estado, acao, s)
            filhos.append(No(s, no, g, h(s)))
        res.gerados += len(filhos)

        if disciplina == "pilha":
            filhos.reverse()  # o primeiro na ordem alfabética fica no topo
        for filho in filhos:
            na_fronteira = next((n for n in fronteira if n.estado == filho.estado), None)
            if filho.estado in explorados:
                status = "explorado"
            elif na_fronteira is None:
                filho.ordem = next(contador)
                fronteira.append(filho)
                status = "novo"
                if teste_na_geracao and problema.eh_objetivo(filho.estado):
                    passo.gerados.append((filho.estado, filho.g, "objetivo"))
                    passo.fronteira, passo.explorados = ordem_de_saida(fronteira), list(explorados)
                    res.solucao = filho
                    return res
            elif disciplina == "prioridade" and filho.g < na_fronteira.g:
                fronteira.remove(na_fronteira)
                filho.ordem = next(contador)
                fronteira.append(filho)
                status = f"atualizado (g {na_fronteira.g}→{filho.g})"
            else:
                status = "já na fronteira"
            passo.gerados.append((filho.estado, filho.g, status))
        if disciplina == "pilha":
            passo.gerados.reverse()  # exibe na ordem de geração
        passo.fronteira, passo.explorados = ordem_de_saida(fronteira), list(explorados)
    return res


def bfs(problema: Problema, teste_na_geracao=True) -> Resultado:
    """Busca em largura (fila FIFO)."""
    return _busca_em_grafo(problema, "BFS", "fila", teste_na_geracao=teste_na_geracao)


def dfs(problema: Problema) -> Resultado:
    """Busca em profundidade (pilha LIFO), teste na expansão."""
    return _busca_em_grafo(problema, "DFS", "pilha")


def ucs(problema: Problema, desempate_por_h=False) -> Resultado:
    """Busca de custo uniforme: prioridade g(n)."""
    return _busca_em_grafo(problema, "UCS", "prioridade", desempate_por_h=desempate_por_h)


def a_estrela(problema: Problema, h: Callable, desempate_por_h=False) -> Resultado:
    """A*: prioridade f(n) = g(n) + h(n)."""
    return _busca_em_grafo(problema, "A*", "prioridade", h=h, desempate_por_h=desempate_por_h)


# ------------------------------------------------------- análise de heurística

def estados_alcancaveis(problema: Problema) -> list:
    vistos, pilha = [problema.inicial], [problema.inicial]
    while pilha:
        s = pilha.pop()
        for a in problema.acoes(s):
            t = problema.resultado(s, a)
            if t not in vistos:
                vistos.append(t)
                pilha.append(t)
    return vistos


def custo_otimo(problema: Problema, estado):
    """h*(estado): custo ótimo até o objetivo, obtido com UCS."""
    return ucs(problema.com_inicial(estado)).custo


def verificar_heuristica(problema: Problema, h: Callable) -> dict:
    """Confere admissibilidade (h <= h*) e consistência (h(s) <= c + h(s'))
    em todos os estados alcançáveis a partir do estado inicial."""
    estados = estados_alcancaveis(problema)
    tabela = [(s, h(s), custo_otimo(problema, s)) for s in estados]
    nao_admissiveis = [(s, hs, hx) for s, hs, hx in tabela if hx is not None and hs > hx]
    inconsistentes = []
    for s in estados:
        for a in problema.acoes(s):
            t = problema.resultado(s, a)
            c = problema.custo_acao(s, a, t)
            if h(s) > c + h(t):
                inconsistentes.append((s, t, h(s), c, h(t)))
    return {"tabela": tabela, "nao_admissiveis": nao_admissiveis,
            "inconsistentes": inconsistentes,
            "admissivel": not nao_admissiveis, "consistente": not inconsistentes}


# ----------------------------------------------------------------- relatórios

def tabela_trace(res: Resultado) -> str:
    """Trace em Markdown, uma linha por nó retirado da fronteira.

    Na fronteira, UCS mostra g entre parênteses e A* mostra f; BFS e DFS
    mostram só o estado, na ordem em que sairiam."""
    p, a_est = res.problema, res.algoritmo == "A*"

    def item_fronteira(no):
        if a_est:
            return f"{p.rotulo(no.estado)}({no.f:g})"
        if res.algoritmo == "UCS":
            return f"{p.rotulo(no.estado)}({no.g:g})"
        return p.rotulo(no.estado)

    colunas = ["Passo", "Retirado", "g"] + (["h", "f"] if a_est else []) + \
        ["Sucessores gerados", "Fronteira depois", "Explorados"]
    linhas = ["| " + " | ".join(colunas) + " |", "|" + " --- |" * len(colunas)]
    for passo in res.passos:
        gerados = ", ".join(f"{p.rotulo(s)}[{g:g}]" + ("" if st == "novo" else f" {st}")
                            for s, g, st in passo.gerados)
        if not passo.gerados and res.solucao is not None and passo is res.passos[-1]:
            gerados = "objetivo, para"
        cel = [str(passo.numero), p.rotulo(passo.estado), f"{passo.g:g}"]
        if a_est:
            cel += [f"{passo.h:g}", f"{passo.g + passo.h:g}"]
        cel += [gerados or "(nenhum)",
                " ".join(item_fronteira(n) for n in passo.fronteira) or "∅",
                ", ".join(p.rotulo(s) for s in passo.explorados) or "∅"]
        linhas.append("| " + " | ".join(cel) + " |")
    return "\n".join(linhas)


def resumo(res: Resultado) -> dict:
    return {"algoritmo": res.algoritmo, "rota": res.rota_str(), "custo": res.custo,
            "expandidos": res.expandidos, "gerados": res.gerados,
            "ordem": " ".join(res.problema.rotulo(s) for s in res.ordem_expansao)}
