"""5거래일 1σ 범위 백테스트 — 과거 변동성(HV)으로 만든 범위에 5거래일 뒤 종가가 실제로 들어온 비율(커버리지)을 잰다.
1σ가 정확하면 약 68.3%여야 한다. 옵션 IV는 과거 값을 구할 수 없어 백테스트할 수 없고, HV 계열만 검증한다.
실행: python scripts/update_data.py backtest  (결과는 data/backtest_sigma.json)"""
import datetime as dt
import json
import os

import numpy as np
import yfinance as yf

H = 5
METHODS = ["HV10", "HV20", "HV60", "EWMA94", "혼합(HV20·HV60)"]


def _sigmas(r):
    """각 시점 i까지의 일간 수익률로 구한 일간 σ 시계열(방법별). r: 일간 로그수익률 ndarray."""
    n = len(r)
    out = {m: np.full(n, np.nan) for m in METHODS}
    s = np.cumsum(np.insert(r, 0, 0.0)); s2 = np.cumsum(np.insert(r * r, 0, 0.0))

    def roll(w):
        v = np.full(n, np.nan)
        for i in range(w - 1, n):
            a = (s2[i + 1] - s2[i + 1 - w]) / w - ((s[i + 1] - s[i + 1 - w]) / w) ** 2
            v[i] = np.sqrt(max(a * w / (w - 1), 0))
        return v
    out["HV10"], out["HV20"], out["HV60"] = roll(10), roll(20), roll(60)
    e = np.full(n, np.nan); var = np.var(r[:20]) if n > 20 else 0
    for i in range(n):
        var = 0.94 * var + 0.06 * r[i] ** 2
        e[i] = np.sqrt(var) if i >= 20 else np.nan
    out["EWMA94"] = e
    out["혼합(HV20·HV60)"] = np.sqrt((out["HV20"] ** 2 + out["HV60"] ** 2) / 2)
    return out


def test_one(px, dates):
    """px: 종가 배열. 반환: {방법: (표본 수, 커버리지, z 표준편차)}, 최근 기록(HV20)"""
    px = np.asarray(px, dtype=float)
    r = np.diff(np.log(px))  # r[k] = ln(px[k+1]/px[k])
    sg = _sigmas(r)
    res, recent = {}, []
    for m in METHODS:
        hits, zs = [], []
        for i in range(60, len(px) - H):  # i일 종가 기준 → i+H일 종가 검증. σ는 i일까지의 수익률(r[:i])만 사용
            sd = sg[m][i - 1]
            if not np.isfinite(sd) or sd <= 0:
                continue
            x = sd * np.sqrt(H)
            lo, hi = px[i] * (1 - x), px[i] * (1 + x)
            hits.append(lo <= px[i + H] <= hi)
            zs.append(np.log(px[i + H] / px[i]) / x)
            if m == "HV20" and i >= len(px) - H - 15:
                recent.append({"d": str(dates[i])[:10], "px": round(px[i], 2), "lo": round(lo, 2), "hi": round(hi, 2), "end": round(px[i + H], 2), "hit": bool(hits[-1])})
        if hits:
            res[m] = (len(hits), float(np.mean(hits)), float(np.std(zs)))
    return res, recent


def run(tickers, mapping):
    out = {"asof": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "h": H, "by": {}, "agg": {}, "nvda_recent": []}
    for tk in tickers:
        try:
            h = yf.Ticker(mapping.get(tk, tk)).history(period="3y", interval="1d", auto_adjust=True).dropna(subset=["Close"])
            if len(h) < 200:
                continue
            res, recent = test_one(h["Close"].values, h.index)
            out["by"][tk] = {m: {"n": v[0], "cov": round(v[1], 4), "zsd": round(v[2], 3)} for m, v in res.items()}
            if tk == "NVDA":
                out["nvda_recent"] = recent
            print(tk, " ".join(f"{m}={v[1] * 100:.1f}%/z{v[2]:.2f}" for m, v in res.items()))
        except Exception as e:  # noqa: BLE001
            print("[백테스트 실패]", tk, e)
    for m in METHODS:
        c = [v[m]["cov"] for v in out["by"].values() if m in v]
        z = [v[m]["zsd"] for v in out["by"].values() if m in v]
        if c:
            out["agg"][m] = {"cov": round(float(np.mean(c)), 4), "zsd": round(float(np.mean(z)), 3), "n_tickers": len(c)}
    print("== 전체 평균 (목표 커버리지 68.3%, z 표준편차 1.0) ==")
    for m, v in out["agg"].items():
        print(f"{m}: 커버리지 {v['cov'] * 100:.1f}% · z표준편차 {v['zsd']:.2f} · {v['n_tickers']}종목")
    return out
