"""매일 GitHub Actions에서 실행: 시장 지표·CNN 공포탐욕 지수·16개 종목 CTA 데이터를 받아 data/*.json에 저장.

- 시세: Yahoo Finance (yfinance)
- 미국 국채 금리: 미국 재무부 일간 수익률 곡선 (공식 CSV)
- 일본 국채 금리: 일본 재무성 국채 금리 (공식 CSV)
- 공포·탐욕 지수: CNN Business 차트 데이터 (비공식 경로 → 실패하면 이전 값 유지)
어느 한 출처가 실패해도 나머지는 갱신하고, 실패한 부분은 이전 파일 값을 그대로 둔다.
"""
import datetime as dt
import io
import json
import os
import sys
import traceback

import pandas as pd
import requests
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from ctalib import signals  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

MARKET = {  # 사이트 키: 야후 심볼
    "NQ": "NQ=F", "ES": "ES=F", "YM": "YM=F", "VIX": "^VIX", "DXY": "DX-Y.NYB",
    "USDKRW": "KRW=X", "CL": "CL=F", "GC": "GC=F",
}
RATES = {"US02Y": "2 Yr", "US10Y": "10 Yr", "US20Y": "20 Yr", "US30Y": "30 Yr"}  # 미 재무부 일간 수익률 곡선 열 이름
STOCKS = {  # 사이트 티커: 야후 심볼
    "MU": "MU", "GOOGL": "GOOGL", "MSFT": "MSFT", "AMZN": "AMZN", "NVDA": "NVDA", "MRVL": "MRVL",
    "005930": "005930.KS", "000660": "000660.KS", "AAPL": "AAPL", "AVGO": "AVGO", "TSM": "TSM", "AMD": "AMD",
    "INTC": "INTC", "QCOM": "QCOM", "ORCL": "ORCL", "PLTR": "PLTR", "META": "META", "CRWV": "CRWV",
    "TSLA": "TSLA", "SPCX": "SPCX", "DELL": "DELL", "SNDK": "SNDK", "CRWD": "CRWD", "NBIS": "NBIS",
}
FG_COMP = [  # CNN 키, 이름, 설명
    ("market_momentum_sp500", "시장 모멘텀", "S&P500 vs 125일선"),
    ("stock_price_strength", "주가 강도", "52주 신고가-신저가"),
    ("stock_price_breadth", "주가 폭", "상승·하락 거래량"),
    ("put_call_options", "풋·콜 옵션", "5일 평균 비율"),
    ("market_volatility_vix", "시장 변동성", "VIX vs 50일선"),
    ("junk_bond_demand", "정크본드 수요", "수익률 스프레드"),
    ("safe_haven_demand", "안전자산 수요", "주식 vs 국채 수익률"),
]
RATING = {"extreme fear": "극단적 공포", "fear": "공포", "neutral": "중립", "greed": "탐욕", "extreme greed": "극단적 탐욕"}


