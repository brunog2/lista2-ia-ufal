"""Consultas sobre a rede da Q8: inferência exata, enumeração manual,
amostragem, atualização incremental e valor da informação de cada sintoma."""

import numpy as np
import pandas as pd
from pgmpy.factors.discrete import State, TabularCPD
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.sampling import BayesianModelSampling

Evidencia = dict[str, str]


def distribuicao(
    inferencia: VariableElimination, variavel: str, evidencia: Evidencia | None = None,
    incertas: list[TabularCPD] | None = None,
) -> pd.Series:
    """P(variavel | evidencia) por eliminação de variáveis, indexada pelos estados.

    `incertas` recebe evidências virtuais (ver `evidencia_incerta`).
    """
    fator = inferencia.query(
        [variavel], evidence=evidencia or None, virtual_evidence=incertas or None, show_progress=False
    )
    return pd.Series(fator.values, index=fator.state_names[variavel], name=variavel)


def evidencia_incerta(variavel: str, confianca_sim: float) -> TabularCPD:
    """Evidência virtual Sim/Nao: o relato pesa `confianca_sim` a favor de Sim e o restante a favor de Nao."""
    return TabularCPD(variavel, 2, [[confianca_sim], [1 - confianca_sim]], state_names={variavel: ["Sim", "Nao"]})


def enumeracao_manual(rede: DiscreteBayesianNetwork, variavel: str, evidencia: Evidencia | None = None) -> pd.Series:
    """P(variavel | evidencia) somando a distribuição conjunta inteira com numpy.

    Monta P(X1..Xn) = prod_i P(Xi | Pais(Xi)) por einsum, fixa as evidências
    por indexação, soma as variáveis ocultas e normaliza. Serve de conferência
    independente do Variable Elimination do pgmpy.
    """
    evidencia = evidencia or {}
    nos = list(rede.nodes())
    eixo = {no: i for i, no in enumerate(nos)}
    operandos = []
    for cpd in rede.get_cpds():
        operandos += [cpd.get_values().reshape(cpd.cardinality), [eixo[v] for v in cpd.variables]]
    conjunta = np.einsum(*operandos, list(range(len(nos))))

    estados = {no: rede.get_cpds(no).state_names[no] for no in nos}
    indice = tuple(estados[no].index(evidencia[no]) if no in evidencia else slice(None) for no in nos)
    restantes = [no for no in nos if no not in evidencia]
    ocultas = tuple(i for i, no in enumerate(restantes) if no != variavel)
    marginal = conjunta[indice].sum(axis=ocultas)
    return pd.Series(marginal / marginal.sum(), index=estados[variavel], name=variavel)


def atualizacao_incremental(
    inferencia: VariableElimination, variavel: str, estado: str, passos: list[tuple[str, str]]
) -> pd.DataFrame:
    """P(variavel=estado) depois de cada evidência acrescentada, começando pela priori."""
    evidencia: Evidencia = {}
    linhas = [("(nenhuma)", distribuicao(inferencia, variavel)[estado])]
    for no, valor in passos:
        evidencia[no] = valor
        linhas.append((f"+ {no}={valor}", distribuicao(inferencia, variavel, evidencia)[estado]))
    return pd.DataFrame(linhas, columns=["evidencia", f"P({variavel}={estado})"])


def estimar_por_amostragem(
    rede: DiscreteBayesianNetwork, variavel: str, estado: str, evidencia: Evidencia,
    n_amostras: int, metodo: str, semente: int,
) -> float:
    """Estimativa de P(variavel=estado | evidencia) por 'rejeicao' ou 'ponderacao' (likelihood weighting)."""
    amostrador = BayesianModelSampling(rede)
    estados = [State(no, valor) for no, valor in evidencia.items()]
    if metodo == "rejeicao":
        amostras = amostrador.rejection_sample(estados, size=n_amostras, seed=semente, show_progress=False)
        return float((amostras[variavel] == estado).mean())
    if metodo == "ponderacao":
        amostras = amostrador.likelihood_weighted_sample(estados, size=n_amostras, seed=semente, show_progress=False)
        pesos = amostras["_weight"]
        return float(pesos[amostras[variavel] == estado].sum() / pesos.sum())
    raise ValueError(f"método desconhecido: {metodo}")


def entropia(probabilidades: pd.Series) -> float:
    """Entropia de Shannon em bits."""
    p = probabilidades[probabilidades > 0]
    return float(-(p * np.log2(p)).sum())


def valor_da_informacao(
    inferencia: VariableElimination, alvo: str, estado: str, evidencia: Evidencia, candidatos: list[str]
) -> pd.DataFrame:
    """Quanto observar cada candidato Sim/Nao (ainda não observado) mexe no diagnóstico de `alvo`.

    Para cada candidato C devolve P(C=Sim | e), P(alvo=estado | e, C=Sim),
    P(alvo=estado | e, C=Nao) e a informação mútua I(alvo; C | e) em bits,
    que é a redução esperada da entropia do diagnóstico ao se observar C.
    """
    h_atual = entropia(distribuicao(inferencia, alvo, evidencia))
    linhas = []
    for candidato in candidatos:
        p_candidato = distribuicao(inferencia, candidato, evidencia)
        posteriores = {v: distribuicao(inferencia, alvo, {**evidencia, candidato: v}) for v in ("Sim", "Nao")}
        h_esperada = sum(p_candidato[v] * entropia(posteriores[v]) for v in posteriores)
        linhas.append({
            "variavel": candidato,
            "P(C=Sim|e)": p_candidato["Sim"],
            f"P({alvo}={estado}|e,C=Sim)": posteriores["Sim"][estado],
            f"P({alvo}={estado}|e,C=Nao)": posteriores["Nao"][estado],
            "informacao_mutua_bits": h_atual - h_esperada,
        })
    return pd.DataFrame(linhas).sort_values("informacao_mutua_bits", ascending=False, ignore_index=True)
