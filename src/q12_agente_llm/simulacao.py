"""Cliente roteirizado: simula o formato das respostas da API sem chamar nenhum modelo.

Serve para testar o loop do agente e para demonstrar o fluxo quando não há
``ANTHROPIC_API_KEY``. As respostas são objetos dos próprios tipos do SDK
(``BetaMessage``, ``BetaTextBlock``, ``BetaToolUseBlock``), mas o conteúdo foi
escrito à mão: representa o que se espera que o modelo extraia, e não é
saída real do Claude. O texto final do roteiro de demonstração é a explicação
determinística do planejador (``texto_explicacao``), também sem LLM.
"""
from __future__ import annotations

import itertools
import json
from typing import Callable

from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock, BetaUsage

from agente import MODELO
from explicacao import texto_explicacao

_ids = itertools.count(1)


def texto(conteudo: str) -> BetaTextBlock:
    return BetaTextBlock(type="text", text=conteudo)


def chamada(nome: str, entrada: dict, id_: str | None = None) -> BetaToolUseBlock:
    return BetaToolUseBlock(type="tool_use", id=id_ or f"toolu_sim_{next(_ids):04d}", name=nome, input=entrada)


def mensagem(*blocos, stop_reason: str | None = None) -> BetaMessage:
    if stop_reason is None:
        stop_reason = "tool_use" if any(b.type == "tool_use" for b in blocos) else "end_turn"
    return BetaMessage(id=f"msg_sim_{next(_ids):04d}", type="message", role="assistant", model=MODELO,
                       content=list(blocos), stop_reason=stop_reason, stop_sequence=None,
                       usage=BetaUsage(input_tokens=0, output_tokens=0))


Passo = BetaMessage | Callable[[list[dict]], BetaMessage]


class ClienteRoteirizado:
    """Devolve as respostas de um roteiro, em ordem, e registra cada requisição recebida."""

    def __init__(self, passos: list[Passo]):
        self.passos = list(passos)
        self.requisicoes: list[dict] = []

    def criar_mensagem(self, *, system, tools, messages):
        self.requisicoes.append({"system": system, "tools": tools, "messages": list(messages)})
        if not self.passos:
            raise AssertionError("o roteiro acabou, mas o agente pediu outra resposta")
        passo = self.passos.pop(0)
        return passo(messages) if callable(passo) else passo


def explicacao_do_ultimo_plano(messages: list[dict]) -> BetaMessage:
    """Passo de roteiro que responde com a explicação determinística do último planejar_agenda."""
    for msg in reversed(messages):
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for r in msg["content"]:
                if r.get("type") == "tool_result" and not r["is_error"] and '"plano"' in r["content"]:
                    return mensagem(texto(texto_explicacao(json.loads(r["content"]))))
    return mensagem(texto("Nenhum plano foi calculado neste turno."))


PEDIDO_Q11 = (
    "Preciso preparar uma aula de Inteligência Artificial, corrigir trabalhos de alunos e participar de uma "
    "reunião de pesquisa. Tenho apenas quatro horas disponíveis hoje, das 14h às 18h. A preparação da aula é "
    "urgente e leva uns 90 minutos. A correção dos trabalhos precisa ser concluída até amanhã e leva duas horas. "
    "A reunião é das 16h às 17h. Também tenho a revisão de um artigo, uma hora de trabalho, para a próxima "
    "semana, mas é a menos importante. Organize minhas atividades da melhor maneira possível."
)

PEDIDO_NOVO = ("Surgiu agora uma orientação de TCC de 30 minutos, alta prioridade, tem que ser hoje. "
               "Encaixe na agenda.")


def _atividade(id_, nome, dur, prio, dias, fixo=None, divisivel=False):
    return {"id": id_, "nome": nome, "duracao_min": dur, "prioridade": prio, "prazo_dias": dias,
            "prazo_hora": None, "horario_fixo": fixo, "divisivel": divisivel, "bloco_minimo_min": None}


ATIVIDADES_Q11 = [
    _atividade("A", "Preparar aula de IA", 90, "alta", 0),
    _atividade("B", "Corrigir trabalhos", 120, "media", 1),
    _atividade("C", "Reunião de pesquisa", 60, "alta", 0, fixo="16:00"),
    _atividade("D", "Revisar artigo", 60, "baixa", 7),
]


def roteiro_q11() -> list[Passo]:
    """Dois turnos: o pedido da Q11 e, depois, um pedido novo que força replanejamento."""
    return [
        # turno 1: extração do pedido (duas chamadas paralelas), planejamento, explicação
        mensagem(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"}),
                 chamada("registrar_atividades", {"atividades": ATIVIDADES_Q11})),
        mensagem(chamada("planejar_agenda", {})),
        explicacao_do_ultimo_plano,
        # turno 2: atividade nova no meio da conversa
        mensagem(chamada("registrar_atividades", {"atividades": [
            _atividade("E", "Orientação de TCC", 30, "alta", 0)]})),
        mensagem(chamada("planejar_agenda", {})),
        explicacao_do_ultimo_plano,
    ]
