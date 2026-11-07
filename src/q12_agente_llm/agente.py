"""Agente de agenda acadêmica: LLM para linguagem natural, ferramentas para decidir (Q12).

O LLM (Claude) interpreta o pedido do professor e chama ferramentas com schemas
estritos. As ferramentas guardam o estado da agenda e chamam o planejador e o
verificador determinísticos. O cliente do LLM é injetável: em produção é
``ClienteAnthropic``; nos testes e no notebook sem chave é um cliente roteirizado.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from explicacao import avaliar_proposta, explicar
from planejador import Atividade, Segmento, hhmm_para_min, min_para_hhmm

MODELO = "claude-opus-5-5"
BETA_FALLBACK = "server-side-fallback-2026-07-01"

SYSTEM = """Você é o assistente de agenda acadêmica de um professor universitário. Responda em português do Brasil.

Seu papel é interpretar o pedido e comunicar o resultado. Quem decide horários é o planejador, acessado pelas ferramentas.

Como trabalhar:
1. Extraia do pedido a janela disponível e cada atividade (duração em minutos, prioridade alta/media/baixa, prazo em dias a partir de hoje: hoje=0, amanhã=1, próxima semana=7, horário fixo se houver, prazo com horário se houver).
2. Use definir_janela e registrar_atividades para gravar o que entendeu. Marque divisivel=true só se o professor permitir dividir a atividade; na dúvida, use false e diga isso na resposta.
3. Se faltar um dado essencial (por exemplo, a duração de uma atividade), pergunte ao professor em vez de inventar.
4. Sempre que a agenda mudar, chame planejar_agenda antes de responder. Para avaliar um plano sugerido pelo professor, use avaliar_plano.
5. Se uma ferramenta devolver erro, corrija os dados e tente de novo, ou explique o problema ao professor.

