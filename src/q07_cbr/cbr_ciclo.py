"""Ciclo de Raciocínio Baseado em Casos: Retrieve, Reuse, Revise e Retain (Q7)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from cbr_casos import Caso, Problema, carregar_base, salvar_base
from cbr_similaridade import SimSintomas, jaccard_ponderado, similaridade

# Acima deste valor, um caso revisado é considerado repetição de um caso já
# existente com o mesmo diagnóstico (ver a calibração no notebook/README).
LIMIAR_DUPLICATA = 0.95

# Alternativa sugerida quando o paciente informa alergia a um medicamento.
SUBSTITUTOS = {
    "dipirona": "paracetamol",
    "paracetamol": "dipirona",
    "ibuprofeno": "paracetamol",
    "amoxicilina": "azitromicina",
    "azitromicina": "amoxicilina",
}
ORIENTACAO_PEDIATRICA = "Paciente pediátrico: doses calculadas pelo peso"
ORIENTACAO_IDOSO = "Paciente idoso: reavaliar em 24 a 48 h e reforçar a hidratação"


@dataclass
class Sugestao:
    """Resultado do Reuse: diagnóstico votado, confiança e tratamento adaptado."""

    diagnostico: str
    confianca: float
    votos: dict[str, float]
    vizinhos: list[tuple[Caso, float]]
    caso_fonte: Caso
    tratamento: list[str]
    ajustes: list[str] = field(default_factory=list)


@dataclass
class ResultadoRetencao:
    retido: bool
    id_caso: str
    similaridade: float  # maior similaridade com um caso de mesmo diagnóstico


def adaptar_tratamento(tratamento: list[str], problema: Problema) -> tuple[list[str], list[str]]:
    """Adapta o tratamento do caso recuperado às alergias e à idade do paciente.

    Retorna o novo tratamento e a lista de ajustes aplicados. Itens que já são
    proibições ("Evitar ...") ficam como estão.
    """
    novo, ajustes = [], []
    for item in tratamento:
        if item in (ORIENTACAO_PEDIATRICA, ORIENTACAO_IDOSO):  # eram do paciente do caso fonte; refeitas abaixo
            continue
        # shortcut: casa o nome do alérgeno como substring do texto; com tratamentos estruturados
        # (medicamento, dose) a checagem seria por campo
        alergeno = next((a for a in problema.alergias if a in item.lower()), None)
        if alergeno is None or item.lower().startswith("evitar"):
            novo.append(item)
            continue
        alternativa = SUBSTITUTOS.get(alergeno, "outra opção")
        novo.append(f"Não usar {alergeno} (alergia informada): {alternativa} como alternativa, a critério médico")
        ajustes.append(f"Item '{item}' trocado por causa da alergia a {alergeno}")
    if problema.idade < 12:
        novo.append(ORIENTACAO_PEDIATRICA)
        ajustes.append("Orientação pediátrica acrescentada")
    elif problema.idade >= 60:
        novo.append(ORIENTACAO_IDOSO)
        ajustes.append("Orientação para idoso acrescentada")
    return novo, ajustes


class SistemaCBR:
    """Base de casos com as quatro etapas do ciclo CBR."""

    def __init__(
        self,
        casos: list[Caso],
        k: int = 3,
        sim_sintomas: SimSintomas = jaccard_ponderado,
        caminho: str | Path | None = None,
        limiar_duplicata: float = LIMIAR_DUPLICATA,
    ) -> None:
        self.casos = casos
        self.k = k
        self.sim_sintomas = sim_sintomas
        self.caminho = caminho  # None = base só em memória (não persiste)
        self.limiar_duplicata = limiar_duplicata

    @classmethod
    def de_arquivo(cls, caminho: str | Path, **kwargs) -> SistemaCBR:
        return cls(carregar_base(caminho), caminho=caminho, **kwargs)

    def similaridade(self, p: Problema, q: Problema) -> float:
        return similaridade(p, q, self.sim_sintomas)

    def recuperar(self, problema: Problema, k: int | None = None) -> list[tuple[Caso, float]]:
        """Retrieve: os k casos mais similares, em ordem decrescente."""
        ranking = sorted(
            ((c, self.similaridade(problema, c.problema)) for c in self.casos),
            key=lambda par: par[1],
            reverse=True,
        )
        return ranking[: k or self.k]

    def reutilizar(self, problema: Problema, vizinhos: list[tuple[Caso, float]]) -> Sugestao:
        """Reuse: voto ponderado pela similaridade e adaptação do tratamento."""
        votos: dict[str, float] = defaultdict(float)
        for caso, sim in vizinhos:
            votos[caso.diagnostico] += sim
        # empate de votos: vence o diagnóstico do vizinho mais similar (ordem de inserção)
        diagnostico = max(votos, key=votos.get)
        fonte = next(c for c, _ in vizinhos if c.diagnostico == diagnostico)
        tratamento, ajustes = adaptar_tratamento(fonte.tratamento, problema)
        total = sum(votos.values())
        return Sugestao(
            diagnostico=diagnostico,
            confianca=votos[diagnostico] / total if total else 0.0,
            votos=dict(sorted(votos.items(), key=lambda kv: kv[1], reverse=True)),
            vizinhos=vizinhos,
            caso_fonte=fonte,
            tratamento=tratamento,
            ajustes=ajustes,
        )

    def consultar(self, problema: Problema) -> Sugestao:
        """Retrieve + Reuse."""
        return self.reutilizar(problema, self.recuperar(problema))

    def reter(self, caso: Caso) -> ResultadoRetencao:
        """Retain: inclui o caso revisado, salvo se repetir um caso de mesmo diagnóstico.

        Na repetição, o caso existente ganha uma confirmação em vez de duplicar a base.
        """
        mesmos = [c for c in self.casos if c.diagnostico == caso.diagnostico]
        mais_proximo, sim = max(
            ((c, self.similaridade(caso.problema, c.problema)) for c in mesmos),
            key=lambda par: par[1],
            default=(None, 0.0),
        )
        if mais_proximo is not None and sim >= self.limiar_duplicata:
            mais_proximo.confirmacoes += 1
            self._persistir()
            return ResultadoRetencao(False, mais_proximo.id, sim)
        novo = replace(caso, id=self._proximo_id(), origem="retido")
        self.casos.append(novo)
        self._persistir()
        return ResultadoRetencao(True, novo.id, sim)

    def _proximo_id(self) -> str:
        return f"C{max((int(c.id[1:]) for c in self.casos), default=0) + 1:02d}"

    def _persistir(self) -> None:
        if self.caminho is not None:
            salvar_base(self.casos, self.caminho)


def revisar(
    problema: Problema,
    sugestao: Sugestao,
    diagnostico: str | None = None,
    tratamento: list[str] | None = None,
    observacao: str = "",
) -> Caso:
    """Revise: o médico confirma (argumentos None) ou corrige a sugestão.

    Devolve o caso resolvido, ainda sem id; o id é atribuído na retenção.
    """
    corrigido = diagnostico is not None and diagnostico != sugestao.diagnostico
    if not tratamento:
        if corrigido:  # o tratamento sugerido era para outro diagnóstico
            raise ValueError("Ao corrigir o diagnóstico, informe também o tratamento.")
        tratamento = sugestao.tratamento
    return Caso(
        id="",
        problema=problema,
        diagnostico=diagnostico or sugestao.diagnostico,
        tratamento=list(tratamento),
        observacao=observacao or ("Diagnóstico corrigido na revisão." if corrigido else "Sugestão confirmada na revisão."),
    )


def revisar_interativo(
    problema: Problema, sugestao: Sugestao, perguntar: Callable[[str], str] = input
) -> Caso:
    """Revise em modo interativo: pergunta ao médico se confirma ou corrige."""
    resposta = perguntar(f"Confirma o diagnóstico '{sugestao.diagnostico}'? [s/n] ").strip().lower()
    if resposta.startswith("s"):
        return revisar(problema, sugestao)
    diagnostico = ""
    while not diagnostico:
        diagnostico = perguntar("Diagnóstico correto: ").strip()
    tratamento: list[str] = []
    while not tratamento:
        texto = perguntar("Tratamento (itens separados por ';'): ")
        tratamento = [t.strip() for t in texto.split(";") if t.strip()]
    observacao = perguntar("Observação (opcional): ").strip()
    return revisar(problema, sugestao, diagnostico, tratamento, observacao)
