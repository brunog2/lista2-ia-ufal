"""Interface de linha de comando do sistema CBR de apoio ao diagnóstico (Q7).

Executa o ciclo completo (Retrieve, Reuse, Revise, Retain) para cada consulta.
Por padrão trabalha sobre ``base_casos_local.json``, uma cópia da base versionada
criada na primeira execução, para que a demonstração não altere ``base_casos.json``.

Uso:
    python src/q07_cbr/cbr_cli.py [--base ARQUIVO] [--k 3] [--metrica ponderada]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Callable

from cbr_casos import AVISO, INICIOS, INTENSIDADES, SINTOMAS, Problema
from cbr_ciclo import SistemaCBR, Sugestao, revisar_interativo
from cbr_similaridade import METRICAS_SINTOMAS, similaridades_locais

PASTA = Path(__file__).parent
BASE_ORIGINAL = PASTA / "base_casos.json"
BASE_LOCAL = PASTA / "base_casos_local.json"


def interpretar_sintomas(texto: str) -> dict[str, int]:
    """Lê 'nome:intensidade' ou 'número:intensidade' separados por vírgula.

    Sem intensidade, assume 2 (moderada). Ex.: 'dor_retroorbital:3, 1:2, tosse'.
    """
    nomes = list(SINTOMAS)
    sintomas: dict[str, int] = {}
    for parte in filter(None, (p.strip() for p in texto.split(","))):
        nome, _, intensidade = (x.strip() for x in parte.partition(":"))
        if nome.isdigit():
            if not 1 <= int(nome) <= len(nomes):
                raise ValueError(f"Número de sintoma inválido: {nome}")
            nome = nomes[int(nome) - 1]
        if nome not in SINTOMAS:
            raise ValueError(f"Sintoma desconhecido: {nome}")
        if intensidade not in ("", *map(str, INTENSIDADES)):
            raise ValueError("Intensidade deve ser 1, 2 ou 3.")
        sintomas[nome] = int(intensidade or 2)
    if not sintomas:
        raise ValueError("Informe pelo menos um sintoma.")
    return sintomas


def perguntar_valido(mensagem: str, converter: Callable[[str], object], padrao: str = ""):
    """Repete a pergunta até a resposta ser aceita por ``converter``."""
    while True:
        resposta = input(mensagem).strip() or padrao
        try:
            return converter(resposta)
        except ValueError as erro:
            print(f"  Entrada inválida: {erro}")


def numero(tipo: type) -> Callable[[str], float]:
    """Conversor numérico que aceita vírgula decimal e erra em português."""
    def converter(texto: str):
        try:
            return tipo(texto.replace(",", "."))
        except ValueError:
            raise ValueError(f"'{texto}' não é um número válido") from None
    return converter


def ler_inicio(texto: str) -> str:
    inicio = {"s": "subito", "g": "gradual"}.get(texto.lower()[:1], texto.lower())
    if inicio not in INICIOS:
        raise ValueError("responda s (súbito) ou g (gradual)")
    return inicio


def ler_problema() -> Problema:
    print("\nSintomas disponíveis (intensidade: 1 = leve, 2 = moderada, 3 = intensa):")
    for i, (nome, descricao) in enumerate(SINTOMAS.items(), 1):
        print(f"  {i:2d}. {nome:<22} {descricao}")
    while True:
        try:
            return Problema(
                sintomas=perguntar_valido("Sintomas (ex.: 2:3, mialgia:2): ", interpretar_sintomas),
                temperatura=perguntar_valido("Temperatura em °C [36.5]: ", numero(float), "36.5"),
                dias_sintomas=perguntar_valido("Há quantos dias começaram os sintomas: ", numero(int)),
                idade=perguntar_valido("Idade: ", numero(int)),
                inicio=perguntar_valido("Início súbito ou gradual? [s/g]: ", ler_inicio),
                alergias=tuple(a.strip().lower() for a in input("Alergias a medicamentos (vírgula, opcional): ").split(",") if a.strip()),
            )
        except ValueError as erro:
            print(f"  Dados inválidos: {erro}. Vamos recomeçar.")


def exibir_vizinhos(problema: Problema, sistema: SistemaCBR, vizinhos) -> None:
    print("\n[Retrieve] Casos mais semelhantes:")
    print(f"  {'caso':<5} {'diagnóstico':<22} {'sim':>5}  {'sint.':>5} {'temp.':>5} {'início':>6} {'dias':>5} {'idade':>5}  origem")
    for caso, sim in vizinhos:
        loc = similaridades_locais(problema, caso.problema, sistema.sim_sintomas)
        print(f"  {caso.id:<5} {caso.diagnostico:<22} {sim:5.3f}  {loc['sintomas']:5.2f} {loc['temperatura']:5.2f}"
              f" {loc['inicio']:6.2f} {loc['dias_sintomas']:5.2f} {loc['idade']:5.2f}  {caso.origem}")


def exibir_sugestao(sugestao: Sugestao) -> None:
    print(f"\n[Reuse] Diagnóstico sugerido: {sugestao.diagnostico} (confiança {sugestao.confianca:.0%})")
    print("  Votos: " + ", ".join(f"{d} = {v:.3f}" for d, v in sugestao.votos.items()))
    if sugestao.vizinhos[0][1] < 0.6:
        print("  Atenção: nenhum caso da base é muito parecido; a revisão médica é essencial.")
    print(f"  Tratamento (adaptado do caso {sugestao.caso_fonte.id}):")
    for item in sugestao.tratamento:
        print(f"   - {item}")
    for ajuste in sugestao.ajustes:
        print(f"   * ajuste: {ajuste}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sistema CBR de apoio ao diagnóstico (Q7)")
    parser.add_argument("--base", type=Path, default=BASE_LOCAL, help="arquivo JSON da base de trabalho")
    parser.add_argument("--k", type=int, default=3, help="número de casos recuperados")
    parser.add_argument("--metrica", choices=METRICAS_SINTOMAS, default="ponderada",
                        help="similaridade local dos sintomas")
    args = parser.parse_args(argv)
    if not args.base.exists():
        shutil.copy(BASE_ORIGINAL, args.base)
        print(f"Base de trabalho criada a partir de {BASE_ORIGINAL.name}: {args.base}")

    sistema = SistemaCBR.de_arquivo(args.base, k=args.k, sim_sintomas=METRICAS_SINTOMAS[args.metrica])
    print(AVISO)
    print(f"Base: {args.base} ({len(sistema.casos)} casos, "
          f"{len({c.diagnostico for c in sistema.casos})} diagnósticos), k = {args.k}, métrica = {args.metrica}")
    try:
        while True:
            problema = ler_problema()
            vizinhos = sistema.recuperar(problema)
            exibir_vizinhos(problema, sistema, vizinhos)
            sugestao = sistema.reutilizar(problema, vizinhos)
            exibir_sugestao(sugestao)
            print("\n[Revise]")
            caso = revisar_interativo(problema, sugestao)
            if input("\n[Retain] Guardar este caso na base? [s/n] ").strip().lower().startswith("s"):
                r = sistema.reter(caso)
                if r.retido:
                    print(f"  Caso retido como {r.id_caso} (base agora com {len(sistema.casos)} casos).")
                else:
                    print(f"  Caso quase idêntico a {r.id_caso} (similaridade {r.similaridade:.3f}); "
                          "registrada uma confirmação em vez de duplicar.")
            if not input("\nNova consulta? [s/n] ").strip().lower().startswith("s"):
                break
    except (EOFError, KeyboardInterrupt):
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
