"""Explicações estruturadas do plano (componente de explicabilidade da Q12).

Tudo aqui é calculado a partir do planejador e do verificador. O LLM recebe
este resumo como resultado de ferramenta e só redige o texto final; os fatos
(horários, utilidades, motivos) vêm daqui. ``texto_explicacao`` gera uma versão
em texto sem LLM, usada no modo de demonstração e como referência.
"""
from __future__ import annotations

from dataclasses import replace

from planejador import PESO_PRIORIDADE, Atividade, Plano, Segmento, min_para_hhmm, planejar, urgencia, verificar


def _num(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def _intervalo(inicio: int, fim: int) -> str:
    return f"{min_para_hhmm(inicio)}-{min_para_hhmm(fim)}"


def intervalos_livres(ocupados: list[tuple[int, int]], inicio: int, fim: int) -> list[tuple[int, int]]:
    livres, t = [], inicio
    for a, b in sorted(ocupados):
        if a > t:
            livres.append((t, a))
        t = max(t, b)
    if t < fim:
        livres.append((t, fim))
    return livres


def _mudancas(antes: dict[str, int], depois: dict[str, int]) -> list[dict]:
    return [{"atividade": i, "minutos_antes": antes.get(i, 0), "minutos_depois": depois.get(i, 0)}
            for i in sorted(set(antes) | set(depois)) if antes.get(i, 0) != depois.get(i, 0)]


def _contrafactual(a: Atividade, status: str, atividades: list[Atividade], inicio: int, fim: int,
                   plano: Plano, livres_janela: list[tuple[int, int]], passo: int) -> dict:
    """Replaneja exigindo a atividade (inteira se parcial ou não divisível) e mede a perda de utilidade."""
    exigido = a.duracao if (status == "parcial" or not a.divisivel) else a.bloco
    forcadas = [replace(x, minimo_exigido=exigido) if x.id == a.id else x for x in atividades]
    alt = planejar(forcadas, inicio, fim, passo).melhor
    pergunta = f"e se {a.id} recebesse pelo menos {exigido} min?"
    if alt is None:
        maior = max((b - t for t, b in livres_janela), default=0)
        if not a.divisivel and a.duracao > maior:
            motivo = (f"não cabe: precisa de {a.duracao} min contínuos e o maior intervalo livre "
                      f"entre os compromissos fixos tem {maior} min")
        elif a.prazo_hora is not None:
            motivo = f"não cabe antes do prazo das {min_para_hhmm(a.prazo_hora)}"
        else:
            motivo = f"não cabe: o tempo livre total da janela não comporta {exigido} min dessa atividade"
        return {"pergunta": pergunta, "viavel": False, "motivo": motivo}
    return {
        "pergunta": pergunta,
        "viavel": True,
        "utilidade": round(alt.utilidade, 4),
        "perda": round(plano.utilidade - alt.utilidade, 4),
        "mudancas": _mudancas(plano.minutos, alt.minutos),
        "segmentos": [{"atividade": s.atividade_id, "inicio": min_para_hhmm(s.inicio), "fim": min_para_hhmm(s.fim)}
                      for s in alt.segmentos],
    }


def explicar(atividades: list[Atividade], inicio: int, fim: int, passo: int = 15) -> dict:
    """Planeja, verifica e devolve um resumo JSON-serializável com as justificativas."""
    resultado = planejar(atividades, inicio, fim, passo)
    plano = resultado.melhor
    if plano is None:
        raise ValueError("nenhum plano atende às exigências mínimas informadas")
    segs = list(plano.segmentos)
    fixas = [a for a in atividades if a.fixa]
    livres_janela = intervalos_livres([(a.inicio_fixo, a.inicio_fixo + a.duracao) for a in fixas], inicio, fim)
    ociosos = intervalos_livres([(s.inicio, s.fim) for s in segs], inicio, fim)
    por_id = {a.id: a for a in atividades}
    nome_de_fixa_em = {a.inicio_fixo: a for a in fixas}

    detalhes = []
    for a in atividades:
        blocos = [s for s in segs if s.atividade_id == a.id]
        feitos = plano.minutos.get(a.id, 0)
        status = "fixa" if a.fixa else "fora" if feitos == 0 else "completa" if feitos == a.duracao else "parcial"
        motivos = [f"valor {_num(a.valor)} = peso {PESO_PRIORIDADE[a.prioridade]} (prioridade {a.prioridade}) "
                   f"x urgência {_num(urgencia(a.prazo_dias))} (prazo em {a.prazo_dias} dia(s))"]
        if status == "fixa":
            motivos.append(f"compromisso fixo {_intervalo(a.inicio_fixo, a.inicio_fixo + a.duracao)}, tratado como restrição rígida")
        for s in blocos if status != "fixa" else []:
            anterior = next((x for x in segs if x.fim == s.inicio), None)
            depois_de = "o início da janela" if s.inicio == inicio else (
                f"o fim de {anterior.atividade_id}" if anterior else "um intervalo ocioso")
            limite = ""
            if s.fim in nome_de_fixa_em:
                limite = f"; termina encostada no compromisso fixo {nome_de_fixa_em[s.fim].id}"
            elif s.fim == fim:
                limite = "; termina no fim da janela"
            if a.prazo_hora is not None and s.fim == a.prazo_hora:
                limite += f"; termina exatamente no prazo ({min_para_hhmm(a.prazo_hora)})"
            motivos.append(f"bloco {_intervalo(s.inicio, s.fim)} ({s.minutos} min), logo após {depois_de}{limite}")
        if status == "parcial":
            motivos.append(f"feita em parte: {feitos} de {a.duracao} min; {a.duracao - feitos} min ficam para depois")
        contrafactual = None
        if status in ("fora", "parcial"):
            contrafactual = _contrafactual(a, status, atividades, inicio, fim, plano, livres_janela, passo)
        detalhes.append({
            "id": a.id, "nome": a.nome, "status": status, "prioridade": a.prioridade,
            "prazo_dias": a.prazo_dias, "duracao": a.duracao, "divisivel": a.divisivel,
            "minutos": feitos, "valor": round(a.valor, 4),
            "contribuicao": round(a.valor * feitos / a.duracao, 4),
            "blocos": [{"inicio": min_para_hhmm(s.inicio), "fim": min_para_hhmm(s.fim)} for s in blocos],
            "justificativa": motivos, "contrafactual": contrafactual,
        })

    pendentes = [a for a in atividades if not a.fixa and plano.minutos[a.id] < a.duracao]
    ociosidade = []
    for t, b in ociosos:
        porque = []
        for a in pendentes:
            if not a.divisivel and plano.minutos[a.id] == 0 and a.duracao > b - t:
                porque.append(f"{a.id} precisa de {a.duracao} min contínuos")
            elif not a.divisivel and plano.minutos[a.id] > 0:
                continue  # já foi feita inteira em outro horário
            elif a.divisivel and a.bloco > b - t:
                porque.append(f"o bloco mínimo de {a.id} é {a.bloco} min")
            elif a.prazo_hora is not None and a.prazo_hora < t + min(a.bloco if a.divisivel else a.duracao, b - t):
                porque.append(f"o prazo de {a.id} ({min_para_hhmm(a.prazo_hora)}) já passou nesse horário")
        ociosidade.append({"inicio": min_para_hhmm(t), "fim": min_para_hhmm(b), "minutos": b - t,
                           "motivo": "; ".join(porque) or "nenhuma atividade pendente"})

    demanda = sum(a.duracao for a in atividades if not a.fixa)
    livre = sum(b - t for t, b in livres_janela)
    restricoes = [
        f"janela {_intervalo(inicio, fim)} ({fim - inicio} min)",
        *(f"compromisso fixo {a.id} em {_intervalo(a.inicio_fixo, a.inicio_fixo + a.duracao)}" for a in fixas),
        "intervalos livres: " + ", ".join(f"{_intervalo(t, b)} ({b - t} min)" for t, b in livres_janela),
        f"demanda das atividades flexíveis: {demanda} min; tempo livre: {livre} min"
        + ("; não há tempo para tudo" if demanda > livre else ""),
        *(f"{a.id} não pode ser interrompida" for a in atividades if not a.fixa and not a.divisivel),
        *(f"{a.id} pode ser dividida em blocos de pelo menos {a.bloco} min" for a in atividades if a.divisivel),
        *(f"{a.id} deve terminar até {min_para_hhmm(a.prazo_hora)}" for a in atividades if a.prazo_hora is not None),
    ]

    viaveis = [d for d in detalhes if d["contrafactual"] and d["contrafactual"]["viavel"]]
    melhor_alt = max(viaveis, key=lambda d: d["contrafactual"]["utilidade"], default=None)
    alternativa = None
    if melhor_alt:
        alternativa = {"forcando": melhor_alt["id"], **melhor_alt["contrafactual"]}

    return {
        "janela": {"inicio": min_para_hhmm(inicio), "fim": min_para_hhmm(fim)},
        "plano": [{"atividade": s.atividade_id, "nome": por_id[s.atividade_id].nome,
                   "inicio": min_para_hhmm(s.inicio), "fim": min_para_hhmm(s.fim), "minutos": s.minutos}
                  for s in segs],
        "utilidade": round(plano.utilidade, 4),
        "utilidade_maxima_teorica": round(sum(a.valor for a in atividades), 4),
        "atividades": detalhes,
        "ociosidade": ociosidade,
        "restricoes_ativas": restricoes,
        "segunda_melhor_alternativa": alternativa,
        "verificacao": {"valido": not (v := verificar(segs, atividades, inicio, fim)), "violacoes": v},
        "busca": resultado.estatisticas,
        "criterio_de_desempate": "com utilidades iguais, termina antes o que vale mais; depois, menos blocos",
    }


def avaliar_proposta(segmentos: list[Segmento], atividades: list[Atividade], inicio: int, fim: int,
                     passo: int = 15) -> dict:
    """Confere um plano vindo de fora (usuário ou LLM) e compara com o ótimo."""
    violacoes = verificar(segmentos, atividades, inicio, fim)
    minutos: dict[str, int] = {}
    for s in segmentos:
        minutos[s.atividade_id] = minutos.get(s.atividade_id, 0) + s.minutos
    otimo = planejar(atividades, inicio, fim, passo).melhor
    u = sum(a.valor * min(minutos.get(a.id, 0), a.duracao) / a.duracao for a in atividades)
    return {
        "valido": not violacoes,
        "violacoes": violacoes,
        "utilidade_proposta": round(u, 4) if not violacoes else None,
        "utilidade_otima": round(otimo.utilidade, 4) if otimo else None,
        "diferenca_para_otimo": _mudancas(otimo.minutos, minutos) if otimo else [],
    }


def texto_explicacao(resumo: dict) -> str:
    """Explicação em português gerada só a partir do resumo (sem LLM)."""
    j = resumo["janela"]
    linhas = [f"Plano para {j['inicio']}-{j['fim']} (utilidade {_num(resumo['utilidade'])}; "
              f"{_num(resumo['utilidade_maxima_teorica'])} se tudo coubesse):"]
    linhas += [f"  {p['inicio']}-{p['fim']}  {p['atividade']}  {p['nome']}" for p in resumo["plano"]]
    for d in resumo["atividades"]:
        if d["status"] == "parcial":
            linhas.append(f"{d['id']} ({d['nome']}) foi dividida: {d['minutos']} de {d['duracao']} min hoje, "
                          f"o restante fica para depois.")
    fora = [d for d in resumo["atividades"] if d["status"] in ("fora", "parcial")]
    if fora:
        linhas.append("Por que algo ficou de fora ou incompleto:")
    for d in fora:
        c = d["contrafactual"]
        if not c["viavel"]:
            linhas.append(f"  - {d['id']} ({d['nome']}): {c['motivo']}.")
        else:
            trocas = ", ".join(f"{m['atividade']} {m['minutos_antes']}->{m['minutos_depois']} min" for m in c["mudancas"])
            linhas.append(f"  - {d['id']} ({d['nome']}): exigir {d['id']} levaria a utilidade a "
                          f"{_num(c['utilidade'])} (perda de {_num(c['perda'])}), com as trocas {trocas}.")
    for o in resumo["ociosidade"]:
        linhas.append(f"Tempo livre não usado {o['inicio']}-{o['fim']} ({o['minutos']} min): {o['motivo']}.")
    alt = resumo["segunda_melhor_alternativa"]
    if alt:
        linhas.append(f"Segunda melhor alternativa: forçar {alt['forcando']} dá utilidade {_num(alt['utilidade'])}, "
                      f"{_num(alt['perda'])} abaixo do plano escolhido.")
    v = resumo["verificacao"]
    linhas.append("Verificador independente: nenhuma violação." if v["valido"]
                  else "Verificador independente encontrou violações: " + "; ".join(v["violacoes"]))
    return "\n".join(linhas)
