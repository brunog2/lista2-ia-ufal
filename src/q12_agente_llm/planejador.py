"""Planejador exato e verificador de restrições do assistente de agenda (Q12).

Este módulo é a parte de inferência do agente e não usa LLM. Recebe atividades
já estruturadas e devolve o plano de maior utilidade dentro da janela disponível.

Modelo do problema
------------------
- Janela [inicio, fim) em minutos desde 00:00.
- Compromisso fixo: ocupa exatamente [inicio_fixo, inicio_fixo + duracao) e é
  obrigatório (restrição rígida).
- Atividade não divisível: entra inteira, num único bloco contínuo, ou fica de fora.
- Atividade divisível: pode ser executada em blocos de pelo menos ``bloco_minimo``
  minutos e pode ser feita só em parte (o restante fica para depois).
- Prazo com hora (``prazo_hora``): todos os blocos terminam até esse horário.
- Atividades não se sobrepõem.

Utilidade
---------
valor(a) = peso(prioridade) * urgencia(prazo_dias), com peso alta=3, media=2,
baixa=1 e urgencia(d) = 1 + 2/(1 + d) (hoje 3,0; amanhã 2,0; 7 dias 1,25).
U(plano) = soma de valor(a) * minutos_feitos(a) / duracao(a). A parcela
fracionária repete o f(B) da função de utilidade da Q11.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PESO_PRIORIDADE = {"alta": 3, "media": 2, "baixa": 1}
_HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def urgencia(prazo_dias: int) -> float:
    """Peso de urgência: decresce com os dias até o prazo (hoje=3, amanhã=2, 7 dias=1,25)."""
    return 1 + 2 / (1 + prazo_dias)


def hhmm_para_min(texto: str) -> int:
    m = _HHMM.match(texto.strip())
    if not m:
        raise ValueError(f"horário inválido: {texto!r} (use HH:MM)")
    return int(m.group(1)) * 60 + int(m.group(2))


def min_para_hhmm(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


@dataclass(frozen=True)
class Atividade:
    id: str
    nome: str
    duracao: int
    prioridade: str
    prazo_dias: int
    prazo_hora: int | None = None
    inicio_fixo: int | None = None
    divisivel: bool = False
    bloco_minimo: int = 30
    minimo_exigido: int = 0  # minutos que o plano é obrigado a dar à atividade (perguntas contrafactuais)

    def __post_init__(self):
        if not self.id:
            raise ValueError("atividade sem id")
        if self.duracao <= 0:
            raise ValueError(f"{self.id}: duração deve ser positiva")
        if self.prioridade not in PESO_PRIORIDADE:
            raise ValueError(f"{self.id}: prioridade deve ser alta, media ou baixa")
        if self.prazo_dias < 0:
            raise ValueError(f"{self.id}: prazo_dias não pode ser negativo")
        if self.prazo_hora is not None and self.prazo_dias != 0:
            raise ValueError(f"{self.id}: prazo com horário só vale para prazo hoje (prazo_dias=0)")
        if self.inicio_fixo is not None and self.divisivel:
            raise ValueError(f"{self.id}: compromisso com horário fixo não pode ser divisível")
        if self.bloco_minimo <= 0:
            raise ValueError(f"{self.id}: bloco mínimo deve ser positivo")
        if not 0 <= self.minimo_exigido <= self.duracao:
            raise ValueError(f"{self.id}: mínimo exigido fora de [0, duração]")

    @property
    def fixa(self) -> bool:
        return self.inicio_fixo is not None

    @property
    def valor(self) -> float:
        return PESO_PRIORIDADE[self.prioridade] * urgencia(self.prazo_dias)

    @property
    def bloco(self) -> int:
        return min(self.bloco_minimo, self.duracao)


@dataclass(frozen=True)
class Segmento:
    atividade_id: str
    inicio: int
    fim: int

    @property
    def minutos(self) -> int:
        return self.fim - self.inicio


@dataclass
class Plano:
    segmentos: tuple[Segmento, ...]
    minutos: dict[str, int]
    utilidade: float


@dataclass
class ResultadoPlanejamento:
    melhor: Plano | None  # None quando nenhum plano atende aos mínimos exigidos
    estatisticas: dict = field(default_factory=dict)


def utilidade(atividades: list[Atividade], minutos: dict[str, int]) -> float:
    return sum(a.valor * minutos.get(a.id, 0) / a.duracao for a in atividades)


def validar_instancia(atividades: list[Atividade], inicio: int, fim: int) -> None:
    """Erros que tornam o problema mal definido (não são decisões do planejador)."""
    erros = []
    if inicio >= fim:
        erros.append("a janela precisa ter início antes do fim")
    ids = [a.id for a in atividades]
    if len(ids) != len(set(ids)):
        erros.append("há ids de atividades repetidos")
    fixas = sorted((a for a in atividades if a.fixa), key=lambda a: a.inicio_fixo)
    for a in fixas:
        if a.inicio_fixo < inicio or a.inicio_fixo + a.duracao > fim:
            erros.append(f"{a.id}: compromisso fixo {min_para_hhmm(a.inicio_fixo)}-"
                         f"{min_para_hhmm(a.inicio_fixo + a.duracao)} fora da janela "
                         f"{min_para_hhmm(inicio)}-{min_para_hhmm(fim)}")
        if a.prazo_hora is not None and a.inicio_fixo + a.duracao > a.prazo_hora:
            erros.append(f"{a.id}: horário fixo termina depois do próprio prazo")
    for a, b in zip(fixas, fixas[1:]):
        if a.inicio_fixo + a.duracao > b.inicio_fixo:
            erros.append(f"compromissos fixos {a.id} e {b.id} se sobrepõem")
    if erros:
        raise ValueError("; ".join(erros))


def planejar(atividades: list[Atividade], inicio: int, fim: int, passo: int = 15,
             podar: bool = True) -> ResultadoPlanejamento:
    """Busca exata em profundidade com poda (branch and bound) sobre agendas justificadas à esquerda.

    Em cada instante livre ``t`` o planejador decide: começar uma atividade
    não divisível, executar um bloco de uma divisível (comprimentos múltiplos de
    ``passo`` a partir do bloco mínimo, mais o bloco que esgota o intervalo ou a
    atividade) ou ficar ocioso até o próximo compromisso fixo. Ficar ocioso e
    começar algo antes do próximo obstáculo nunca é necessário: qualquer agenda
    viável pode ser deslocada para a esquerda sem violar restrições, e terminar
    mais cedo só facilita os prazos. Assim a busca percorre todas as agendas
    relevantes sem enumerar instantes ociosos um a um.

    A poda usa a relaxação fracionária (mochila fracionária) do tempo livre
    restante como limite superior: um ramo cujo limite fica abaixo da melhor
    utilidade já encontrada não pode conter o ótimo e é descartado. ``podar=False``
    desliga a poda (usado para medir o ganho e para testar que ela não muda o ótimo).
    """
    validar_instancia(atividades, inicio, fim)
    por_id = {a.id: a for a in atividades}
    fixas = sorted((a for a in atividades if a.fixa), key=lambda a: a.inicio_fixo)
    flexiveis = [a for a in atividades if not a.fixa]
    valor_fixas = sum(a.valor for a in fixas)
    densidade = sorted(flexiveis, key=lambda a: a.valor / a.duracao, reverse=True)

    feito = {a.id: 0 for a in flexiveis}
    segmentos: list[Segmento] = []
    melhor: list = []  # [(chave, Plano)]; lista para ser alterada dentro das funções aninhadas
    stats = {"nos_explorados": 0, "planos_completos": 0, "podas": 0}

    def tempo_livre(t: int) -> int:
        ocupado = sum(max(0, min(fim, a.inicio_fixo + a.duracao) - max(t, a.inicio_fixo)) for a in fixas)
        return fim - t - ocupado

    def limite_superior(t: int) -> float:
        u = valor_fixas + sum(a.valor * feito[a.id] / a.duracao for a in flexiveis)
        capacidade = tempo_livre(t)
        for a in densidade:
            if capacidade <= 0:
                break
            restante = 0 if (not a.divisivel and feito[a.id]) else a.duracao - feito[a.id]
            usar = min(restante, capacidade)
            u += a.valor * usar / a.duracao
            capacidade -= usar
        return u

    def registrar() -> None:
        stats["planos_completos"] += 1
        minutos = {a.id: a.duracao for a in fixas} | dict(feito)
        if any(minutos[a.id] < a.minimo_exigido for a in atividades):
            return
        u = utilidade(atividades, minutos)
        fim_de = {}
        for s in segmentos:
            fim_de[s.atividade_id] = s.fim
        # desempate: mesma utilidade -> terminar antes o que vale mais -> menos fragmentos
        chave = (round(u, 9), -round(sum(por_id[i].valor * f for i, f in fim_de.items()), 6), -len(segmentos))
        if not melhor or chave > melhor[0][0]:
            melhor[:] = [(chave, Plano(tuple(segmentos), minutos, u))]

    def proximo_obstaculo(t: int) -> int:
        return min((a.inicio_fixo for a in fixas if a.inicio_fixo >= t), default=fim)

    def colocar(a: Atividade, t: int, duracao: int) -> None:
        segmentos.append(Segmento(a.id, t, t + duracao))
        if not a.fixa:
            feito[a.id] += duracao
        dfs(t + duracao)
        segmentos.pop()
        if not a.fixa:
            feito[a.id] -= duracao

    def dfs(t: int) -> None:
        stats["nos_explorados"] += 1
        fixa_agora = next((a for a in fixas if a.inicio_fixo == t), None)
        if fixa_agora:
            colocar(fixa_agora, t, fixa_agora.duracao)
            return
        if t >= fim:
            registrar()
            return
        if podar and melhor and limite_superior(t) < melhor[0][1].utilidade - 1e-9:
            stats["podas"] += 1
            return
        limite = proximo_obstaculo(t)
        for a in flexiveis:
            teto = min(limite, a.prazo_hora if a.prazo_hora is not None else fim)
            if not a.divisivel:
                if feito[a.id] == 0 and t + a.duracao <= teto:
                    colocar(a, t, a.duracao)
                continue
            # bloco colado a outro bloco da mesma atividade duplicaria agendas já vistas
            if segmentos and segmentos[-1].atividade_id == a.id and segmentos[-1].fim == t:
                continue
            maximo = min(a.duracao - feito[a.id], teto - t)
            if maximo < a.bloco:
                continue
            comprimentos = set(range(a.bloco, maximo + 1, passo)) | {maximo}
            for duracao in sorted(comprimentos, reverse=True):
                colocar(a, t, duracao)
        if limite > t:
            dfs(limite)  # ocioso até o próximo compromisso fixo (ou o fim da janela)

    dfs(inicio)
    return ResultadoPlanejamento(melhor[0][1] if melhor else None, stats)


def verificar(segmentos: list[Segmento], atividades: list[Atividade], inicio: int, fim: int) -> list[str]:
    """Verificador independente: devolve a lista de violações (vazia = plano válido).

    Não reaproveita nada da busca; confere o plano pronto contra as restrições.
    Serve para validar a saída do planejador e qualquer plano proposto por fora
    (pelo usuário ou pelo próprio LLM).
    """
    violacoes = []
    por_id = {a.id: a for a in atividades}
    por_atividade: dict[str, list[Segmento]] = {}
    for s in segmentos:
        if s.atividade_id not in por_id:
            violacoes.append(f"{s.atividade_id}: atividade desconhecida")
            continue
        if s.inicio >= s.fim:
            violacoes.append(f"{s.atividade_id}: bloco com início depois do fim")
        if s.inicio < inicio or s.fim > fim:
            violacoes.append(f"{s.atividade_id}: bloco {min_para_hhmm(s.inicio)}-{min_para_hhmm(s.fim)} "
                             f"fora da janela {min_para_hhmm(inicio)}-{min_para_hhmm(fim)}")
        por_atividade.setdefault(s.atividade_id, []).append(s)

    ordem = sorted(segmentos, key=lambda s: (s.inicio, s.fim))
    for a, b in zip(ordem, ordem[1:]):
        if b.inicio < a.fim:
            violacoes.append(f"sobreposição entre {a.atividade_id} ({min_para_hhmm(a.inicio)}-{min_para_hhmm(a.fim)}) "
                             f"e {b.atividade_id} ({min_para_hhmm(b.inicio)}-{min_para_hhmm(b.fim)})")

    for a in atividades:
        blocos = por_atividade.get(a.id, [])
        total = sum(s.minutos for s in blocos)
        if a.fixa:
            if [(s.inicio, s.fim) for s in blocos] != [(a.inicio_fixo, a.inicio_fixo + a.duracao)]:
                violacoes.append(f"{a.id}: compromisso fixo deve ocupar exatamente "
                                 f"{min_para_hhmm(a.inicio_fixo)}-{min_para_hhmm(a.inicio_fixo + a.duracao)}")
        elif not a.divisivel:
            if len(blocos) > 1:
                violacoes.append(f"{a.id}: atividade não divisível foi interrompida em {len(blocos)} blocos")
            elif blocos and total != a.duracao:
                violacoes.append(f"{a.id}: atividade não divisível com {total} de {a.duracao} min")
        else:
            if total > a.duracao:
                violacoes.append(f"{a.id}: {total} min agendados para uma atividade de {a.duracao} min")
            for s in blocos:
                if s.minutos < a.bloco:
                    violacoes.append(f"{a.id}: bloco de {s.minutos} min menor que o mínimo de {a.bloco} min")
        if a.prazo_hora is not None and any(s.fim > a.prazo_hora for s in blocos):
            violacoes.append(f"{a.id}: termina depois do prazo das {min_para_hhmm(a.prazo_hora)}")
        if total < a.minimo_exigido:
            violacoes.append(f"{a.id}: recebeu {total} min, abaixo do mínimo exigido de {a.minimo_exigido} min")
    return violacoes
