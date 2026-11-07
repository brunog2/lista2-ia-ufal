"""Representação dos casos clínicos e persistência da base em JSON (Q7).

Um caso é o par (problema, solução): o problema descreve o paciente
(sintomas com intensidade, temperatura, duração, idade, tipo de início e
alergias) e a solução traz o diagnóstico e o tratamento recomendado.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

AVISO = (
    "Base de casos FICTÍCIA, criada para fins educacionais (Lista 2 de IA, UFAL). "
    "Não usar para diagnóstico ou tratamento reais."
)

# Vocabulário fechado de sintomas: nome interno -> descrição para o usuário.
SINTOMAS: dict[str, str] = {
    "dor_cabeca": "dor de cabeça",
    "dor_retroorbital": "dor atrás dos olhos",
    "mialgia": "dor muscular",
    "artralgia": "dor nas articulações",
    "edema_articular": "inchaço nas articulações",
    "exantema": "manchas vermelhas na pele",
    "prurido": "coceira",
    "conjuntivite": "olhos vermelhos sem secreção",
    "petequias": "pontos vermelhos de sangramento na pele",
    "nauseas": "náuseas",
    "vomito": "vômito",
    "diarreia": "diarreia",
    "dor_abdominal": "dor abdominal",
    "coriza": "coriza",
    "espirros": "espirros",
    "congestao_nasal": "nariz entupido",
    "dor_garganta": "dor de garganta",
    "placas_amigdalas": "placas de pus nas amígdalas",
    "linfonodos_cervicais": "ínguas no pescoço",
    "tosse": "tosse",
    "falta_ar": "falta de ar",
    "anosmia": "perda de olfato",
    "cansaco": "cansaço",
    "calafrios": "calafrios",
}
INTENSIDADES = {1: "leve", 2: "moderada", 3: "intensa"}
INICIOS = ("subito", "gradual")


@dataclass(frozen=True)
class Problema:
    """Descrição do paciente, isto é, a parte 'problema' de um caso."""

    sintomas: dict[str, int]
    temperatura: float
    dias_sintomas: int
    idade: int
    inicio: str
    alergias: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        desconhecidos = set(self.sintomas) - SINTOMAS.keys()
        if desconhecidos:
            raise ValueError(f"Sintomas fora do vocabulário: {sorted(desconhecidos)}")
        if any(v not in INTENSIDADES for v in self.sintomas.values()):
            raise ValueError("Intensidade deve ser 1 (leve), 2 (moderada) ou 3 (intensa).")
        if not 34.0 <= self.temperatura <= 43.0:
            raise ValueError("Temperatura fora da faixa plausível (34 a 43 °C).")
        if self.dias_sintomas < 0:
            raise ValueError("Dias de sintomas não pode ser negativo.")
        if not 0 <= self.idade <= 120:
            raise ValueError("Idade deve estar entre 0 e 120 anos.")
        if self.inicio not in INICIOS:
            raise ValueError(f"Início deve ser um de {INICIOS}.")


@dataclass
class Caso:
    """Caso da base: problema + diagnóstico + tratamento, com metadados de retenção."""

    id: str
    problema: Problema
    diagnostico: str
    tratamento: list[str]
    origem: str = "novo"  # "base" (cadastro inicial), "retido" (aprendido no ciclo) ou "novo" (ainda não retido)
    confirmacoes: int = 0  # quantas consultas posteriores confirmaram este caso
    observacao: str = ""

    @classmethod
    def de_dict(cls, dados: dict) -> Caso:
        p = dados["problema"]
        problema = Problema(**{**p, "alergias": tuple(p.get("alergias", ()))})
        return cls(**{**dados, "problema": problema})

    def para_dict(self) -> dict:
        return asdict(self)


def carregar_base(caminho: str | Path) -> list[Caso]:
    """Lê a base de casos de um arquivo JSON."""
    with open(caminho, encoding="utf-8") as f:
        return [Caso.de_dict(c) for c in json.load(f)["casos"]]


def salvar_base(casos: list[Caso], caminho: str | Path) -> None:
    """Grava a base em JSON (escrita atômica, para não corromper o arquivo)."""
    caminho = Path(caminho)
    temporario = caminho.with_suffix(".tmp")
    conteudo = {"aviso": AVISO, "casos": [c.para_dict() for c in casos]}
    temporario.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, caminho)
