import json

import anthropic
import httpx2
import pytest
from anthropic.types.beta import BetaThinkingBlock

from agente import BETA_FALLBACK, FERRAMENTAS, MODELO, Agente, ClienteAnthropic, ErroLLM, LEMBRETE_PLANEJAR
from simulacao import ATIVIDADES_Q11, PEDIDO_NOVO, PEDIDO_Q11, ClienteRoteirizado, chamada, mensagem, roteiro_q11, texto


def ultimos_resultados(requisicao):
    conteudo = requisicao["messages"][-1]["content"]
    assert isinstance(conteudo, list) and all(b["type"] == "tool_result" for b in conteudo)
    return conteudo


def test_schemas_sao_estritos():
    def checar(schema):
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
            for sub in schema["properties"].values():
                checar(sub)
        if schema.get("type") == "array":
            checar(schema["items"])

    for f in FERRAMENTAS:
        assert f["strict"] is True
        checar(f["input_schema"])


def test_fluxo_q11_executa_ferramentas_e_devolve_resultados():
    cliente = ClienteRoteirizado(roteiro_q11())
    agente = Agente(cliente)
    resposta = agente.processar(PEDIDO_Q11)

    assert resposta.stop_reason == "end_turn"
    assert [c.nome for c in resposta.trace] == ["definir_janela", "registrar_atividades", "planejar_agenda"]
    assert not any(c.erro for c in resposta.trace)
    # as duas chamadas paralelas voltam juntas, numa única mensagem de usuário, com ids correspondentes
    resultados = ultimos_resultados(cliente.requisicoes[1])
    chamadas = [b for b in cliente.requisicoes[1]["messages"][-2]["content"] if b.type == "tool_use"]
    assert [r["tool_use_id"] for r in resultados] == [c.id for c in chamadas]
    assert all(r["is_error"] is False for r in resultados)
    # o plano vem do planejador
    assert [(p["atividade"], p["inicio"]) for p in resposta.resumo["plano"]] == [("A", "14:00"), ("C", "16:00"),
                                                                                ("D", "17:00")]
    assert "14:00-15:30  A" in resposta.texto
    # histórico: usuário, assistente (2 tool_use), resultados, assistente, resultado, assistente final
    assert [m["role"] for m in agente.historico] == ["user", "assistant", "user", "assistant", "user", "assistant"]
    assert agente.historico[1]["content"] is cliente.requisicoes[1]["messages"][1]["content"]


def test_replanejamento_multiturno():
    agente = Agente(ClienteRoteirizado(roteiro_q11()))
    agente.processar(PEDIDO_Q11)
    resposta = agente.processar(PEDIDO_NOVO)
    assert set(agente.agenda.atividades) == {"A", "B", "C", "D", "E"}
    assert [(p["atividade"], p["inicio"], p["fim"]) for p in resposta.resumo["plano"]][:2] == [
        ("E", "14:00", "14:30"), ("A", "14:30", "16:00")]
    assert resposta.resumo["verificacao"]["valido"]


def test_erro_de_ferramenta_vira_tool_result_com_is_error():
    cliente = ClienteRoteirizado([
        mensagem(chamada("definir_janela", {"inicio": "25:00", "fim": "18:00"}),
                 chamada("ferramenta_inexistente", {})),
        mensagem(texto("Não consegui entender o horário de início.")),
    ])
    resposta = Agente(cliente).processar("das 25h às 18h")
    resultados = ultimos_resultados(cliente.requisicoes[1])
    assert [r["is_error"] for r in resultados] == [True, True]
    assert "horário inválido" in resultados[0]["content"]
    assert "ferramenta desconhecida" in resultados[1]["content"]
    assert resposta.texto == "Não consegui entender o horário de início."


def test_planejar_sem_dados_e_erro():
    cliente = ClienteRoteirizado([mensagem(chamada("planejar_agenda", {})), mensagem(texto("ok"))])
    Agente(cliente).processar("planeje")
    assert "defina a janela" in ultimos_resultados(cliente.requisicoes[1])[0]["content"]


def test_para_em_end_turn_sem_chamar_ferramentas():
    cliente = ClienteRoteirizado([mensagem(texto("Qual a duração da correção?"))])
    resposta = Agente(cliente).processar("organize meu dia")
    assert resposta.texto == "Qual a duração da correção?" and resposta.trace == []
    assert len(cliente.requisicoes) == 1


