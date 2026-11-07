"""Recomendador de atividades físicas apoiado em ontologia OWL 2 e HermiT (Questão 9).

Fluxo de uma consulta:

1. carrega ``ontologia_atividades_fisicas.owl`` num World novo;
2. cria o indivíduo ``usuario_consulta`` com os fatos informados;
3. roda o HermiT, que classifica o usuário (``UsuarioIdoso``...), classifica as
   atividades (``AtividadeAdequadaParaIdoso``...) e deduz, por cadeias de
   propriedades, ``temAtividadeCandidata`` e ``naoDevePraticar``;
4. filtra as candidatas pelas exigências de segurança do perfil e pelas
   contraindicações e ordena as restantes por uma pontuação explicada.

Uso interativo: ``python recomendador_atividades.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from owlready2 import OwlReadyInconsistentOntologyError, ThingClass

from ontologia_atividades import ARQUIVO_OWL
from raciocinio_owl import carregar_ontologia, raciocinar_hermit
from sintaxe_owl import manchester, propriedades_em

PESO_OBJETIVO = 3
PESO_AMBIENTE = 1
BONUS_ORCAMENTO = 1
PENALIDADE_ORCAMENTO = -2
AMBIENTES = {"ar livre": "AtividadeAoArLivre", "fechado": "AtividadeEmAmbienteFechado",
             "indiferente": None}


@dataclass
class PerfilUsuario:
    """Dados informados pelo usuário. ``condicoes=None`` significa "não informou"."""

    nome: str
    idade: int
    peso_kg: float
    altura_m: float
    minutos_ativos_por_semana: int
    meses_de_experiencia: int
    objetivos: list[str]
    condicoes: list[str] | None = None
    orcamento_mensal: float = 0.0
    prefere_ambiente: str = "indiferente"

    @property
    def imc(self) -> float:
        return round(self.peso_kg / self.altura_m ** 2, 1)


@dataclass
class ItemRecomendado:
    atividade: str
    rotulo: str
    pontuacao: int
    motivos: list[str]
    classes_inferidas: list[str]


@dataclass
class Recomendacao:
    """Resultado de uma consulta, com todos os elementos usados na decisão."""

    usuario: str
    fatos: list[str]
    perfis: list[str]
    exigencias: list[str]
    contraindicacoes: dict[str, list[str]]
    recomendadas: list[ItemRecomendado]
    descartadas: dict[str, list[str]]
    avisos: list[str] = field(default_factory=list)
    segundos_reasoner: float = 0.0


def _rotulo(entidade) -> str:
    return str(entidade.label[0]) if entidade.label else entidade.name


def _valores(individuo, prop) -> str:
    valores = getattr(individuo, prop.python_name)
    valores = valores if isinstance(valores, list) else [valores]
    return ", ".join(_rotulo(v) if hasattr(v, "label") else str(v) for v in valores) or "(nenhum)"


def _fatos(individuo, classe: ThingClass) -> str:
    """Valores do indivíduo para as propriedades citadas na definição da classe."""
    props = dict.fromkeys(p for eq in classe.equivalent_to for p in propriedades_em(eq))
    return "; ".join(f"{p.name} = {_valores(individuo, p)}" for p in props)


def _evidencia(individuo, classe: ThingClass) -> str:
    """Definição da classe em Manchester seguida dos fatos do indivíduo."""
    return f"{classe.name} ≡ {manchester(classe.equivalent_to[0])}  |  {_fatos(individuo, classe)}"


def _validar(perfil: PerfilUsuario, onto) -> None:
    erros = []
    if not 5 <= perfil.idade <= 120:
        erros.append("idade deve estar entre 5 e 120 anos")
    if not (20 <= perfil.peso_kg <= 400 and 0.5 <= perfil.altura_m <= 2.5):
        erros.append("peso (20 a 400 kg) ou altura (0,5 a 2,5 m) fora da faixa")
    if perfil.minutos_ativos_por_semana < 0 or perfil.meses_de_experiencia < 0 or perfil.orcamento_mensal < 0:
        erros.append("minutos, meses e orçamento não podem ser negativos")
    if perfil.prefere_ambiente not in AMBIENTES:
        erros.append(f"ambiente deve ser um de {sorted(AMBIENTES)}")
    if not perfil.objetivos:
        erros.append("informe pelo menos um objetivo")
    for nome in perfil.objetivos:
        if not isinstance(onto[nome], onto.Objetivo):
            erros.append(f"objetivo desconhecido: {nome}")
    for nome in perfil.condicoes or []:
        if not isinstance(onto[nome], onto.CondicaoDeSaude):
            erros.append(f"condição desconhecida: {nome}")
    if erros:
        raise ValueError("; ".join(erros))


def _registrar_usuario(perfil: PerfilUsuario, onto):
    u = onto.Usuario("usuario_consulta", namespace=onto)
    u.label = [perfil.nome]
    u.idade, u.imc = perfil.idade, perfil.imc
    u.minutosAtivosPorSemana = perfil.minutos_ativos_por_semana
    u.mesesDeExperiencia = perfil.meses_de_experiencia
    u.orcamentoMensal, u.prefereAmbiente = perfil.orcamento_mensal, perfil.prefere_ambiente
    u.temObjetivo = [onto[o] for o in perfil.objetivos]
    if perfil.condicoes is not None:
        u.temCondicao = [onto[c] for c in perfil.condicoes]
        if not perfil.condicoes:  # "nenhuma" declarada: fecha o mundo para temCondicao
            u.is_a.append(onto.temCondicao.max(0, onto.CondicaoDeSaude))
    return u


def _explicar_veto(u, atividade, onto, sobrecarga_declarada: dict) -> list[str]:
    """Reconstrói o caminho da cadeia temCondicao ∘ contraindica deduzida pelo HermiT."""
    caminhos = []
    for cond in u.temCondicao:
        if cond not in atividade.contraindicadaPara:
            continue
        for parte in cond.afeta:
            if parte not in atividade.sobrecarrega:
                continue
            declaradas = sobrecarga_declarada[atividade]
            via = next((q for q in declaradas if parte in q.INDIRECT_parteDe), None)
            if parte in declaradas:
                origem = "fato declarado"
            elif via is not None:
                origem = (f"sobrecarrega {_rotulo(via)}, que é parteDe {_rotulo(parte)} "
                          "(parteDe transitiva + cadeia sobrecarrega ∘ parteDe ⊑ sobrecarrega)")
            else:
                origem = (f"inferido: é AtividadeVigorosa (gastoMET = {atividade.gastoMET}) e "
                          "AtividadeVigorosa ⊑ sobrecarrega value sistema_cardiovascular")
            caminhos.append(
                f"{_rotulo(cond)} afeta {_rotulo(parte)}; {_rotulo(atividade)} sobrecarrega "
                f"{_rotulo(parte)} [{origem}] ⇒ contraindicadaPara (sobrecarrega ∘ afetadaPor) "
                "⇒ naoDevePraticar (temCondicao ∘ contraindica)")
    return caminhos


def recomendar(perfil: PerfilUsuario, caminho_owl: Path = ARQUIVO_OWL) -> Recomendacao:
    """Consulta a ontologia, roda o HermiT e devolve recomendações justificadas."""
    world, onto = carregar_ontologia(caminho_owl)
    _validar(perfil, onto)
    u = _registrar_usuario(perfil, onto)
    atividades = list(onto.AtividadeFisica.instances())
    sobrecarga_declarada = {a: list(a.sobrecarrega) for a in atividades}
    try:
        segundos = raciocinar_hermit(world)
    except OwlReadyInconsistentOntologyError as erro:
        raise ValueError("os dados informados tornam a ontologia inconsistente") from erro

    perfis = sorted((c for c in u.INDIRECT_is_a
                     if isinstance(c, ThingClass) and c is not onto.Usuario and issubclass(c, onto.Usuario)),
                    key=lambda c: c.name)
    exigencias = [(p, t) for p in perfis for t in p.exigeAtividadeDoTipo]
    vetadas = set(u.naoDevePraticar)
    avisos = []
    if perfil.condicoes is None:
        avisos.append("Condições de saúde não informadas: pela hipótese de mundo aberto o reasoner não "
                      "assume que não existam, e nenhuma contraindicação pôde ser deduzida.")
    if onto.UsuarioSemCondicaoDeSaude in perfis:
        avisos.append("Usuário declarou não ter condições de saúde (axioma de fechamento temCondicao max 0).")

    recomendadas, descartadas = [], {}
    contraindicacoes = {_rotulo(a): _explicar_veto(u, a, onto, sobrecarga_declarada) for a in vetadas}
    for a in sorted(u.temAtividadeCandidata, key=lambda x: x.name):
        motivos_descarte = [f"contraindicada: {c}" for c in contraindicacoes.get(_rotulo(a), [])]
        motivos_descarte += [f"não foi classificada como {t.name}, exigida por {p.name} ({_fatos(a, t)})"
                             for p, t in exigencias if a not in t.instances()]
        if motivos_descarte:
            descartadas[_rotulo(a)] = motivos_descarte
            continue
        recomendadas.append(_pontuar(a, u, onto, perfil, exigencias))
    recomendadas.sort(key=lambda i: (-i.pontuacao, onto[i.atividade].custoMensal, i.rotulo))

    condicoes = "não informado" if perfil.condicoes is None else ", ".join(perfil.condicoes) or "nenhuma"
    fatos = [f"idade = {perfil.idade}", f"IMC = {perfil.imc}",
             f"minutosAtivosPorSemana = {perfil.minutos_ativos_por_semana}",
             f"mesesDeExperiencia = {perfil.meses_de_experiencia}",
             f"temObjetivo = {', '.join(perfil.objetivos)}", f"temCondicao = {condicoes}",
             f"orçamento = R$ {perfil.orcamento_mensal:.2f}", f"ambiente preferido = {perfil.prefere_ambiente}"]
    return Recomendacao(
        usuario=perfil.nome, fatos=fatos,
        perfis=[_evidencia(u, p) for p in perfis],
        exigencias=[f"{p.name} → {t.name}: {manchester(t.equivalent_to[0])}" for p, t in exigencias],
        contraindicacoes=contraindicacoes, recomendadas=recomendadas, descartadas=descartadas,
        avisos=avisos, segundos_reasoner=segundos)


def _pontuar(a, u, onto, perfil: PerfilUsuario, exigencias) -> ItemRecomendado:
    motivos, pontos = [], 0
    for obj in u.temObjetivo:
        if obj in a.atendeObjetivo:
            beneficios = [_rotulo(b) for b in a.promove if b in obj.dependeDe]
            pontos += PESO_OBJETIVO
            motivos.append(f"+{PESO_OBJETIVO} atende '{_rotulo(obj)}' (promove {', '.join(beneficios)}; "
                           "cadeia promove ∘ contribuiPara ⊑ atendeObjetivo)")
    classe_ambiente = AMBIENTES[perfil.prefere_ambiente]
    if classe_ambiente and a in onto[classe_ambiente].instances():
        pontos += PESO_AMBIENTE
        motivos.append(f"+{PESO_AMBIENTE} é {classe_ambiente} (realizada em "
                       f"{', '.join(_rotulo(l) for l in a.realizadaEm)})")
    if a.custoMensal <= perfil.orcamento_mensal:
        pontos += BONUS_ORCAMENTO
        motivos.append(f"+{BONUS_ORCAMENTO} custo R$ {a.custoMensal:.2f} cabe no orçamento")
    else:
        pontos += PENALIDADE_ORCAMENTO
        motivos.append(f"{PENALIDADE_ORCAMENTO} custo R$ {a.custoMensal:.2f} acima do orçamento")
    for p, t in exigencias:
        motivos.append(f"segura para {p.name}: classificada como {t.name} ({_fatos(a, t)})")
    inferidas = sorted(c.name for c in a.INDIRECT_is_a
                       if isinstance(c, ThingClass) and c.equivalent_to)
    return ItemRecomendado(a.name, _rotulo(a), pontos, motivos, inferidas)


def formatar(rec: Recomendacao, limite: int = 5) -> str:
    """Relatório em texto para o terminal."""
    linhas = [f"Usuário: {rec.usuario}", "Fatos informados:"]
    linhas += [f"  {f}" for f in rec.fatos]
    linhas.append(f"Perfis inferidos pelo HermiT ({rec.segundos_reasoner:.2f} s):")
    linhas += [f"  {p}" for p in rec.perfis] or ["  (nenhum perfil especial)"]
    linhas.append("Exigências de segurança (anotação exigeAtividadeDoTipo):")
    linhas += [f"  {e}" for e in rec.exigencias] or ["  (nenhuma)"]
    linhas += [f"Aviso: {a}" for a in rec.avisos]
    linhas.append("Contraindicações deduzidas (naoDevePraticar):")
    for atividade, caminhos in sorted(rec.contraindicacoes.items()):
        linhas += [f"  {atividade}: {c}" for c in caminhos]
    if not rec.contraindicacoes:
        linhas.append("  (nenhuma)")
    linhas.append(f"Recomendações ({min(limite, len(rec.recomendadas))} de {len(rec.recomendadas)} aptas):")
    for n, item in enumerate(rec.recomendadas[:limite], 1):
        linhas.append(f"  {n}. {item.rotulo} (pontuação {item.pontuacao})")
        linhas += [f"       {m}" for m in item.motivos]
    linhas.append("Candidatas descartadas:")
    for atividade, motivos in sorted(rec.descartadas.items()):
        linhas.append(f"  {atividade}")
        linhas += [f"       {m}" for m in motivos]
    if not rec.descartadas:
        linhas.append("  (nenhuma)")
    return "\n".join(linhas)


def _escolher(titulo: str, opcoes: list, permitir_vazio: bool) -> list[str] | None:
    print(titulo)
    for n, ind in enumerate(opcoes, 1):
        print(f"  {n}. {_rotulo(ind)}")
    resposta = input("Números separados por vírgula" + (" (0 = nenhuma, Enter = prefiro não informar)"
                                                          if permitir_vazio else "") + ": ").strip()
    if permitir_vazio and not resposta:
        return None
    if permitir_vazio and resposta == "0":
        return []
    return [opcoes[int(x) - 1].name for x in resposta.split(",")]


def main() -> None:
    _, onto = carregar_ontologia()
    objetivos = sorted(onto.Objetivo.instances(), key=_rotulo)
    condicoes = sorted(onto.CondicaoDeSaude.instances(), key=_rotulo)
    print("Recomendador de atividades físicas (ontologia OWL 2 + HermiT)\n")
    try:
        perfil = PerfilUsuario(
            nome=input("Nome: ").strip() or "Usuário",
            idade=int(input("Idade (anos): ")),
            peso_kg=float(input("Peso (kg): ").replace(",", ".")),
            altura_m=float(input("Altura (m): ").replace(",", ".")),
            minutos_ativos_por_semana=int(input("Minutos de exercício por semana hoje: ")),
            meses_de_experiencia=int(input("Há quantos meses pratica exercícios com regularidade: ")),
            objetivos=_escolher("Objetivos:", objetivos, permitir_vazio=False) or [],
            condicoes=_escolher("Condições de saúde:", condicoes, permitir_vazio=True),
            orcamento_mensal=float(input("Orçamento mensal (R$): ").replace(",", ".")),
            prefere_ambiente=input("Ambiente preferido (ar livre / fechado / indiferente): ").strip().lower()
            or "indiferente",
        )
        print("\n" + formatar(recomendar(perfil)))
    except (ValueError, IndexError) as erro:
        raise SystemExit(f"Entrada inválida: {erro}")


if __name__ == "__main__":
    main()
