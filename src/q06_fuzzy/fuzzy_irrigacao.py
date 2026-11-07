"""Controlador fuzzy Mamdani para o tempo diário de irrigação por gotejamento.

Entradas: umidade do solo (% da água disponível), temperatura do ar (°C) e
probabilidade de chuva prevista (%). Saída: tempo de irrigação (min).

O módulo traz duas implementações do mesmo sistema:

* uma inferência Mamdani escrita passo a passo com NumPy e as funções de baixo
  nível do scikit-fuzzy (``inferir``), que expõe todos os valores intermediários;
* o mesmo sistema montado com a API ``skfuzzy.control`` (``criar_sistema_skfuzzy``),
  usada como referência para conferir a primeira.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import and_

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

ENTRADAS = ("umidade", "temperatura", "chuva")

UNIVERSOS: dict[str, np.ndarray] = {
    "umidade": np.round(np.arange(0, 100.01, 0.5), 2),
    "temperatura": np.round(np.arange(15, 40.001, 0.1), 2),
    "chuva": np.round(np.arange(0, 100.01, 0.5), 2),
    "tempo": np.round(np.arange(0, 60.001, 0.1), 2),
}

UNIDADES = {"umidade": "%", "temperatura": "°C", "chuva": "%", "tempo": "min"}

NOMES = {
    "umidade": "Umidade do solo (% da água disponível)",
    "temperatura": "Temperatura do ar (°C)",
    "chuva": "Probabilidade de chuva prevista (%)",
    "tempo": "Tempo de irrigação (min)",
}

# Cada termo linguístico: (tipo da função de pertinência, parâmetros).
TERMOS: dict[str, dict[str, tuple[str, list[float]]]] = {
    "umidade": {
        "seca": ("trap", [0, 0, 20, 45]),
        "adequada": ("tri", [25, 50, 75]),
        "úmida": ("trap", [55, 80, 100, 100]),
    },
    "temperatura": {
        "amena": ("gauss", [15, 5]),
        "quente": ("gauss", [27, 4]),
        "muito quente": ("gauss", [40, 5]),
    },
    "chuva": {
        "baixa": ("trap", [0, 0, 20, 40]),
        "média": ("tri", [20, 50, 80]),
        "alta": ("trap", [60, 80, 100, 100]),
    },
    "tempo": {
        "nenhum": ("tri", [0, 0, 15]),
        "curto": ("tri", [0, 15, 30]),
        "médio": ("tri", [15, 30, 45]),
        "longo": ("tri", [30, 45, 60]),
        "muito longo": ("tri", [45, 60, 60]),
    },
}

# Matriz de regras: para cada nível de chuva, linhas = umidade
# (seca, adequada, úmida) e colunas = temperatura (amena, quente, muito quente).
MATRIZ_REGRAS: dict[str, list[list[str]]] = {
    "baixa": [
        ["longo", "longo", "muito longo"],
        ["curto", "médio", "médio"],
        ["nenhum", "nenhum", "nenhum"],
    ],
    "média": [
        ["médio", "longo", "longo"],
        ["curto", "curto", "médio"],
        ["nenhum", "nenhum", "nenhum"],
    ],
    "alta": [
        ["curto", "médio", "médio"],
        ["nenhum", "curto", "curto"],
        ["nenhum", "nenhum", "nenhum"],
    ],
}


@dataclass(frozen=True)
class Regra:
    """Regra SE umidade E temperatura E chuva ENTÃO tempo.

    Uma entrada igual a ``None`` não participa do antecedente.
    """

    umidade: str | None
    temperatura: str | None
    chuva: str | None
    tempo: str

    def antecedentes(self) -> dict[str, str]:
        """Pares (variável, termo) que aparecem no SE da regra."""
        return {v: getattr(self, v) for v in ENTRADAS if getattr(self, v) is not None}

    def __str__(self) -> str:
        se = " E ".join(f"{v} é {t}" for v, t in self.antecedentes().items())
        return f"SE {se} ENTÃO tempo é {self.tempo}"


def _montar_regras() -> list[Regra]:
    umidades = list(TERMOS["umidade"])
    temperaturas = list(TERMOS["temperatura"])
    return [
        Regra(u, t, c, MATRIZ_REGRAS[c][i][j])
        for i, u in enumerate(umidades)
        for j, t in enumerate(temperaturas)
        for c in TERMOS["chuva"]
    ]


REGRAS: list[Regra] = _montar_regras()

# Variante com as 9 regras de solo úmido (todas com saída "nenhum") fundidas em uma só.
REGRAS_COMPACTAS: list[Regra] = (
    [r for r in REGRAS if r.umidade != "úmida"] + [Regra("úmida", None, None, "nenhum")]
)


def funcao_pertinencia(variavel: str, termo: str) -> np.ndarray:
    """Valores da função de pertinência de ``termo`` sobre o universo da variável."""
    tipo, p = TERMOS[variavel][termo]
    x = UNIVERSOS[variavel]
    if tipo == "tri":
        return fuzz.trimf(x, p)
    if tipo == "trap":
        return fuzz.trapmf(x, p)
    if tipo == "gauss":
        return fuzz.gaussmf(x, *p)
    raise ValueError(f"tipo de pertinência desconhecido: {tipo}")


def fuzzificar(umidade: float, temperatura: float, chuva: float,
               limitar: bool = True) -> dict[str, dict[str, float]]:
    """Grau de pertinência de cada entrada em cada termo linguístico.

    Com ``limitar=True`` (padrão, igual ao ``clip_to_bounds`` do skfuzzy) a
    entrada fora do universo é saturada no limite, como um sensor no fim de escala.
    """
    valores = dict(zip(ENTRADAS, (umidade, temperatura, chuva)))
    graus = {}
    for var, valor in valores.items():
        x = UNIVERSOS[var]
        if limitar:
            valor = float(np.clip(valor, x[0], x[-1]))
        graus[var] = {
            termo: float(fuzz.interp_membership(x, funcao_pertinencia(var, termo), valor))
            for termo in TERMOS[var]
        }
    return graus


@dataclass
class ResultadoMamdani:
    """Valores intermediários de uma inferência Mamdani."""

    graus: dict[str, dict[str, float]]
    forcas: np.ndarray            # força de disparo de cada regra (mesma ordem de REGRAS)
    ativacao: dict[str, float]    # maior força entre as regras de cada termo de saída
    cortes: dict[str, np.ndarray]  # conjunto de saída de cada termo, cortado (min)
    agregado: np.ndarray          # união (max) dos conjuntos cortados


def inferir(umidade: float, temperatura: float, chuva: float,
            regras: list[Regra] = REGRAS, limitar: bool = True) -> ResultadoMamdani:
    """Inferência Mamdani: AND = min, implicação = min, agregação = max."""
    graus = fuzzificar(umidade, temperatura, chuva, limitar)
    forcas = np.array([
        min(graus[v][t] for v, t in r.antecedentes().items()) for r in regras
    ])
    ativacao = {termo: 0.0 for termo in TERMOS["tempo"]}
    for regra, forca in zip(regras, forcas):
        ativacao[regra.tempo] = max(ativacao[regra.tempo], float(forca))
    cortes = {termo: np.fmin(a, funcao_pertinencia("tempo", termo))
              for termo, a in ativacao.items()}
    agregado = np.max(np.vstack(list(cortes.values())), axis=0)
    return ResultadoMamdani(graus, forcas, ativacao, cortes, agregado)


def centroide_manual(x: np.ndarray, mu: np.ndarray) -> float:
    """Centroide pela definição, integral de x·μ(x) dividida pela integral de μ(x)."""
    area = np.trapezoid(mu, x)
    if area == 0:
        raise ValueError("nenhuma regra disparou: conjunto agregado vazio")
    return float(np.trapezoid(x * mu, x) / area)


def defuzzificar(agregado: np.ndarray, metodo: str = "centroid") -> float:
    """Defuzzifica o conjunto agregado com o método do skfuzzy indicado.

    Métodos: centroid, bisector, mom, som, lom.
    """
    if not agregado.any():
        raise ValueError("nenhuma regra disparou: conjunto agregado vazio")
    return float(fuzz.defuzz(UNIVERSOS["tempo"], agregado, metodo))


def tempo_irrigacao(umidade: float, temperatura: float, chuva: float,
                    metodo: str = "centroid", regras: list[Regra] = REGRAS) -> float:
    """Tempo de irrigação (min) para uma leitura dos sensores."""
    return defuzzificar(inferir(umidade, temperatura, chuva, regras).agregado, metodo)


def criar_sistema_skfuzzy(metodo: str = "centroid",
                          regras: list[Regra] = REGRAS) -> ctrl.ControlSystem:
    """Mesmo sistema (variáveis, pertinências e regras) na API skfuzzy.control."""
    antecedentes = {v: ctrl.Antecedent(UNIVERSOS[v], v) for v in ENTRADAS}
    tempo = ctrl.Consequent(UNIVERSOS["tempo"], "tempo", defuzzify_method=metodo)
    for var in (*antecedentes.values(), tempo):
        for termo in TERMOS[var.label]:
            var[termo] = funcao_pertinencia(var.label, termo)
    regras_ctrl = [
        ctrl.Rule(reduce(and_, (antecedentes[v][t] for v, t in r.antecedentes().items())),
                  tempo[r.tempo], label=f"R{i}")
        for i, r in enumerate(regras, start=1)
    ]
    return ctrl.ControlSystem(regras_ctrl)


def tempo_irrigacao_skfuzzy(sistema: ctrl.ControlSystem, umidade: float,
                            temperatura: float, chuva: float) -> float:
    """Executa o sistema do skfuzzy.control para uma leitura dos sensores."""
    sim = ctrl.ControlSystemSimulation(sistema)
    sim.inputs({"umidade": umidade, "temperatura": temperatura, "chuva": chuva})
    sim.compute()
    return float(sim.output["tempo"])


def superficie(eixo_x: str, eixo_y: str, fixo: dict[str, float],
               n: int = 41) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Saída do controlador numa grade n×n de duas entradas, com a terceira fixa."""
    xs = np.linspace(UNIVERSOS[eixo_x][0], UNIVERSOS[eixo_x][-1], n)
    ys = np.linspace(UNIVERSOS[eixo_y][0], UNIVERSOS[eixo_y][-1], n)
    X, Y = np.meshgrid(xs, ys)
    Z = np.empty_like(X)
    for idx in np.ndindex(X.shape):
        Z[idx] = tempo_irrigacao(**{eixo_x: X[idx], eixo_y: Y[idx]}, **fixo)
    return X, Y, Z
