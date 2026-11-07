"""Interface de chat em linha de comando do assistente de agenda acadêmica (Q12).

Uso:
    export ANTHROPIC_API_KEY=...        # necessário para conversar com o Claude
    python agente_cli.py                # chat interativo
    python agente_cli.py --demo         # simulação roteirizada do cenário da Q11, sem chave

Comandos no chat: /agenda mostra o estado atual; sair (ou Ctrl+D) encerra.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from agente import Agente, ClienteAnthropic, ErroLLM, RespostaAgente


def _resumir(texto: str, limite: int = 160) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 3] + "..."


def mostrar(resposta: RespostaAgente, com_trace: bool = True) -> None:
    if com_trace and resposta.trace:
        print("  trace de ferramentas:")
        for c in resposta.trace:
            estado = "ERRO" if c.erro else "ok"
            print(f"    - {c.nome}({_resumir(json.dumps(c.entrada, ensure_ascii=False), 90)}) -> {estado}: "
                  f"{_resumir(c.resultado, 110)}")
    print(f"\nassistente> {resposta.texto}\n")


def demo(com_trace: bool) -> None:
    from simulacao import PEDIDO_NOVO, PEDIDO_Q11, ClienteRoteirizado, roteiro_q11

    print("Modo demonstração: as chamadas de ferramenta foram roteirizadas à mão (não há LLM nesta execução).\n"
          "Planejador, verificador e explicações são reais.\n")
    agente = Agente(ClienteRoteirizado(roteiro_q11()))
    for pedido in (PEDIDO_Q11, PEDIDO_NOVO):
        print(f"professor> {pedido}")
        mostrar(agente.processar(pedido), com_trace)


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente de agenda acadêmica (Q12)")
    parser.add_argument("--demo", action="store_true", help="roda a simulação roteirizada da Q11, sem chave de API")
    parser.add_argument("--esforco", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                        help="output_config.effort enviado ao Claude (padrão: medium)")
    parser.add_argument("--sem-trace", action="store_true", help="não mostra as chamadas de ferramentas")
    args = parser.parse_args()
    com_trace = not args.sem_trace

    if args.demo:
        demo(com_trace)
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY não definida. Exporte a chave ou rode com --demo.", file=sys.stderr)
        return 1

    agente = Agente(ClienteAnthropic(esforco=args.esforco))
    print("Assistente de agenda acadêmica. Descreva suas atividades e o tempo disponível. "
          "Digite 'sair' para encerrar.\n")
    while True:
        try:
            pedido = input("professor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not pedido:
            continue
        if pedido.lower() in {"sair", "exit", "quit"}:
            return 0
        if pedido == "/agenda":
            print(json.dumps(agente.agenda.estado(), ensure_ascii=False, indent=2))
            continue
        try:
            mostrar(agente.processar(pedido), com_trace)
        except ErroLLM as e:
            print(f"[erro] {e}. O turno foi desfeito; tente de novo.\n", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
