"""Renderização de axiomas OWL do owlready2 em Manchester Syntax e notação DL."""

from __future__ import annotations

from owlready2 import (
    EXACTLY,
    MAX,
    MIN,
    ONLY,
    SOME,
    VALUE,
    And,
    ConstrainedDatatype,
    Inverse,
    Not,
    OneOf,
    Ontology,
    Or,
    Restriction,
    Thing,
)

_XSD = {int: "integer", float: "decimal", str: "string", bool: "boolean"}
_FACETAS = {"min_inclusive": ">=", "max_inclusive": "<=", "min_exclusive": ">", "max_exclusive": "<"}
_FACETAS_DL = {">=": "≥", "<=": "≤", ">": ">", "<": "<"}
_CARD = {EXACTLY: ("exactly", "="), MIN: ("min", "≥"), MAX: ("max", "≤")}


def _nome(x) -> str:
    if x is Thing:
        return "owl:Thing"
    if x in _XSD:
        return _XSD[x]
    return getattr(x, "name", repr(x))


def _datatype(d: ConstrainedDatatype, dl: bool) -> str:
    facetas = []
    for faceta, op in _FACETAS.items():
        if (v := getattr(d, faceta, None)) is not None:
            facetas.append(f"{_FACETAS_DL[op] if dl else op} {v}")
    return f"{_XSD[d.base_datatype]}[{', '.join(facetas)}]"


def manchester(expr) -> str:
    """Expressão de classe em Manchester Syntax (a usada pelo Protégé)."""
    def sub(e):
        s = manchester(e)
        return f"({s})" if isinstance(e, (And, Or, Restriction)) else s

    if isinstance(expr, And):
        return " and ".join(sub(c) for c in expr.Classes)
    if isinstance(expr, Or):
        return " or ".join(sub(c) for c in expr.Classes)
    if isinstance(expr, Not):
        return f"not {sub(expr.Class)}"
    if isinstance(expr, OneOf):
        return "{" + ", ".join(_nome(i) for i in expr.instances) + "}"
    if isinstance(expr, Inverse):
        return f"inverse {_nome(expr.property)}"
    if isinstance(expr, ConstrainedDatatype):
        return _datatype(expr, dl=False)
    if isinstance(expr, Restriction):
        p = manchester(expr.property)
        if expr.type == SOME:
            return f"{p} some {sub(expr.value)}"
        if expr.type == ONLY:
            return f"{p} only {sub(expr.value)}"
        if expr.type == VALUE:
            return f"{p} value {_nome(expr.value)}"
        palavra, _ = _CARD[expr.type]
        alvo = f" {sub(expr.value)}" if expr.value is not None else ""
        return f"{p} {palavra} {expr.cardinality}{alvo}"
    return _nome(expr)


def dl(expr) -> str:
    """Expressão de classe em notação de Lógica de Descrição."""
    def sub(e):
        s = dl(e)
        return f"({s})" if isinstance(e, (And, Or)) else s

    if isinstance(expr, And):
        return " ⊓ ".join(sub(c) for c in expr.Classes)
    if isinstance(expr, Or):
        return " ⊔ ".join(sub(c) for c in expr.Classes)
    if isinstance(expr, Not):
        return f"¬{sub(expr.Class)}"
    if isinstance(expr, OneOf):
        return "{" + ", ".join(_nome(i) for i in expr.instances) + "}"
    if isinstance(expr, Inverse):
        return f"{_nome(expr.property)}⁻"
    if isinstance(expr, ConstrainedDatatype):
        return _datatype(expr, dl=True)
    if isinstance(expr, Restriction):
        p = dl(expr.property)
        if expr.type == SOME:
            return f"∃{p}.{sub(expr.value)}"
        if expr.type == ONLY:
            return f"∀{p}.{sub(expr.value)}"
        if expr.type == VALUE:
            return f"∃{p}.{{{_nome(expr.value)}}}"
        _, simbolo = _CARD[expr.type]
        alvo = sub(expr.value) if expr.value is not None else "⊤"
        return f"{simbolo}{expr.cardinality} {p}.{alvo}"
    return "⊤" if expr is Thing else _nome(expr)


def propriedades_em(expr) -> list:
    """Propriedades citadas numa expressão, na ordem em que aparecem."""
    if isinstance(expr, (And, Or)):
        return [p for c in expr.Classes for p in propriedades_em(c)]
    if isinstance(expr, Not):
        return propriedades_em(expr.Class)
    if isinstance(expr, Restriction):
        return [expr.property, *propriedades_em(expr.value)]
    return []


def axiomas(onto: Ontology) -> list[dict[str, str]]:
    """Axiomas de TBox e RBox declarados, lado a lado em DL e em Manchester."""
    linhas = []

    def add(tipo: str, notacao_dl: str, notacao_manchester: str) -> None:
        linhas.append({"tipo": tipo, "DL": notacao_dl, "Manchester": notacao_manchester})

    for c in onto.classes():
        for eq in c.equivalent_to:
            add("equivalência", f"{c.name} ≡ {dl(eq)}", f"Class: {c.name} EquivalentTo: {manchester(eq)}")
        for pai in c.is_a:
            if pai is not Thing:
                add("subclasse", f"{c.name} ⊑ {dl(pai)}", f"Class: {c.name} SubClassOf: {manchester(pai)}")
    for disj in onto.disjoint_classes():
        nomes = [_nome(e) for e in disj.entities]
        add("disjunção", f"Disj({', '.join(nomes)})", f"DisjointClasses: {', '.join(nomes)}")
    for p in [*onto.object_properties(), *onto.data_properties()]:
        caracteristicas = [t.__name__.replace("Property", "") for t in p.is_a
                           if t.__name__ in ("FunctionalProperty", "TransitiveProperty")]
        for car in caracteristicas:
            simbolo = f"⊤ ⊑ ≤1 {p.name}.⊤" if car == "Functional" else f"{p.name} ∘ {p.name} ⊑ {p.name}"
            add("característica", simbolo, f"Property: {p.name} Characteristics: {car}")
        if getattr(p, "inverse_property", None) and p.name > p.inverse_property.name:
            add("inversa", f"{p.name} ≡ {p.inverse_property.name}⁻",
                f"ObjectProperty: {p.name} InverseOf: {p.inverse_property.name}")
        for cadeia in getattr(p, "property_chain", []):
            nomes = [q.name for q in cadeia.properties]
            add("cadeia", f"{' ∘ '.join(nomes)} ⊑ {p.name}",
                f"ObjectProperty: {p.name} SubPropertyChain: {' o '.join(nomes)}")
        for d in p.domain:
            add("domínio", f"∃{p.name}.⊤ ⊑ {_nome(d)}", f"Property: {p.name} Domain: {_nome(d)}")
        for r in p.range:
            add("imagem", f"⊤ ⊑ ∀{p.name}.{_nome(r)}", f"Property: {p.name} Range: {_nome(r)}")
    return linhas
