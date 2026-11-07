"""Rede Bayesiana para diagnóstico diferencial de dengue e influenza (Q8).

Define a estrutura, as CPTs e a exportação do modelo para formatos de
ferramentas de redes bayesianas (BIF, XMLBIF, XDSL do GeNIe e NET do Hugin).
As probabilidades são valores plausíveis definidos para fins educacionais;
a justificativa de cada uma está no README da questão.
"""

from pathlib import Path

from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.readwrite import (
    BIFReader, BIFWriter, NETReader, NETWriter, XDSLReader, XDSLWriter, XMLBIFReader, XMLBIFWriter,
)

SIM_NAO = ["Sim", "Nao"]

ARESTAS = [
    ("Estacao", "Exposicao"),
    ("Estacao", "Influenza"),
    ("Exposicao", "Dengue"),
    ("Dengue", "Febre"),
    ("Influenza", "Febre"),
    ("Dengue", "DorMuscular"),
    ("Influenza", "DorMuscular"),
    ("Influenza", "Tosse"),
    ("Dengue", "DorRetroOrbital"),
    ("Dengue", "Manchas"),
    ("Dengue", "ProvaLaco"),
]

DESCRICOES = {
    "Estacao": "Período do ano em Alagoas: Chuvosa (cerca de abril a agosto) ou Seca",
    "Exposicao": "Paciente mora ou circula perto de foco do Aedes aegypti",
    "Dengue": "Paciente está com dengue (doença principal)",
    "Influenza": "Paciente está com gripe (diagnóstico concorrente)",
    "Febre": "Febre aferida ou relatada (>= 38 °C)",
    "DorMuscular": "Mialgia (dor no corpo)",
    "Tosse": "Tosse",
    "DorRetroOrbital": "Dor atrás dos olhos",
    "Manchas": "Exantema (manchas vermelhas na pele)",
    "ProvaLaco": "Prova do laço positiva (exame de beira de leito)",
}

TIPOS = {
    "Estacao": "fator de contexto",
    "Exposicao": "fator de risco",
    "Dengue": "doença",
    "Influenza": "doença",
    "Febre": "sintoma",
    "DorMuscular": "sintoma",
    "Tosse": "sintoma",
    "DorRetroOrbital": "sintoma",
    "Manchas": "sintoma",
    "ProvaLaco": "exame",
}


def _cpd_binaria(variavel: str, pais: list[str], p_sim: list[float]) -> TabularCPD:
    """CPT de variável Sim/Nao a partir de P(var=Sim | pais) na ordem Sim/Nao dos pais."""
    return TabularCPD(
        variavel, 2, [p_sim, [round(1 - p, 10) for p in p_sim]],
        evidence=pais or None, evidence_card=[2] * len(pais) or None,
        state_names={variavel: SIM_NAO, **{p: SIM_NAO for p in pais}},
    )


def construir_cpds() -> list[TabularCPD]:
    """Todas as CPTs da rede. Colunas seguem a ordem dos estados dos pais (Sim antes de Nao)."""
    estacao = TabularCPD("Estacao", 2, [[0.4], [0.6]], state_names={"Estacao": ["Chuvosa", "Seca"]})
    exposicao = TabularCPD(
        "Exposicao", 2, [[0.6, 0.25], [0.4, 0.75]], evidence=["Estacao"], evidence_card=[2],
        state_names={"Exposicao": SIM_NAO, "Estacao": ["Chuvosa", "Seca"]},
    )
    influenza = TabularCPD(
        "Influenza", 2, [[0.20, 0.08], [0.80, 0.92]], evidence=["Estacao"], evidence_card=[2],
        state_names={"Influenza": SIM_NAO, "Estacao": ["Chuvosa", "Seca"]},
    )
    return [
        estacao,
        exposicao,
        influenza,
        _cpd_binaria("Dengue", ["Exposicao"], [0.20, 0.03]),
        # colunas: (D=Sim,I=Sim), (D=Sim,I=Nao), (D=Nao,I=Sim), (D=Nao,I=Nao)
        _cpd_binaria("Febre", ["Dengue", "Influenza"], [0.98, 0.90, 0.75, 0.10]),
        _cpd_binaria("DorMuscular", ["Dengue", "Influenza"], [0.95, 0.80, 0.70, 0.15]),
        _cpd_binaria("Tosse", ["Influenza"], [0.80, 0.15]),
        _cpd_binaria("DorRetroOrbital", ["Dengue"], [0.60, 0.05]),
        _cpd_binaria("Manchas", ["Dengue"], [0.45, 0.05]),
        _cpd_binaria("ProvaLaco", ["Dengue"], [0.40, 0.05]),
    ]


def construir_rede() -> DiscreteBayesianNetwork:
    """Monta a rede com estrutura e CPTs e valida com check_model."""
    rede = DiscreteBayesianNetwork(ARESTAS)
    rede.add_cpds(*construir_cpds())
    rede.check_model()
    return rede


FORMATOS = {
    "bif": (BIFWriter, BIFReader),
    "xml": (XMLBIFWriter, XMLBIFReader),
    "xdsl": (XDSLWriter, XDSLReader),
    "net": (NETWriter, NETReader),
}


def exportar_rede(rede: DiscreteBayesianNetwork, pasta: Path) -> dict[str, Path]:
    """Grava a rede em BIF, XMLBIF, XDSL (GeNIe) e NET (Hugin) e devolve os caminhos."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = {}
    for extensao, (escritor, _) in FORMATOS.items():
        caminhos[extensao] = pasta / f"rede_dengue.{extensao}"
        escritor(rede).write(str(caminhos[extensao]))
    return caminhos


def ler_rede(caminho: Path) -> DiscreteBayesianNetwork:
    """Relê um arquivo exportado em qualquer dos formatos de FORMATOS."""
    _, leitor = FORMATOS[caminho.suffix.lstrip(".")]
    return leitor(str(caminho)).get_model()
