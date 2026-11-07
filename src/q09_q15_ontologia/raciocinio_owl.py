"""Execução dos reasoners HermiT e Pellet sobre a ontologia (Questões 9 e 15).

O HermiT 1.3.8 é chamado pelo owlready2 (o Protégé 5.6 traz o 1.4.3). O Pellet
2.3.1 que acompanha o owlready2 0.51 falha no Java 21 quando usa o carregador
Jena (``sync_reasoner_pellet``): três classes do jar ``jena-arq-fixed`` foram
compiladas para Java 25. Por isso o Pellet é chamado aqui pela linha de comando
com ``--loader OWLAPIv3``, que não passa por essas classes.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import owlready2
from owlready2 import Ontology, Thing, ThingClass, World, sync_reasoner_hermit

from ontologia_atividades import ARQUIVO_OWL

_PELLET_JARS = sorted((Path(owlready2.__file__).parent / "pellet").glob("*.jar"))
_LINHA_TAXONOMIA = re.compile(r"^( *)(\S+)(?: = (\S+))?(?: - \((.*)\))?$")


@dataclass
class Classificacao:
    """Resultado comparável de classificação + realização."""

    superclasses: dict[str, set[str]] = field(default_factory=dict)
    tipos: dict[str, set[str]] = field(default_factory=dict)
    insatisfaziveis: set[str] = field(default_factory=set)
    segundos: float = 0.0


def carregar_ontologia(caminho: Path = ARQUIVO_OWL) -> tuple[World, Ontology]:
    """Carrega o arquivo .owl num World isolado."""
    world = World()
    onto = world.get_ontology(Path(caminho).resolve().as_uri()).load()
    return world, onto


def raciocinar_hermit(world: World) -> float:
    """Classifica, realiza e infere valores de propriedades; devolve o tempo em s."""
    inicio = time.perf_counter()
    sync_reasoner_hermit(world, infer_property_values=True, debug=0)
    return time.perf_counter() - inicio


def _local(iri: str) -> str:
    return iri.rsplit("#", 1)[-1]


def classificacao_hermit(caminho: Path = ARQUIVO_OWL) -> Classificacao:
    """Hierarquia inferida e tipos de cada indivíduo segundo o HermiT."""
    world, onto = carregar_ontologia(caminho)
    segundos = raciocinar_hermit(world)
    resultado = Classificacao(segundos=segundos)
    insatisfaziveis = set(world.inconsistent_classes()) - {owlready2.Nothing}
    resultado.insatisfaziveis = {c.name for c in insatisfaziveis}
    for c in onto.classes():
        if c not in insatisfaziveis:
            resultado.superclasses[c.name] = {a.name for a in c.ancestors() if a not in (c, Thing)}
    for i in onto.individuals():
        resultado.tipos[i.name] = {t.name for t in i.INDIRECT_is_a
                                   if isinstance(t, ThingClass) and t is not Thing}
    return resultado


def executar_pellet(argumentos: list[str], caminho: Path = ARQUIVO_OWL) -> str:
    """Roda o Pellet empacotado no owlready2 e devolve a saída de texto."""
    classpath = os.pathsep.join(str(j) for j in _PELLET_JARS)
    # "explain" já usa a OWL API e não aceita a opção --loader.
    carregador = [] if argumentos[0] == "explain" else ["--loader", "OWLAPIv3"]
    comando = [owlready2.JAVA_EXE, "-cp", classpath, "pellet.Pellet", *argumentos, *carregador,
               str(Path(caminho).resolve())]
    saida = subprocess.run(comando, capture_output=True, text=True, check=False)
    return saida.stdout + saida.stderr


def consistente_pellet(caminho: Path = ARQUIVO_OWL) -> bool:
    """Verificação de consistência pelo Pellet."""
    return "Consistent: Yes" in executar_pellet(["consistency"], caminho)


def classificacao_pellet(caminho: Path = ARQUIVO_OWL) -> Classificacao:
    """Lê a taxonomia impressa por ``pellet realize`` (indentação = profundidade)."""
    inicio = time.perf_counter()
    saida = executar_pellet(["realize"], caminho)
    resultado = Classificacao(segundos=time.perf_counter() - inicio)
    pais: dict[str, set[str]] = {}
    diretos: dict[str, set[str]] = {}
    pilha: list[tuple[int, str]] = []
    for linha in saida.splitlines():
        m = _LINHA_TAXONOMIA.match(linha)
        if not m or not m.group(2).startswith("http"):
            continue
        nivel, classe = len(m.group(1)), _local(m.group(2))
        if m.group(3) and m.group(3).endswith("#Nothing"):
            resultado.insatisfaziveis.add(classe)
            continue
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        if pilha and pilha[-1][1] != "Thing":
            pais.setdefault(classe, set()).add(pilha[-1][1])
        pais.setdefault(classe, set())
        pilha.append((nivel, classe))
        for ind in (m.group(4) or "").split(", "):
            if ind:
                diretos.setdefault(_local(ind), set()).add(classe)

    def ancestrais(c: str) -> set[str]:
        acc: set[str] = set()
        for p in pais.get(c, ()):
            acc |= {p} | ancestrais(p)
        return acc

    resultado.superclasses = {c: ancestrais(c) for c in pais if c != "Thing"}
    resultado.tipos = {i: set().union(*({c} | ancestrais(c) for c in cs)) for i, cs in diretos.items()}
    return resultado


def explicar_pellet(opcao: str, alvo: str = "", caminho: Path = ARQUIVO_OWL) -> str:
    """Justificativa mínima do Pellet (equivale ao botão "?" de explicação do Protégé).

    ``opcao``: ``--instance``, ``--property-value``, ``--subclass``, ``--unsat``
    ou ``--inconsistent``; ``alvo`` no formato do Pellet (ex.: ``maria,UsuarioIdoso``).
    O método "black" devolve um conjunto mínimo de axiomas; o "glass" (padrão
    do Pellet) inclui axiomas a mais quando há restrições de tipos de dados,
    mas é o único que explica inconsistência.
    """
    metodo = "glass" if opcao == "--inconsistent" else "black"  # black não explica inconsistência
    saida = executar_pellet(["explain", "-m", metodo, opcao, *([alvo] if alvo else [])], caminho)
    uteis = [l.rstrip() for l in saida.splitlines()
             if l.startswith(("Axiom:", "   ")) or re.match(r"^\d+\)", l)]
    return "\n".join(uteis)