Na resposta final, use somente fatos que vieram das ferramentas: horários, utilidades, motivos de cada atividade ficar dentro ou fora, a segunda melhor alternativa e o resultado da verificação. Não calcule horários nem utilidades por conta própria. Mostre o plano em uma tabela curta, diga o que ficou de fora e por quê, e liste as suposições que você fez ao interpretar o pedido."""

LEMBRETE_PLANEJAR = ("A agenda foi alterada nesta conversa e planejar_agenda ainda não foi chamada depois da "
                     "alteração. Chame planejar_agenda e responda com base no resultado.")


def _schema(propriedades: dict) -> dict:
    return {"type": "object", "properties": propriedades, "required": list(propriedades), "additionalProperties": False}


_ATIVIDADE = _schema({
    "id": {"type": "string", "description": "Identificador curto e estável, por exemplo A, B ou aula_ia."},
    "nome": {"type": "string"},
    "duracao_min": {"type": "integer", "description": "Duração total em minutos."},
    "prioridade": {"type": "string", "enum": ["alta", "media", "baixa"]},
    "prazo_dias": {"type": "integer", "description": "Dias até o prazo: hoje=0, amanhã=1, próxima semana=7."},
    "prazo_hora": {"type": ["string", "null"], "description": "HH:MM em que deve terminar hoje, ou null."},
    "horario_fixo": {"type": ["string", "null"], "description": "HH:MM de início de um compromisso fixo, ou null."},
    "divisivel": {"type": "boolean", "description": "true só se o professor permitir dividir a atividade."},
    "bloco_minimo_min": {"type": ["integer", "null"], "description": "Menor bloco aceitável se divisível (padrão 30)."},
})

FERRAMENTAS = [
    {
        "name": "definir_janela",
        "description": "Define o intervalo de tempo disponível hoje (HH:MM a HH:MM). Substitui a janela anterior.",
        "input_schema": _schema({"inicio": {"type": "string"}, "fim": {"type": "string"}}),
        "strict": True,
    },
    {
        "name": "registrar_atividades",
        "description": ("Inclui ou atualiza atividades na agenda (atualiza quando o id já existe). "
                        "Devolve a agenda atual com o valor calculado de cada atividade."),
        "input_schema": _schema({"atividades": {"type": "array", "items": _ATIVIDADE}}),
        "strict": True,
    },
    {
        "name": "remover_atividade",
        "description": "Remove uma atividade da agenda pelo id.",
        "input_schema": _schema({"id": {"type": "string"}}),
        "strict": True,
    },
    {
        "name": "planejar_agenda",
        "description": ("Calcula o plano de maior utilidade para a agenda atual com busca exata e devolve "
                        "justificativas: motivo de cada horário, motivo de cada atividade fora do plano, "
                        "restrições ativas, segunda melhor alternativa e verificação independente."),
        "input_schema": _schema({}),
        "strict": True,
    },
    {
        "name": "avaliar_plano",
        "description": ("Verifica um plano proposto pelo professor (ou por você) contra as restrições e "
                        "compara sua utilidade com a do plano ótimo."),
        "input_schema": _schema({"segmentos": {"type": "array", "items": _schema({
            "atividade_id": {"type": "string"}, "inicio": {"type": "string"}, "fim": {"type": "string"}})}}),
        "strict": True,
    },
]


class ErroLLM(RuntimeError):
    """Falha ao falar com o provedor do LLM (rede, autenticação, limite de taxa...)."""


class ClienteLLM(Protocol):
    def criar_mensagem(self, *, system: str, tools: list[dict], messages: list[dict]) -> Any:
        """Devolve um objeto com ``content`` (blocos com ``type``) e ``stop_reason``."""


class ClienteAnthropic:
    """Cliente real: Messages API (beta, por causa do fallback de recusa no servidor)."""

    def __init__(self, esforco: str = "medium", max_tokens: int = 16000, client: Any = None):
        import anthropic

        self._anthropic = anthropic
        self._client = client or anthropic.Anthropic()
        self.esforco = esforco
        self.max_tokens = max_tokens

    def criar_mensagem(self, *, system, tools, messages):
        a = self._anthropic
        try:
            return self._client.beta.messages.create(
                model=MODELO,
                max_tokens=self.max_tokens,
                betas=[BETA_FALLBACK],
                fallbacks="default",
                output_config={"effort": self.esforco},
                system=system,
                tools=tools,
                messages=messages,
            )
        except a.AuthenticationError as e:
            raise ErroLLM("chave de API inválida ou ausente (ANTHROPIC_API_KEY)") from e
        except a.PermissionDeniedError as e:
            raise ErroLLM("a chave não tem permissão para este modelo ou recurso") from e
        except a.RateLimitError as e:
            raise ErroLLM("limite de requisições atingido; tente de novo em instantes") from e
        except a.BadRequestError as e:
            raise ErroLLM(f"requisição rejeitada pela API: {e.message}") from e
        except a.APIStatusError as e:
            raise ErroLLM(f"erro da API ({e.status_code}): {e.message}") from e
        except a.APIConnectionError as e:
            raise ErroLLM("falha de conexão com a API") from e


def _atividade_de_entrada(d: dict) -> Atividade:
    return Atividade(
        id=d["id"].strip(),
        nome=d["nome"].strip(),
        duracao=int(d["duracao_min"]),
        prioridade=d["prioridade"],
        prazo_dias=int(d["prazo_dias"]),
        prazo_hora=hhmm_para_min(d["prazo_hora"]) if d.get("prazo_hora") else None,
        inicio_fixo=hhmm_para_min(d["horario_fixo"]) if d.get("horario_fixo") else None,
        divisivel=bool(d["divisivel"]),
        bloco_minimo=int(d.get("bloco_minimo_min") or 30),
    )


@dataclass
class Agenda:
    """Estado do ambiente do agente e executor das ferramentas (sem LLM)."""

    janela: tuple[int, int] | None = None
    atividades: dict[str, Atividade] = field(default_factory=dict)

    def executar(self, nome: str, entrada: dict) -> dict:
        """Executa uma ferramenta. Entrada inválida gera ValueError (vira tool_result com is_error)."""
        if nome == "definir_janela":
            inicio, fim = hhmm_para_min(entrada["inicio"]), hhmm_para_min(entrada["fim"])
            if inicio >= fim:
                raise ValueError("a janela precisa ter início antes do fim")
            self.janela = (inicio, fim)
            return {"janela": {"inicio": min_para_hhmm(inicio), "fim": min_para_hhmm(fim)}}
        if nome == "registrar_atividades":
            novas = [_atividade_de_entrada(d) for d in entrada["atividades"]]  # valida tudo antes de gravar
            for a in novas:
                self.atividades[a.id] = a
            return self.estado()
        if nome == "remover_atividade":
            if entrada["id"] not in self.atividades:
                raise ValueError(f"não existe atividade com id {entrada['id']!r}")
            del self.atividades[entrada["id"]]
            return self.estado()
        if nome == "planejar_agenda":
            self._exigir_dados()
            return explicar(list(self.atividades.values()), *self.janela)
        if nome == "avaliar_plano":
            self._exigir_dados()
            segs = [Segmento(s["atividade_id"], hhmm_para_min(s["inicio"]), hhmm_para_min(s["fim"]))
                    for s in entrada["segmentos"]]
            return avaliar_proposta(segs, list(self.atividades.values()), *self.janela)
        raise ValueError(f"ferramenta desconhecida: {nome}")

    def _exigir_dados(self) -> None:
        if self.janela is None:
            raise ValueError("defina a janela disponível com definir_janela antes de planejar")
        if not self.atividades:
            raise ValueError("nenhuma atividade registrada")

    def estado(self) -> dict:
        return {
            "janela": None if self.janela is None else {"inicio": min_para_hhmm(self.janela[0]),
                                                        "fim": min_para_hhmm(self.janela[1])},
            "atividades": [{"id": a.id, "nome": a.nome, "duracao_min": a.duracao, "prioridade": a.prioridade,
                            "prazo_dias": a.prazo_dias, "valor": round(a.valor, 4),
                            "horario_fixo": None if a.inicio_fixo is None else min_para_hhmm(a.inicio_fixo),
                            "prazo_hora": None if a.prazo_hora is None else min_para_hhmm(a.prazo_hora),
                            "divisivel": a.divisivel} for a in self.atividades.values()],
        }


@dataclass
class ChamadaFerramenta:
    nome: str
    entrada: dict
    resultado: str
    erro: bool


@dataclass
class RespostaAgente:
    texto: str
    trace: list[ChamadaFerramenta]
    stop_reason: str | None
    resumo: dict | None = None  # último resultado de planejar_agenda neste turno, para gráficos


_FERRAMENTAS_QUE_ALTERAM = {"definir_janela", "registrar_atividades", "remover_atividade"}


class Agente:
    """Loop manual de uso de ferramentas, com histórico multi-turno."""

    def __init__(self, cliente: ClienteLLM, agenda: Agenda | None = None, max_iteracoes: int = 12):
        self.cliente = cliente
        self.agenda = agenda or Agenda()
        self.max_iteracoes = max_iteracoes
        self.historico: list[dict] = []

    def processar(self, texto_usuario: str) -> RespostaAgente:
        tamanho_inicial = len(self.historico)
        agenda_inicial = copy.deepcopy(self.agenda)

        def desfazer() -> None:
            # mantém o histórico coerente (e o prefixo intacto) quando o turno não se completa
            del self.historico[tamanho_inicial:]
            self.agenda = agenda_inicial

        self.historico.append({"role": "user", "content": texto_usuario})
        trace: list[ChamadaFerramenta] = []
        resumo = None
        replanejar_pendente = lembrete_enviado = False
        try:
            for _ in range(self.max_iteracoes):
                resposta = self.cliente.criar_mensagem(system=SYSTEM, tools=FERRAMENTAS, messages=self.historico)
                motivo = resposta.stop_reason
                if motivo == "refusal":
                    desfazer()
                    detalhes = getattr(resposta, "stop_details", None)
                    categoria = getattr(detalhes, "category", None) or "não informada"
                    return RespostaAgente(f"O modelo recusou o pedido (categoria: {categoria}). "
                                          "Reformule a solicitação.", trace, motivo)
                if motivo == "max_tokens":
                    desfazer()
                    return RespostaAgente("A resposta do modelo foi cortada por limite de tokens; "
                                          "nada foi alterado na agenda.", trace, motivo)
                self.historico.append({"role": "assistant", "content": resposta.content})
                if motivo == "pause_turn":
                    continue
                if motivo == "tool_use":
                    resultados = []
                    for bloco in resposta.content:
                        if bloco.type != "tool_use":
                            continue
                        try:
                            dados = self.agenda.executar(bloco.name, bloco.input)
                            conteudo, erro = json.dumps(dados, ensure_ascii=False), False
                            if bloco.name in _FERRAMENTAS_QUE_ALTERAM:
                                replanejar_pendente = True
                            elif bloco.name == "planejar_agenda":
                                replanejar_pendente, resumo = False, dados
                        except (ValueError, KeyError, TypeError) as e:
                            conteudo, erro = f"Erro: {e}", True
                        trace.append(ChamadaFerramenta(bloco.name, dict(bloco.input), conteudo, erro))
                        resultados.append({"type": "tool_result", "tool_use_id": bloco.id,
                                           "content": conteudo, "is_error": erro})
                    self.historico.append({"role": "user", "content": resultados})
                    continue
                # end_turn: com tool_choice auto não há garantia de chamada; insiste uma vez se faltou planejar
                pode_planejar = self.agenda.janela is not None and bool(self.agenda.atividades)
                if replanejar_pendente and pode_planejar and not lembrete_enviado:
                    lembrete_enviado = True
                    self.historico.append({"role": "user", "content": LEMBRETE_PLANEJAR})
                    continue
                texto = "\n".join(b.text for b in resposta.content if b.type == "text")
                return RespostaAgente(texto, trace, motivo, resumo)
        except ErroLLM:
            desfazer()
            raise
        desfazer()
        raise ErroLLM(f"o agente passou de {self.max_iteracoes} chamadas ao modelo sem concluir o turno")
