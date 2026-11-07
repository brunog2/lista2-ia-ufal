"""Testes do cliente Gemini sem rede: um cliente falso devolve objetos reais do SDK google-genai."""
import pytest
from google.genai import errors, types

from agente import Agente, ErroLLM
from cliente_gemini import MODELO_PRINCIPAL, MODELO_RESERVA, ClienteGemini, de_resposta, para_conteudos


def resposta(*partes, motivo="STOP"):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=list(partes)), finish_reason=motivo)])


def chamada(nome, args, id_=None):
    return types.Part(function_call=types.FunctionCall(name=nome, args=args, id=id_),
                      thought_signature=b"assinatura")


def erro_api(codigo):
    return errors.APIError(codigo, {"error": {"code": codigo, "message": "falhou", "status": "X"}})


class Modelos:
    """Imita ``client.models``: devolve (ou levanta) os itens do roteiro e registra cada chamada."""

    def __init__(self, roteiro):
        self.roteiro, self.chamadas = list(roteiro), []

    def generate_content(self, *, model, contents, config):
        self.chamadas.append({"model": model, "contents": contents, "config": config})
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ClienteFalso:
    def __init__(self, roteiro):
        self.models = Modelos(roteiro)


def cliente(roteiro):
    falso = ClienteFalso(roteiro)
    return ClienteGemini(client=falso), falso.models


def test_chamada_de_ferramenta_vira_tool_use():
    msg = de_resposta(resposta(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"})), "m")
    assert msg.stop_reason == "tool_use"
    [bloco] = msg.content
    assert (bloco.type, bloco.name, bloco.input) == ("tool_use", "definir_janela", {"inicio": "14:00", "fim": "18:00"})
    assert bloco.id


@pytest.mark.parametrize("motivo, esperado", [("STOP", "end_turn"), ("MAX_TOKENS", "max_tokens"),
                                              ("SAFETY", "refusal"), ("PROHIBITED_CONTENT", "refusal")])
def test_motivos_de_parada(motivo, esperado):
    assert de_resposta(resposta(types.Part(text="oi"), motivo=motivo), "m").stop_reason == esperado


def test_pedido_bloqueado_sem_candidatos_e_recusa():
    assert de_resposta(types.GenerateContentResponse(candidates=[]), "m").stop_reason == "refusal"


def test_chamada_malformada_vira_erro():
    with pytest.raises(ErroLLM):
        de_resposta(resposta(types.Part(text=""), motivo="MALFORMED_FUNCTION_CALL"), "m")


def test_historico_preserva_parte_original_e_liga_resultado_a_chamada():
    parte = chamada("planejar_agenda", {}, id_="call-1")
    msg = de_resposta(resposta(parte), "m")
    historico = [
        {"role": "user", "content": "organize meu dia"},
        {"role": "assistant", "content": msg.content},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": msg.content[0].id,
                                      "content": '{"plano": []}', "is_error": False}]},
    ]
    usuario, modelo, retorno = para_conteudos(historico)
    assert usuario.role == "user" and usuario.parts[0].text == "organize meu dia"
    assert modelo.role == "model" and modelo.parts[0] is parte  # thought_signature segue intacta
    fr = retorno.parts[0].function_response
    assert (fr.name, fr.id, fr.response) == ("planejar_agenda", "call-1", {"resultado": '{"plano": []}'})


def test_resultado_com_erro_usa_chave_erro():
    msg = de_resposta(resposta(chamada("remover_atividade", {"id": "Z"})), "m")
    historico = [{"role": "assistant", "content": msg.content},
                 {"role": "user", "content": [{"type": "tool_result", "tool_use_id": msg.content[0].id,
                                               "content": "Erro: não existe", "is_error": True}]}]
    assert para_conteudos(historico)[1].parts[0].function_response.response == {"erro": "Erro: não existe"}


def test_usa_modelo_principal_quando_ele_responde():
    c, modelos = cliente([resposta(types.Part(text="ok"))])
    c.criar_mensagem(system="s", tools=[], messages=[{"role": "user", "content": "oi"}])
    assert [ch["model"] for ch in modelos.chamadas] == [MODELO_PRINCIPAL]
    assert c.modelo_usado == MODELO_PRINCIPAL
    config = modelos.chamadas[0]["config"]
    assert config.system_instruction == "s" and config.automatic_function_calling.disable is True


@pytest.mark.parametrize("codigo", [404, 429, 500, 503])
def test_cai_para_o_modelo_de_reserva(codigo):
    c, modelos = cliente([erro_api(codigo), resposta(types.Part(text="ok"))])
    msg = c.criar_mensagem(system="s", tools=[], messages=[{"role": "user", "content": "oi"}])
    assert [ch["model"] for ch in modelos.chamadas] == [MODELO_PRINCIPAL, MODELO_RESERVA]
    assert msg.model == MODELO_RESERVA and c.modelo_usado == MODELO_RESERVA


def test_falha_nos_dois_modelos_vira_erro_com_detalhes():
    c, _ = cliente([erro_api(429), erro_api(503)])
    with pytest.raises(ErroLLM, match=MODELO_RESERVA):
        c.criar_mensagem(system="s", tools=[], messages=[{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("codigo", [400, 401, 403])
def test_erro_do_pedido_nao_tenta_reserva(codigo):
    c, modelos = cliente([erro_api(codigo)])
    with pytest.raises(ErroLLM):
        c.criar_mensagem(system="s", tools=[], messages=[{"role": "user", "content": "oi"}])
    assert len(modelos.chamadas) == 1


def test_ferramentas_viram_declaracoes_com_json_schema():
    from agente import FERRAMENTAS

    c, modelos = cliente([resposta(types.Part(text="ok"))])
    c.criar_mensagem(system="s", tools=FERRAMENTAS, messages=[{"role": "user", "content": "oi"}])
    declaracoes = modelos.chamadas[0]["config"].tools[0].function_declarations
    assert [d.name for d in declaracoes] == [t["name"] for t in FERRAMENTAS]
    assert declaracoes[1].parameters_json_schema == FERRAMENTAS[1]["input_schema"]


def test_agente_completo_com_gemini_falso():
    roteiro = [
        resposta(chamada("definir_janela", {"inicio": "14:00", "fim": "18:00"}),
                 chamada("registrar_atividades", {"atividades": [{
                     "id": "A", "nome": "Aula", "duracao_min": 90.0, "prioridade": "alta", "prazo_dias": 0,
                     "prazo_hora": None, "horario_fixo": None, "divisivel": False, "bloco_minimo_min": None}]})),
        resposta(chamada("planejar_agenda", {})),
        resposta(types.Part(text="Plano pronto.")),
    ]
    c, modelos = cliente(roteiro)
    r = Agente(c).processar("preparar aula de 90 min entre 14h e 18h")
    assert r.texto == "Plano pronto." and r.stop_reason == "end_turn"
    assert [t.nome for t in r.trace] == ["definir_janela", "registrar_atividades", "planejar_agenda"]
    assert not any(t.erro for t in r.trace) and r.resumo is not None
    # a 2ª requisição leva as duas respostas de ferramenta numa única mensagem do usuário
    ultima = modelos.chamadas[1]["contents"][-1]
    assert [p.function_response.name for p in ultima.parts] == ["definir_janela", "registrar_atividades"]