def test_lembra_de_planejar_quando_a_agenda_mudou():
    cliente = ClienteRoteirizado([
        mensagem(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"}),
                 chamada("registrar_atividades", {"atividades": ATIVIDADES_Q11})),
        mensagem(texto("Faça A primeiro.")),  # respondeu sem planejar
        mensagem(chamada("planejar_agenda", {})),
        mensagem(texto("Plano calculado.")),
    ])
    resposta = Agente(cliente).processar(PEDIDO_Q11)
    assert cliente.requisicoes[2]["messages"][-1] == {"role": "user", "content": LEMBRETE_PLANEJAR}
    assert resposta.texto == "Plano calculado." and resposta.resumo is not None


def test_blocos_de_pensamento_sao_preservados_no_historico():
    pensamento = BetaThinkingBlock(type="thinking", thinking="", signature="sig")
    cliente = ClienteRoteirizado([mensagem(pensamento, texto("ok"), stop_reason="end_turn")])
    agente = Agente(cliente)
    resposta = agente.processar("oi")
    assert agente.historico[-1]["content"][0] is pensamento and resposta.texto == "ok"


@pytest.mark.parametrize("motivo", ["refusal", "max_tokens"])
def test_recusa_e_corte_desfazem_o_turno(motivo):
    cliente = ClienteRoteirizado([
        mensagem(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"})),
        mensagem(texto("..."), stop_reason=motivo),
    ])
    agente = Agente(cliente)
    resposta = agente.processar("pedido")
    assert resposta.stop_reason == motivo
    assert agente.historico == [] and agente.agenda.janela is None


def test_erro_do_llm_desfaz_o_turno():
    class ClienteQueFalha:
        def criar_mensagem(self, **_):
            raise ErroLLM("falha de conexão com a API")

    agente = Agente(ClienteQueFalha())
    with pytest.raises(ErroLLM):
        agente.processar("pedido")
    assert agente.historico == []


def test_limite_de_iteracoes():
    cliente = ClienteRoteirizado([mensagem(chamada("remover_atividade", {"id": "X"})) for _ in range(3)])
    agente = Agente(cliente, max_iteracoes=3)
    with pytest.raises(ErroLLM, match="3 chamadas"):
        agente.processar("pedido")
    assert agente.historico == []


# ---- cliente real com transporte HTTP falso (sem chave, sem rede) ----------------------------

def cliente_http(status, corpo, capturadas):
    def responder(request):
        capturadas.append(request)
        return httpx2.Response(status, json=corpo)

    sdk = anthropic.Anthropic(api_key="sk-teste", max_retries=0,
                              http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(responder)))
    return ClienteAnthropic(client=sdk, esforco="low")


def test_requisicao_enviada_ao_claude():
    corpo = {"id": "msg_1", "type": "message", "role": "assistant", "model": MODELO,
             "content": [{"type": "tool_use", "id": "toolu_1", "name": "planejar_agenda", "input": {}}],
             "stop_reason": "tool_use", "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}
    capturadas = []
    resposta = cliente_http(200, corpo, capturadas).criar_mensagem(
        system="s", tools=FERRAMENTAS, messages=[{"role": "user", "content": "oi"}])
    assert resposta.stop_reason == "tool_use" and resposta.content[0].input == {}

    req = capturadas[0]
    enviado = json.loads(req.content)
    assert BETA_FALLBACK in req.headers["anthropic-beta"]
    assert enviado["model"] == "claude-opus-5-5"
    assert enviado["fallbacks"] == "default"
    assert enviado["output_config"] == {"effort": "low"}
    assert "thinking" not in enviado and "tool_choice" not in enviado
    assert all(t["strict"] for t in enviado["tools"])


@pytest.mark.parametrize("status, trecho", [(401, "chave"), (429, "limite"), (400, "rejeitada"), (529, "erro da API")])
def test_erros_http_viram_erro_llm(status, trecho):
    corpo = {"type": "error", "error": {"type": "x", "message": "detalhe"}}
    with pytest.raises(ErroLLM, match=trecho):
        cliente_http(status, corpo, []).criar_mensagem(system="s", tools=[], messages=[])


def test_nao_insiste_em_planejar_sem_atividades():
    cliente = ClienteRoteirizado([mensagem(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"})),
                                  mensagem(texto("Quais são as atividades?"))])
    resposta = Agente(cliente).processar("Estou livre das 14h às 18h.")
    assert resposta.texto == "Quais são as atividades?" and len(cliente.requisicoes) == 2
