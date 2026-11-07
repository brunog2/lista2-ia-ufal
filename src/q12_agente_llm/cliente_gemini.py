"""Cliente Gemini (Google AI Studio) para o agente da Q12, com modelo principal e modelo de reserva.

O loop do ``Agente`` trabalha com o formato de mensagens por blocos (``text``, ``tool_use``,
``tool_result``). Este cliente traduz esse histórico para o formato do Gemini, chama o modelo
e devolve a resposta no mesmo formato de blocos. Assim o agente, as ferramentas e os testes
não dependem do provedor.

A chave é lida da variável de ambiente ``GEMINI_API_KEY`` (pelo próprio SDK ``google-genai``).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from agente import ErroLLM

MODELO_PRINCIPAL = "gemini-3.5-flash-lite"
MODELO_RESERVA = "gemini-3.1-flash-lite"

# Erros em que vale tentar o modelo de reserva: modelo inexistente, cota esgotada, falha do servidor.
_CODIGOS_DE_RESERVA = {404, 429, 500, 502, 503, 504}
_MOTIVOS_DE_RECUSA = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}

_ids = itertools.count(1)


@dataclass
class Bloco:
    """Bloco de conteúdo no formato que o ``Agente`` espera (``type``, ``text``, ``id``, ``name``, ``input``)."""

    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)
    parte: Any = None  # Part original do Gemini: reenviada intacta para preservar a thought_signature


@dataclass
class Mensagem:
    content: list[Bloco]
    stop_reason: str
    model: str


def declaracoes(tools: list[dict]) -> list:
    """Converte as ferramentas (JSON Schema) em declarações de função do Gemini."""
    from google.genai import types

    return [types.FunctionDeclaration(name=t["name"], description=t["description"],
                                      parameters_json_schema=t["input_schema"]) for t in tools]


def para_conteudos(messages: list[dict]) -> list:
    """Traduz o histórico do agente para a lista de ``Content`` do Gemini."""
    from google.genai import types

    chamadas: dict[str, tuple[str, str | None]] = {}  # id do tool_use -> (nome, id original do Gemini)
    conteudos = []
    for msg in messages:
        if msg["role"] == "assistant":
            partes = []
            for b in msg["content"]:
                if b.type == "tool_use":
                    id_gemini = b.parte.function_call.id if b.parte is not None else None
                    chamadas[b.id] = (b.name, id_gemini)
                if b.parte is not None:
                    partes.append(b.parte)
                elif b.type == "text":
                    partes.append(types.Part(text=b.text))
                elif b.type == "tool_use":
                    partes.append(types.Part(function_call=types.FunctionCall(name=b.name, args=b.input)))
            conteudos.append(types.Content(role="model", parts=partes))
        elif isinstance(msg["content"], str):
            conteudos.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))
        else:
            partes = []
            for r in msg["content"]:
                nome, id_gemini = chamadas[r["tool_use_id"]]
                chave = "erro" if r["is_error"] else "resultado"
                partes.append(types.Part(function_response=types.FunctionResponse(
                    id=id_gemini, name=nome, response={chave: r["content"]})))
            conteudos.append(types.Content(role="user", parts=partes))
    return conteudos


def de_resposta(resposta: Any, modelo: str) -> Mensagem:
    """Traduz a resposta do Gemini para blocos e um ``stop_reason`` no vocabulário do agente."""
    candidato = resposta.candidates[0] if resposta.candidates else None
    if candidato is None:  # o próprio pedido foi bloqueado pelos filtros
        return Mensagem([], "refusal", modelo)
    motivo = candidato.finish_reason.name if candidato.finish_reason else "STOP"
    if motivo == "MALFORMED_FUNCTION_CALL":
        raise ErroLLM(f"{modelo} gerou uma chamada de ferramenta malformada")

    blocos = []
    partes = candidato.content.parts if candidato.content and candidato.content.parts else []
    for parte in partes:
        if parte.function_call:
            fc = parte.function_call
            blocos.append(Bloco("tool_use", id=fc.id or f"gem_{next(_ids):04d}", name=fc.name,
                                input=dict(fc.args or {}), parte=parte))
        elif parte.thought:
            blocos.append(Bloco("pensamento", parte=parte))
        elif parte.text is not None:
            blocos.append(Bloco("text", text=parte.text, parte=parte))
        else:
            blocos.append(Bloco("outro", parte=parte))

    if any(b.type == "tool_use" for b in blocos):
        stop = "tool_use"
    elif motivo in _MOTIVOS_DE_RECUSA:
        stop = "refusal"
    elif motivo == "MAX_TOKENS":
        stop = "max_tokens"
    else:
        stop = "end_turn"
    return Mensagem(blocos, stop, modelo)


class ClienteGemini:
    """Chama o modelo principal e, se ele estiver indisponível ou sem cota, o modelo de reserva."""

    def __init__(self, modelos: tuple[str, ...] = (MODELO_PRINCIPAL, MODELO_RESERVA),
                 max_tokens: int = 8192, client: Any = None):
        from google import genai

        self._client = client or genai.Client()
        self.modelos = modelos
        self.max_tokens = max_tokens
        self.modelo_usado: str | None = None

    def criar_mensagem(self, *, system, tools, messages):
        import httpx
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declaracoes(tools))],
            # o loop de ferramentas é do Agente; o SDK não deve executar funções sozinho
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            max_output_tokens=self.max_tokens,
        )
        conteudos = para_conteudos(messages)
        falhas = []
        for modelo in self.modelos:
            try:
                resposta = self._client.models.generate_content(model=modelo, contents=conteudos, config=config)
            except errors.APIError as e:
                if e.code in (401, 403):
                    raise ErroLLM("chave de API inválida ou sem permissão (GEMINI_API_KEY)") from e
                if e.code not in _CODIGOS_DE_RESERVA:
                    raise ErroLLM(f"requisição rejeitada por {modelo} ({e.code}): {e.message}") from e
                falhas.append(f"{modelo}: {e.code} {e.message}")
                continue
            except httpx.HTTPError as e:
                falhas.append(f"{modelo}: falha de conexão ({type(e).__name__})")
                continue
            self.modelo_usado = modelo
            return de_resposta(resposta, modelo)
        raise ErroLLM("nenhum modelo respondeu. " + "; ".join(falhas))
