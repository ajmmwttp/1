"""単体テスト: python -m research.turn_zones.tests"""
import numpy as np
import pandas as pd

from .helpers import ema_p, pnr, rma_p, ss_p, tanh_p, zones
from .indicators import e04_volume_cog, e07_cycle_phase
from .swing import sd_line


def _df(c, rng=0.01, vol=1.0):
    c = np.asarray(c, float)
    return pd.DataFrame({"Open": c, "High": c * (1 + rng), "Low": c * (1 - rng), "Close": c,
                         "Volume": np.full(len(c), vol)})


def test_filters_pass_constant():
    x = np.full(50, 3.7)
    assert np.allclose(ema_p(x, 5), 3.7)
    assert np.allclose(rma_p(x, 14), 3.7)
    assert np.allclose(ss_p(x, 4), 3.7)


def test_ema_reseeds_after_na():
    y = ema_p(np.array([1.0, 2.0, np.nan, 5.0, 5.0]), 3)
    assert np.isnan(y[2]) and y[3] == 5.0


def test_pnr_ranks():
    x = np.arange(1.0, 11.0)
    hi, lo = pnr(x, 5, 90.0), pnr(x, 5, 10.0)
    assert np.isnan(hi[3]) and hi[4] == 5 and hi[9] == 10   # ceil(4.5)=5番目 = 最大
    assert lo[4] == 1 and lo[9] == 6                        # ceil(0.5)=1番目 = 最小


def test_tanh_matches_numpy():
    x = np.linspace(-30, 30, 101)
    assert np.allclose(tanh_p(x), np.tanh(x))


def test_zones_state_machine():
    line = np.array([0, 70, 80, 50, -70, -40, 90.0])
    U, L = np.full(7, 60.0), np.full(7, -60.0)
    st, ev = zones(line, U, L)
    assert list(st) == [0, 1, 1, 0, -1, 0, 1]
    assert list(np.where(ev["topIn"])[0]) == [1, 6] and list(np.where(ev["topOut"])[0]) == [3]
    assert list(np.where(ev["botIn"])[0]) == [4] and list(np.where(ev["botOut"])[0]) == [5]


def test_swing_detector_on_zigzag():
    # 30本上げ → 20本下げ を繰り返す (1本あたり±2%). 天井は 30, 80, 130 … 本目.
    steps = np.r_[np.tile(np.r_[np.full(30, 0.02), np.full(20, -0.02)], 8)]
    c = 100 * np.exp(np.cumsum(np.r_[0.0, steps]))
    raw, dirs = sd_line(c, c * 1.005, c * 0.995, k=2.0, mode="ext", nAtr=10)
    flips = np.where(np.diff(dirs) != 0)[0] + 1
    flips = flips[dirs[flips - 1] != 0]
    tops = [f for f in flips if dirs[f] == -1]
    # 天井 (50m+30 本目) のあと, θ 分戻したところで下向きに確定する. 未来は使わないので必ず天井より後.
    true_tops = [50 * m + 30 for m in range(8)]
    for f in tops:
        p = max(t for t in true_tops if t < f)
        assert 0 < f - p <= 10, (f, p)
    assert len(tops) >= 6


def test_e04_constant_volume_is_zero():
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
    out = e04_volume_cog(_df(c, vol=5.0), normLen=50)
    # 出来高が一定なら出来高の重心 = 価格の重心なので, 元の値は浮動小数の誤差を除いて 0
    assert np.nanmax(np.abs(out["raw"][20:])) < 1e-9


def test_e07_ramp_reads_neutral():
    c = np.exp(np.linspace(0, 1, 60))
    line = e07_cycle_phase(_df(c))["line"]
    assert abs(line[-1] - 15.6) < 0.1, line[-1]


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(f"{len(tests)} tests passed")
