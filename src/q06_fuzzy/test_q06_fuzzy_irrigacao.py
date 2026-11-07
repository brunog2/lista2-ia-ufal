import numpy as np
import pytest

import fuzzy_irrigacao as fi

# Aviso interno do skfuzzy 0.5 com NumPy 2.x (np.maximum com 3 argumentos posicionais).
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning:skfuzzy")

SAIDAS = list(fi.TERMOS["tempo"])
RNG = np.random.default_rng(42)
AMOSTRAS = [(RNG.uniform(0, 100), RNG.uniform(15, 40), RNG.uniform(0, 100)) for _ in range(30)]


@pytest.fixture(scope="module")
def sistema():
    return fi.criar_sistema_skfuzzy()


def test_base_de_regras_completa():
    combinacoes = {(r.umidade, r.temperatura, r.chuva) for r in fi.REGRAS}
    assert len(fi.REGRAS) == len(combinacoes) == 27


def test_regras_monotonas_na_tabela():
    """Mais umidade ou mais chuva nunca aumenta o tempo; mais calor nunca reduz."""
    nivel = {(r.umidade, r.temperatura, r.chuva): SAIDAS.index(r.tempo) for r in fi.REGRAS}
    u, t, c = (list(fi.TERMOS[v]) for v in fi.ENTRADAS)
    for (ui, ti, ci), k in nivel.items():
        iu, it, ic = u.index(ui), t.index(ti), c.index(ci)
        if iu + 1 < 3:
            assert nivel[(u[iu + 1], ti, ci)] <= k
        if it + 1 < 3:
            assert nivel[(ui, t[it + 1], ci)] >= k
        if ic + 1 < 3:
            assert nivel[(ui, ti, c[ic + 1])] <= k


@pytest.mark.parametrize("u,t,c", AMOSTRAS)
def test_centroide_manual_igual_skfuzzy(sistema, u, t, c):
    agregado = fi.inferir(u, t, c).agregado
    manual = fi.centroide_manual(fi.UNIVERSOS["tempo"], agregado)
    assert manual == pytest.approx(fi.defuzzificar(agregado), abs=1e-3)
    assert manual == pytest.approx(fi.tempo_irrigacao_skfuzzy(sistema, u, t, c), abs=1e-3)


@pytest.mark.parametrize("metodo", ["centroid", "bisector", "mom", "som", "lom"])
@pytest.mark.parametrize("u,t,c", AMOSTRAS[:10] + [(0, 15, 0), (100, 40, 100), (-20, 50, 130)])
def test_saida_dentro_do_universo(u, t, c, metodo):
    assert 0 <= fi.tempo_irrigacao(u, t, c, metodo) <= 60


def test_tendencia_monotona_entre_extremos():
    assert fi.tempo_irrigacao(0, 30, 10) > fi.tempo_irrigacao(50, 30, 10) > fi.tempo_irrigacao(100, 30, 10)
    assert fi.tempo_irrigacao(40, 15, 10) < fi.tempo_irrigacao(40, 27, 10) < fi.tempo_irrigacao(40, 40, 10)
    assert fi.tempo_irrigacao(40, 30, 0) > fi.tempo_irrigacao(40, 30, 50) > fi.tempo_irrigacao(40, 30, 100)


def test_monotonia_aproximada_em_varreduras():
    """O centroide com agregação max admite pequenas inversões locais (ver README)."""
    xs = {v: np.linspace(fi.UNIVERSOS[v][0], fi.UNIVERSOS[v][-1], 41) for v in fi.ENTRADAS}
    sinal = {"umidade": -1, "temperatura": 1, "chuva": -1}
    base = {"umidade": 40, "temperatura": 30, "chuva": 30}
    for var, s in sinal.items():
        ys = np.array([fi.tempo_irrigacao(**{**base, var: x}) for x in xs[var]])
        assert np.min(s * np.diff(ys)) > -2.0


def test_entrada_fora_do_universo_e_saturada():
    assert fi.tempo_irrigacao(-10, 55, -5) == pytest.approx(fi.tempo_irrigacao(0, 40, 0))


def test_nenhuma_regra_disparando():
    regras_secas = [r for r in fi.REGRAS if r.umidade == "seca"]
    resultado = fi.inferir(90, 30, 10, regras=regras_secas)
    assert not resultado.forcas.any()
    with pytest.raises(ValueError):
        fi.defuzzificar(resultado.agregado)
    with pytest.raises(ValueError):
        fi.centroide_manual(fi.UNIVERSOS["tempo"], resultado.agregado)


@pytest.mark.parametrize("u,t,c", AMOSTRAS[:10])
def test_base_compacta_manual_igual_skfuzzy(u, t, c):
    sistema = fi.criar_sistema_skfuzzy(regras=fi.REGRAS_COMPACTAS)
    manual = fi.tempo_irrigacao(u, t, c, regras=fi.REGRAS_COMPACTAS)
    assert manual == pytest.approx(fi.tempo_irrigacao_skfuzzy(sistema, u, t, c), abs=1e-3)


def test_base_compacta_cobre_as_mesmas_combinacoes():
    assert str(fi.REGRAS_COMPACTAS[-1]) == "SE umidade é úmida ENTÃO tempo é nenhum"
    for u, t, c in [(10, 20, 10), (50, 30, 50), (90, 38, 90)]:
        assert fi.inferir(u, t, c, regras=fi.REGRAS_COMPACTAS).forcas.any()