def load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(name, obj):
    json.dump(obj, open(os.path.join(DATA, name), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def history(sym, period="2y"):
    df = yf.Ticker(sym).history(period=period, interval="1d", auto_adjust=False)
    df = df.dropna(subset=["Close"])
    if df.empty:
        raise RuntimeError(f"{sym}: 데이터 없음")
    return df


def snap(close):
    c, p = float(close.iloc[-1]), float(close.iloc[-2])
    return [round(c, 4), round((c / p - 1) * 100, 4), round(c - p, 4)]


# ---------------- 시장 지표 ----------------
def update_market(m):
    for key, sym in MARKET.items():
        try:
            df = history(sym, "1y")
            n = 130 if key in ("NQ", "ES", "YM") else 66
            cl = df["Close"].iloc[-n:]
            m["series"][key] = {"dates": [d.strftime("%m%d") for d in cl.index], "close": [round(float(x), 4) for x in cl]}
            m["snap"][key] = snap(df["Close"])
        except Exception:
            traceback.print_exc()
    try:
        frames = []
        year = dt.datetime.now(KST).year
        for y in (year - 1, year):
            url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
                   f"{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            frames.append(pd.read_csv(io.StringIO(r.text)))
        df = pd.concat(frames)
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        df = df.sort_values("Date").drop_duplicates("Date").iloc[-66:]
        for key, col in RATES.items():
            v = pd.to_numeric(df[col], errors="coerce")
            ok = v.notna()
            m["series"][key] = {"dates": [d.strftime("%m%d") for d in df["Date"][ok]], "close": [float(x) for x in v[ok]]}
            m["snap"][key] = snap(v[ok])
        print("미국 국채 금리 갱신:", df["Date"].iloc[-1].date())
    except Exception:
        traceback.print_exc()
        print("미국 국채 금리 갱신 실패 — 이전 값 유지")
    for k in ("US03M", "US05Y"):
        m["series"].pop(k, None); m["snap"].pop(k, None)
    # 일본 국채 금리: 일본 재무성 공식 CSV (과거 전체 + 이번 달)
    try:
        base = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
        rows = []
        for url in (base + "historical/jgbcme_all.csv", base + "jgbcme.csv"):
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            lines = r.content.decode("utf-8", "ignore").splitlines()
            hi = next(i for i, l in enumerate(lines) if l.split(",")[0].strip().strip('"') == "Date")
            rows.append(pd.read_csv(io.StringIO("\n".join(lines[hi:]))))
        df = pd.concat(rows)
        df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date").drop_duplicates("Date", keep="last").iloc[-66:]
        for key, col in (("JP02Y", "2Y"), ("JP10Y", "10Y")):
            v = pd.to_numeric(df[col], errors="coerce"); ok = v.notna()
            m["series"][key] = {"dates": [d.strftime("%m%d") for d in df["Date"][ok]], "close": [float(x) for x in v[ok]]}
            m["snap"][key] = snap(v[ok])
        print("일본 국채 금리 갱신:", df["Date"].iloc[-1].date())
    except Exception:
        traceback.print_exc()
        print("일본 국채 금리 갱신 실패 — 이전 값 유지")

def update_fg(m):
    try:
        r = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                         headers={**UA, "Referer": "https://edition.cnn.com/", "Origin": "https://edition.cnn.com"}, timeout=30)
        r.raise_for_status()
        j = r.json()
        f = j["fear_and_greed"]
        hist = [round(p["y"]) for p in j["fear_and_greed_historical"]["data"]][-70:]
        comp = []
        for key, name, desc in FG_COMP:
            c = j.get(key, {})
            comp.append([name, desc, round(c.get("score", 0)), RATING.get(str(c.get("rating", "")).lower(), "-")])
        ts = dt.datetime.fromisoformat(str(f["timestamp"]).replace("Z", "+00:00"))
        m["fg"] = {
            "score": round(f["score"], 2), "rating": RATING.get(f["rating"].lower(), f["rating"]),
            "prev": round(f["previous_close"], 2), "w": round(f["previous_1_week"], 2),
            "m": round(f["previous_1_month"], 2), "y": round(f["previous_1_year"], 2),
            "hist": hist, "comp": comp, "asof": ts.strftime("%Y-%m-%d %H:%M UTC"),
        }
        print("CNN 공포·탐욕 지수 갱신:", m["fg"]["score"], m["fg"]["asof"])
    except Exception:
        traceback.print_exc()
        print("CNN 공포·탐욕 지수 갱신 실패 — 이전 값 유지")


# ---------------- CTA ----------------
def cta_fields(df):
    c, h, lo = df["Close"], df["High"], df["Low"]
    e = {"close": round(float(c.iloc[-1]), 4), "chg": round((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2),
         "date": c.index[-1].strftime("%Y-%m-%d")}
    for k in (5, 20, 50, 100, 200):
        e[f"s{k}"] = round(float(c.iloc[-k:].mean()), 4) if len(c) >= k else None
    e["dh55"], e["dl55"] = round(float(h.iloc[-55:].max()), 4), round(float(lo.iloc[-55:].min()), 4)
    for k, n in (("m1", 21), ("m3", 63), ("m6", 126), ("m12", 252)):
        e[k] = round(float(c.iloc[-1 - n]), 4) if len(c) > n else None
    tr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    e["atr"] = round(float(tr.iloc[-14:].mean()), 4)
    e["h52"], e["l52"] = round(float(h.iloc[-252:].max()), 4), round(float(lo.iloc[-252:].min()), 4)
    e["h52d"], e["l52d"] = h.iloc[-252:].idxmax().strftime("%Y-%m-%d"), lo.iloc[-252:].idxmin().strftime("%Y-%m-%d")
    return e


def score_history(df, days=60):
    out = []
    for i in range(max(len(df) - days, 60), len(df)):
        sub = df.iloc[: i + 1]
        _, s = signals(cta_fields(sub))
        out.append(round(s, 3))
    return out


def update_cta(cta):
    for tk, sym in STOCKS.items():
        try:
            df = history(sym, "2y")
            e = cta_fields(df)
            e["cur"] = "원" if sym.endswith(".KS") else "$"
            e["hist"] = score_history(df)
            tail = df["Close"].iloc[-400:]
            e["px"] = {"d": [d.strftime("%m%d") for d in tail.index], "c": [round(float(x), 2) for x in tail]}
            sig, sc = signals(e)
            e["score"] = sc
            cta["tickers"][tk] = e
            print(f"{tk:7s} {e['close']:>12,.2f}  CTA {sc:+.2f}")
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    now = dt.datetime.now(KST)
    m = load("market.json", {"series": {}, "snap": {}, "fg": {}})
    cta = load("cta.json", {"tickers": {}})
    update_market(m)
    update_fg(m)
    update_cta(cta)
    last = m["series"].get("ES", {}).get("dates", ["----"])[-1]
    m["asof"] = cta["asof"] = now.isoformat(timespec="minutes")
    m["label"] = f"미국장 {int(last[:2])}/{int(last[2:])} 종가"
    save("market.json", m)
    save("cta.json", cta)
    print("완료", now)
