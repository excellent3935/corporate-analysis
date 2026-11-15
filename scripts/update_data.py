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
    "LLY": "LLY", "JPM": "JPM", "UNH": "UNH", "KO": "KO", "WMT": "WMT", "COST": "COST", "IONQ": "IONQ",
    "TXN": "TXN", "ASTS": "ASTS", "RKLB": "RKLB", "NOW": "NOW", "CRM": "CRM", "RDDT": "RDDT", "SMCI": "SMCI", "IREN": "IREN", "WDC": "WDC", "VRT": "VRT", "COHR": "COHR", "MSTR": "MSTR", "IBM": "IBM", "UMAC": "UMAC", "JOBY": "JOBY", "ACHR": "ACHR", "ONDS": "ONDS", "GEV": "GEV", "CEG": "CEG", "BE": "BE", "VST": "VST", "COIN": "COIN", "CRCL": "CRCL", "HOOD": "HOOD", "JNJ": "JNJ", "ILMN": "ILMN", "ABBV": "ABBV", "BA": "BA", "GE": "GE", "RTX": "RTX", "LMT": "LMT", "AXON": "AXON", "BAC": "BAC", "WFC": "WFC", "V": "V", "MA": "MA", "MP": "MP", "LRCX": "LRCX", "AMAT": "AMAT", "KLAC": "KLAC", "TER": "TER", "HIMS": "HIMS", "TEM": "TEM", "NVO": "NVO", "CRSP": "CRSP", "QBTS": "QBTS", "RGTI": "RGTI", "DDOG": "DDOG", "SNPS": "SNPS", "VRSN": "VRSN", "CRDO": "CRDO", "PEP": "PEP"
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


def update_mcap(cta):
    """시가총액(USD)을 data/mcap.json에 저장 — 사이트 기업 목록 정렬에 쓴다. 미국 종목은 CNBC, 한국 종목은 야후(원) ÷ 환율. 실패한 종목은 이전 값 유지."""
    old = load("mcap.json", {"usd": {}})
    usd = dict(old.get("usd", {}))
    tks = [t for t in cta["tickers"] if not t.isdigit()]

    def num(v):
        v = str(v or "").replace(",", "").strip()
        mult = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
        try:
            return float(v[:-1]) * mult[v[-1]] if v and v[-1] in mult else float(v)
        except ValueError:
            return None

    try:
        url = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
        for i in range(0, len(tks) + 1, 100):
            chunk = tks[i:i + 100] + (["KRW="] if i + 100 >= len(tks) else [])
            r = requests.get(url, headers=UA, timeout=30, params={"requestMethod": "itv", "noform": 1, "partnerId": 2, "fund": 1, "output": "json", "symbols": "|".join(chunk)})
            q = r.json()["FormattedQuoteResult"]["FormattedQuote"]
            for x in ([q] if isinstance(q, dict) else q):
                if x["symbol"] == "KRW=":
                    usd["_fx"] = num(x.get("last"))
                elif num(x.get("mktcapView")):
                    usd[x["symbol"]] = round(num(x["mktcapView"]))
    except Exception:
        traceback.print_exc()
    fx = usd.get("_fx") or 1335.0
    for tk in [t for t in cta["tickers"] if t.isdigit()]:
        try:
            cap = yf.Ticker(tk + ".KS").fast_info["market_cap"]
            if cap:
                usd[tk] = round(float(cap) / fx)
        except Exception:
            traceback.print_exc()
    save("mcap.json", {"asof": dt.datetime.now(KST).strftime("%Y-%m-%d"), "usd": usd})
    print("시가총액", len(usd), "개")


def update_targets(cta):
    """애널리스트 목표가(평균·중앙값·최고·최저, 의견 수)를 야후에서 받아 data/targets.json에 저장. 실패하거나 값이 없는 종목은 이전 값을 유지한다."""
    old = load("targets.json", {"t": {}})
    out = dict(old.get("t", {}))
    today = dt.datetime.now(KST).strftime("%Y-%m-%d")
    got = 0
    for tk, sym in STOCKS.items():
        try:
            t = yf.Ticker(sym)
            pt = t.analyst_price_targets or {}
            mean = pt.get("mean")
            if not mean:
                continue
            e = {"mean": round(float(mean), 2), "d": today}
            for k in ("median", "high", "low"):
                if pt.get(k):
                    e[k] = round(float(pt[k]), 2)
            try:
                inf = t.info or {}
                if inf.get("numberOfAnalystOpinions"):
                    e["n"] = int(inf["numberOfAnalystOpinions"])
                if inf.get("recommendationKey") and inf["recommendationKey"] != "none":
                    e["rec"] = inf["recommendationKey"]
            except Exception:
                pass
            try:  # 최근 기관별 목표가 변경 내역 (목표가가 있는 건만, 최신 12건)
                ud = t.upgrades_downgrades
                rec = []
                for idx, r in ud.sort_index(ascending=False).iterrows():
                    pt_now = r.get("currentPriceTarget")
                    if pt_now is None or pt_now != pt_now or not float(pt_now):
                        continue
                    pp = r.get("priorPriceTarget")
                    rec.append({"d": str(idx)[:10], "f": str(r.get("Firm", "")), "to": str(r.get("ToGrade", "") or ""), "fr": str(r.get("FromGrade", "") or ""),
                                "ac": str(r.get("priceTargetAction", "") or ""), "pt": round(float(pt_now), 2),
                                "pp": round(float(pp), 2) if pp is not None and pp == pp and float(pp) else None})
                    if len(rec) >= 12:
                        break
                if rec:
                    e["recent"] = rec
                elif out.get(tk, {}).get("recent"):
                    e["recent"] = out[tk]["recent"]
            except Exception:
                if out.get(tk, {}).get("recent"):
                    e["recent"] = out[tk]["recent"]
            out[tk] = e
            got += 1
        except Exception:
            traceback.print_exc()
    save("targets.json", {"asof": today, "t": out})
    print("목표가", got, "개 갱신 /", len(out), "개 보유 / 기관별 내역", sum(1 for v in out.values() if v.get("recent")), "개")


# ---------------- 내부자 거래 (Form 4) · 네임드 펀드 13F ----------------
SEC_UA = {"User-Agent": "CorporateAnalysis excellent3935@users.noreply.github.com", "Accept-Encoding": "gzip, deflate"}
NAMED_FUNDS = [  # (CIK, 표시 이름, 검증용 키워드: SEC 등록 이름에 들어 있어야 함)
    ("1067983", "버크셔 해서웨이", "BERKSHIRE"), ("1350694", "브리지워터", "BRIDGEWATER"), ("1423053", "시타델", "CITADEL"),
    ("1037389", "르네상스 테크놀로지스", "RENAISSANCE"), ("1336528", "퍼싱 스퀘어", "PERSHING"), ("1167483", "타이거 글로벌", "TIGER GLOBAL"),
    ("1029160", "소로스 펀드", "SOROS"), ("1040273", "서드 포인트", "THIRD POINT"), ("1656456", "애팔루사", "APPALOOSA"),
    ("1649339", "사이언(마이클 버리)", "SCION"), ("1536411", "듀케인(드러켄밀러)", "DUQUESNE"), ("1336920", "코튜", "COATUE"),
    ("1103804", "바이킹 글로벌", "VIKING"), ("1603466", "포인트72", "POINT72"), ("1179392", "투 시그마", "TWO SIGMA"),
    ("1009207", "D.E. 쇼", "SHAW"), ("1697748", "ARK 인베스트", "ARK INVEST"), ("1791786", "엘리엇", "ELLIOTT"),
    ("1061165", "론 파인", "LONE PINE"), ("1061768", "바우포스트", "BAUPOST"), ("1273087", "밀레니엄", "MILLENNIUM"),
    ("1167557", "AQR", "AQR"),
]
NAME_OVERRIDE = {  # 13F 발행사명(정규화 전) → 사이트 티커. 이름 매칭이 어려운 종목용
    "TAIWAN SEMICONDUCTOR MFG CO LTD": "TSM", "TAIWAN SEMICONDUCTOR MANUFACTURING": "TSM", "META PLATFORMS INC": "META",
    "ALPHABET INC": "GOOGL", "BROADCOM INC": "AVGO", "ELI LILLY & CO": "LLY", "SPACE EXPLORATION TECHNOLOGIES CORP": "SPCX",
}
_STOP = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "HOLDINGS", "HLDGS", "HLDG", "GROUP", "THE", "NV", "SA", "AG", "LP", "CLASS", "CL", "A", "B", "C", "NEW", "DEL", "COM", "SPONSORED", "ADS", "ADR", "DE"}


def _norm(name):
    import re
    t = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper().replace("&", " "))
    return frozenset(w for w in t.split() if w not in _STOP)


def update_insiders(cta):
    """내부자 거래(Form 4) 최근 내역을 야후(yfinance)로 받아 data/insiders.json에 저장. 실패한 종목은 이전 값 유지."""
    import re
    old = load("insiders.json", {"t": {}})
    out = dict(old.get("t", {}))
    today = dt.datetime.now(KST).strftime("%Y-%m-%d")
    got = 0

    def kind(text, tx):
        z = (str(tx or "") + " " + str(text or "")).lower()
        if "purchase" in z or "buy" in z: return "buy"
        if "sale" in z or "sold" in z: return "sell"
        if "award" in z or "grant" in z: return "grant"
        if "exercise" in z or "conversion" in z: return "exercise"
        if "gift" in z: return "gift"
        return "other"

    for tk, sym in STOCKS.items():
        if sym.endswith(".KS"):
            continue
        try:
            df = yf.Ticker(sym).insider_transactions
            if df is None or len(df) == 0:
                continue
            rows = []
            for _, r in df.iterrows():
                d = r.get("Start Date")
                d = str(d)[:10] if d is not None and str(d) != "NaT" else ""
                text = str(r.get("Text", "") or "")
                m = re.search(r"(?:price|at)\s+\$?\s*([0-9][0-9,]*\.?[0-9]*)", text)
                sh = r.get("Shares"); va = r.get("Value")
                rows.append({"d": d, "n": str(r.get("Insider", "") or "").title(), "p": str(r.get("Position", "") or ""), "k": kind(text, r.get("Transaction")),
                             "sh": int(sh) if sh == sh and sh is not None else None, "v": float(va) if va == va and va is not None else None,
                             "px": float(m.group(1).replace(",", "")) if m else None, "u": str(r.get("URL", "") or "")})
            rows.sort(key=lambda x: x["d"], reverse=True)
            out[tk] = rows[:25]
            got += 1
        except Exception:
            traceback.print_exc()
    save("insiders.json", {"asof": today, "t": out})
    print("내부자 거래", got, "개 갱신 /", len(out), "개 보유")


def _sec_get(url, tries=3):
    import time
    for i in range(tries):
        r = requests.get(url, headers=SEC_UA, timeout=40)
        if r.status_code == 200:
            return r
        time.sleep(1.5 * (i + 1))
    r.raise_for_status()


def _parse_infotable(xml_bytes):
    """13F 정보표 XML → {cusip: {name, cls, sh, v}} (옵션·채권 제외, 같은 CUSIP은 합산)"""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_bytes)
    out = {}
    for it in root.iter():
        if not it.tag.endswith("infoTable"):
            continue
        f = {c.tag.split("}")[-1]: c for c in it.iter()}
        txt = lambda k: (f[k].text or "").strip() if k in f else ""
        if txt("putCall") or txt("sshPrnamtType") not in ("SH", ""):
            continue
        try:
            sh = float(txt("sshPrnamt") or 0); v = float(txt("value") or 0)
        except ValueError:
            continue
        c = txt("cusip")
        e = out.setdefault(c, {"name": txt("nameOfIssuer"), "cls": txt("titleOfClass"), "sh": 0.0, "v": 0.0})
        e["sh"] += sh; e["v"] += v
    return out


def _fund_filings(cik):
    j = _sec_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json").json()
    rc = j["filings"]["recent"]
    fl = [(rc["reportDate"][i], rc["filingDate"][i], rc["accessionNumber"][i]) for i in range(len(rc["form"])) if rc["form"][i] == "13F-HR"]
    fl.sort(reverse=True)
    return j.get("name", ""), fl


def _fund_table(cik, acc):
    idx = _sec_get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/index.json").json()
    xs = [x for x in idx["directory"]["item"] if x["name"].lower().endswith(".xml") and "primary_doc" not in x["name"].lower()]
    if not xs:
        raise RuntimeError("정보표 XML 없음 " + acc)
    xs.sort(key=lambda x: ("infotable" not in x["name"].lower(), -int(x.get("size") or 0)))
    return _parse_infotable(_sec_get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{xs[0]['name']}").content)


def _qavg(sym, period):
    """해당 분기(period=분기 말일 YYYY-MM-DD)의 거래량가중 평균가 — 추정 평단/매도가로 쓴다."""
    end = dt.date.fromisoformat(period)
    start = (end.replace(day=1) - dt.timedelta(days=62)).replace(day=1)
    df = yf.Ticker(sym).history(start=start.isoformat(), end=(end + dt.timedelta(days=1)).isoformat(), interval="1d", auto_adjust=False)
    if len(df) == 0:
        return None
    v = df["Volume"].sum()
    return round(float((df["Close"] * df["Volume"]).sum() / v) if v else float(df["Close"].mean()), 2)


def update_funds(cta):
    """네임드 펀드 13F: 최신·직전 분기 보유 중 사이트 등록 종목만 data/funds13f.json에 저장. 접수번호가 같으면 재수집하지 않는다."""
    old = load("funds13f.json", {"f": {}})
    res = dict(old.get("f", {}))
    # SEC 종목 목록으로 사이트 티커의 정식 이름 확보 → 13F 발행사명과 이름 집합으로 매칭
    try:
        co = _sec_get("https://www.sec.gov/files/company_tickers.json").json()
        titles = {}
        for v in co.values():
            titles.setdefault(v["ticker"].upper(), v["title"])
    except Exception:
        traceback.print_exc()
        titles = {}
    ours = {tk: STOCKS[tk] for tk in STOCKS if not STOCKS[tk].endswith(".KS")}
    by_name = {}
    for tk in ours:
        t = titles.get(tk.replace("-", "."))
        if t:
            by_name.setdefault(_norm(t), []).append(tk)
    ov = {_norm(k): v for k, v in NAME_OVERRIDE.items()}

    def tick_of(name, cls):
        k = _norm(name)
        if k in ov and ov[k] in ours:
            if ov[k] == "GOOGL" and "C" in str(cls).upper().split() and "A" not in str(cls).upper().split():
                return None
            return ov[k]
        c = by_name.get(k)
        return c[0] if c else None

    import time
    for cik, label, kw in NAMED_FUNDS:
        try:
            sec_name, fl = _fund_filings(cik)
            if kw not in sec_name.upper():
                print(f"[건너뜀] {label}: CIK {cik} 이름 불일치 → {sec_name}")
                continue
            if not fl:
                continue
            per, filed, acc = fl[0]
            if res.get(cik, {}).get("acc") == acc:
                print(f"{label}: 변경 없음 ({per})"); continue
            cur = _fund_table(cik, acc); time.sleep(0.3)
            prv = _fund_table(cik, fl[1][2]) if len(fl) > 1 else {}
            time.sleep(0.3)

            def pick(tab):
                rows = {}
                for c, e in tab.items():
                    tk = tick_of(e["name"], e["cls"])
                    if tk:
                        r = rows.setdefault(tk, {"sh": 0.0, "v": 0.0}); r["sh"] += e["sh"]; r["v"] += e["v"]
                return {k: {"sh": round(v["sh"]), "v": round(v["v"])} for k, v in rows.items()}
            rows, prows = pick(cur), pick(prv)
            tot, ptot = sum(e["v"] for e in cur.values()), sum(e["v"] for e in prv.values())
            for tk, r in rows.items():  # 변동이 있는 종목은 분기 평균가(추정 평단/매도가) 계산
                if r["sh"] != prows.get(tk, {}).get("sh", 0):
                    try:
                        r["est"] = _qavg(ours[tk], per)
                    except Exception:
                        pass
            for tk, r in prows.items():
                if tk not in rows:  # 청산 종목
                    try:
                        r["est"] = _qavg(ours[tk], per)
                    except Exception:
                        pass
            res[cik] = {"name": label, "acc": acc, "period": per, "filed": filed, "prev": fl[1][0] if len(fl) > 1 else "", "total": round(tot), "ptotal": round(ptot), "rows": rows, "prows": prows}
            print(f"{label}: {per} 보유 {len(cur)}종목 중 등록 종목 {len(rows)}개")
        except Exception:
            print("[실패]", label)
            traceback.print_exc()
    save("funds13f.json", {"asof": dt.datetime.now(KST).strftime("%Y-%m-%d"), "f": res})
    seen = {tk for f in res.values() for tk in list(f["rows"]) + list(f["prows"])}
    print("13F 펀드", len(res), "개 / 보유 확인된 종목", len(seen), "개 / 미확인:", sorted(set(ours) - seen))


def update_news(cta):
    """종목별 최신 뉴스를 data/news.json에 저장 — 야후 파이낸스 종목 RSS(영문), 한국 종목은 구글뉴스 한국어 RSS를 추가로 사용. 실패한 종목은 이전 값 유지."""
    import time
    import email.utils
    import html as _h
    import re as _re
    import xml.etree.ElementTree as ET
    old = load("news.json", {"items": {}})
    out = dict(old.get("items", {}))

    def parse(xml, src_default, cut=12):
        res = []
        for it in ET.fromstring(xml).iter("item"):
            t = (it.findtext("title") or "").strip()
            l = (it.findtext("link") or "").strip()
            if not t or not l:
                continue
            try:
                d = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(dt.timezone.utc).isoformat(timespec="minutes")
            except Exception:
                continue
            ds = _re.sub(r"<[^>]+>", " ", _h.unescape(it.findtext("description") or ""))
            ds = _re.sub(r"\s+", " ", ds).strip()
            src = it.findtext("source") or src_default
            res.append({"t": _h.unescape(t), "l": l, "d": d, "s": ds[:220], "src": src})
            if len(res) >= cut:
                break
        return res

    ok = 0
    for tk in cta["tickers"]:
        try:
            items = []
            sym = tk + ".KS" if tk.isdigit() else tk
            r = requests.get("https://feeds.finance.yahoo.com/rss/2.0/headline", headers=UA, timeout=20, params={"s": sym, "region": "US", "lang": "en-US"})
            r.raise_for_status()
            items += parse(r.content, "Yahoo Finance")
            if tk.isdigit():  # 한국 종목: 한국어 기사 추가
                q = {"005930": "삼성전자", "000660": "SK하이닉스"}.get(tk, tk)
                r = requests.get("https://news.google.com/rss/search", headers=UA, timeout=20, params={"q": q + " 주가", "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
                r.raise_for_status()
                items += parse(r.content, "Google News", 12)
            if items:
                out[tk] = items
                ok += 1
        except Exception:
            traceback.print_exc()
        time.sleep(0.3)
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat(timespec="minutes")
    for tk in list(out):  # 30일 지난 기사 제거
        out[tk] = [x for x in out[tk] if x["d"] >= cutoff]
    translate_items(out, old.get("items", {}))
    save("news.json", {"asof": dt.datetime.now(KST).isoformat(timespec="minutes"), "items": out})
    print("뉴스", ok, "개 종목 갱신")


def translate_items(cur, prev):
    """기사 제목·요약을 한국어로 번역해 tk/sk에 저장. 이미 번역한 링크는 재사용하고, 새 기사만 번역한다(시간 제한 있음)."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    cache = {x["l"]: (x["tk"], x.get("sk", "")) for its in prev.values() for x in its if x.get("tk")}
    todo = {}
    for its in cur.values():
        for x in its:
            if x["l"] in cache:
                x["tk"], x["sk"] = cache[x["l"]]
            elif x["l"] not in todo:
                todo[x["l"]] = x
    t0 = time.time()

    def job(x):
        if time.time() - t0 > 480:  # 8분 넘으면 중단, 나머지는 다음 갱신 때
            return
        raw = x["t"] + ("\n\n" + x["s"] if x.get("s") else "")
        ko = translate_ko(raw)
        if not ko:
            return
        parts = [p.strip() for p in __import__("re").split(r"\n+", ko) if p.strip()]
        x["tk"] = parts[0]
        x["sk"] = _cut(" ".join(parts[1:]), 200) if len(parts) > 1 else ""

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(job, list(todo.values())))
    for its in cur.values():  # 같은 링크가 여러 종목에 걸려 있으면 번역 공유
        for x in its:
            if x["l"] in todo and todo[x["l"]].get("tk"):
                x["tk"], x["sk"] = todo[x["l"]]["tk"], todo[x["l"]].get("sk", "")
    print("번역", sum(1 for x in todo.values() if x.get("tk")), "/", len(todo), "건")


# ---------------- 일정: 미국 경제지표 + 등록 기업 실적 발표 (Nasdaq 캘린더) ----------------
NQ_H = dict(UA, **{"Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
ECON_DROP = __import__("re").compile(r"auction|bill\b|note\b|bond\b|speaks|refinery|distillate|gasoline|heating oil|cushing|crude oil imports|crude runs|production\b", __import__("re").I)
ECON_KO = [  # (정규식, 한글 이름, 중요도) — 위에서부터 먼저 맞는 항목을 쓴다
    (r"adp", "ADP 민간고용", 2), (r"nonfarm productivity", "비농업 생산성", 1), (r"nfib", "NFIB 소기업 낙관지수", 2), (r"chicago pmi", "시카고 PMI", 2),
    (r"fomc statement", "FOMC 성명", 3), (r"fomc press", "FOMC 기자회견", 3), (r"cleveland cpi", "클리블랜드 연은 CPI", 1), (r"core cpi index", "근원 CPI 지수", 1),
    (r"cpi index|cpi, n\.s\.a|cpi, s\.a", "CPI 세부 지표", 1), (r"ism manufacturing (employment|new orders|prices)", "ISM 제조업 세부지수", 1), (r"ism non-manufacturing (business|employment|new orders|prices)", "ISM 서비스업 세부지수", 1),
    (r"durables excluding transport", "내구재 주문(운송 제외)", 2),
    (r"gdpnow", "애틀랜타 연은 GDPNow", 1), (r"dallas fed", "댈러스 연은 PCE", 1), (r"gdp price", "GDP 물가지수", 2), (r"gdp sales", "GDP 최종판매", 2),
    (r"core retail", "근원 소매판매", 3), (r"retail sales ex", "소매판매(휘발유·자동차 제외)", 2), (r"core durable", "근원 내구재 주문", 2), (r"durables ex", "내구재 주문(국방 제외)", 2),
    (r"s&p global composite", "S&P 글로벌 종합 PMI", 2), (r"s&p global manufacturing", "S&P 글로벌 제조업 PMI", 2), (r"s&p global services", "S&P 글로벌 서비스업 PMI", 2),
    (r"core cpi", "근원 CPI(소비자물가)", 3), (r"\bcpi\b|consumer price", "CPI(소비자물가)", 3),
    (r"core ppi", "근원 PPI(생산자물가)", 3), (r"\bppi\b|producer price", "PPI(생산자물가)", 3),
    (r"non[- ]?farm", "비농업 고용자 수", 3), (r"unemployment rate", "실업률", 3),
    (r"import price", "수입물가지수", 3), (r"export price", "수출물가지수", 2),
    (r"core pce", "근원 PCE 물가", 3), (r"pce", "PCE 물가", 3), (r"gdp", "GDP", 3), (r"retail sales", "소매판매", 3),
    (r"interest rate decision|fed funds", "FOMC 금리 결정", 3), (r"fomc.*minutes|minutes", "FOMC 의사록", 3),
    (r"initial jobless", "신규 실업수당 청구건수", 2), (r"continuing jobless", "연속 실업수당 청구건수", 1), (r"jobless claims 4", "실업수당 4주 평균", 1),
    (r"ism.*manufactur", "ISM 제조업지수", 2), (r"ism.*service|ism non", "ISM 서비스업지수", 2), (r"pmi", "PMI", 2),
    (r"jolts|job openings", "JOLTS 구인건수", 2), (r"adp", "ADP 민간고용", 2), (r"average hourly earnings", "평균 시간당 임금", 2),
    (r"consumer confidence", "소비자신뢰지수", 2), (r"michigan|consumer sentiment", "미시간대 소비자심리", 2),
    (r"durable goods", "내구재 주문", 2), (r"housing starts", "주택착공", 2), (r"building permits", "건축허가", 2),
    (r"existing home", "기존주택 매매", 2), (r"new home", "신규주택 매매", 2), (r"industrial production", "산업생산", 2),
    (r"trade balance", "무역수지", 2), (r"philadelphia", "필라델피아 연은 제조업지수", 2), (r"empire state", "뉴욕 연은 제조업지수", 2),
    (r"personal (income|spending)", "개인소득·지출", 2), (r"productivity", "생산성", 1), (r"unit labor", "단위노동비용", 1),
    (r"crude oil inventor", "원유 재고(EIA)", 1), (r"inflation expectations", "기대 인플레이션", 2), (r"capacity utilization", "설비가동률", 1),
    (r"factory orders", "공장 주문", 1), (r"leading (index|indicators)", "경기선행지수", 1), (r"business inventories", "기업 재고", 1),
]


def _clean(v):
    v = (v or "").replace("&nbsp;", " ").strip()
    return v


def update_calendar(cta):
    """data/calendar.json: 미국 경제지표(예상·이전·실제)와 등록 기업 실적 발표 일정. 날짜별로 실패하면 이전 값을 유지한다."""
    import re
    import time
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    old = load("calendar.json", {"econ": [], "earn": []})
    today = dt.datetime.now(ET).date()
    tks = {t for t in cta["tickers"] if not t.isdigit()}
    kocache = {e["name"]: e["ko"] for e in old.get("econ", []) if e.get("ko")}

    def nq(path, day):
        for _ in range(2):
            try:
                r = requests.get("https://api.nasdaq.com/api/calendar/" + path, headers=NQ_H, params={"date": day}, timeout=20)
                if r.ok:
                    return r.json()["data"]
            except Exception:
                pass
            time.sleep(1)
        return None

    econ, earn, ok_e, ok_n = [], [], 0, 0
    old_e = {}
    for e in old.get("econ", []):
        old_e.setdefault(e["day"], []).append(e)
    old_n = {}
    for e in old.get("earn", []):
        old_n.setdefault(e["day"], []).append(e)
    for off in range(-35, 61):  # 경제지표: 35일 전 ~ 60일 후 (달력 탐색용)
        d = today + dt.timedelta(days=off)
        if d.weekday() > 4:
            continue
        ds = d.isoformat()
        data = nq("economicevents", ds)
        if data is None or "rows" not in data:
            econ += old_e.get(ds, [])
            continue
        ok_e += 1
        for x in data.get("rows") or []:
            if x.get("country") != "United States" or ECON_DROP.search(x.get("eventName", "")):
                continue
            nm = x["eventName"].strip()
            m = re.match(r"(\d{1,2}):(\d{2})", x.get("gmt", ""))
            tm = dt.datetime(d.year, d.month, d.day, int(m.group(1)), int(m.group(2)), tzinfo=ET) if m else dt.datetime(d.year, d.month, d.day, 0, 0, tzinfo=ET)
            ko, imp = None, 1
            for pat, k, w in ECON_KO:
                if re.search(pat, nm, re.I):
                    ko, imp = k, w
                    break
            suf = re.search(r"\((MoM|YoY|QoQ|Q/Q|M/M|Y/Y)\)", nm, re.I)
            if ko and suf:
                ko += " (" + {"mom": "MoM", "m/m": "MoM", "yoy": "YoY", "y/y": "YoY", "qoq": "QoQ", "q/q": "QoQ"}[suf.group(1).lower()] + ")"
            if any(z["ts"] == tm.astimezone(dt.timezone.utc).isoformat(timespec="minutes") and z["name"] == nm and (z["a"], z["c"], z["p"]) == (_clean(x.get("actual")), _clean(x.get("consensus")), _clean(x.get("previous"))) for z in econ):
                continue  # 완전히 같은 중복 행 제거
            econ.append({"day": ds, "ts": tm.astimezone(dt.timezone.utc).isoformat(timespec="minutes"), "allday": not m, "name": nm, "ko": ko or kocache.get(nm), "imp": imp,
                         "a": _clean(x.get("actual")), "c": _clean(x.get("consensus")), "p": _clean(x.get("previous"))})
        time.sleep(0.2)
    for off in range(-35, 76):  # 실적: 35일 전 ~ 75일 후
        d = today + dt.timedelta(days=off)
        if d.weekday() > 4:
            continue
        ds = d.isoformat()
        data = nq("earnings", ds)
        if data is None:
            earn += old_n.get(ds, [])
            continue
        ok_n += 1
        for x in data.get("rows") or []:
            if x.get("symbol") in tks:
                tmx = x.get("time", "")
                earn.append({"day": ds, "tk": x["symbol"], "time": "pre" if "pre" in tmx else ("post" if "after" in tmx else "na"), "fq": x.get("fiscalQuarterEnding", ""),
                             "est": _clean(x.get("epsForecast")), "n": _clean(x.get("noOfEsts")), "ly": _clean(x.get("lastYearEPS")), "eps": _clean(x.get("eps")), "sur": _clean(x.get("surprise"))})
        time.sleep(0.2)
    if not ok_e and not ok_n:
        print("일정 수집 실패 — 이전 데이터 유지")
        return
    for e in econ:  # 영어 이름 번역(캐시)
        if not e["ko"]:
            e["ko"] = translate_ko(e["name"]) or ""
            kocache[e["name"]] = e["ko"]
    econ.sort(key=lambda e: (e["ts"], -e["imp"]))
    save("calendar.json", {"asof": dt.datetime.now(KST).isoformat(timespec="minutes"), "econ": econ, "earn": earn})
    print("일정 경제지표", len(econ), "건 / 실적", len(earn), "건 (성공 일수", ok_e, ok_n, ")")


# ---------------- 장전·장후 뉴스 브리핑 (규칙 기반 선별 + 한국어 번역 요약) ----------------
_HAN = __import__("re").compile("[가-힣]")
KW = [  # (정규식, 분류, 가중치)
    (r"\b(earnings|eps|revenue|guidance|outlook|forecast|quarterly results|profit|sales)\b", "실적·가이던스", 3.0),
    (r"\b(acquir\w*|acquisition|merger|takeover|buyout|deal|stake|partnership|contract|invests?|investment)\b", "인수합병·계약", 3.0),
    (r"\b(sec|ftc|doj|lawsuit|sues?|sued|probe|investigation|antitrust|fines?|fined|ban|tariffs?|sanctions?|export controls?|regulators?)\b", "규제·소송", 3.0),
    (r"\b(ceo|cfo|resign\w*|steps? down|appoints?|layoffs?|job cuts|restructur\w*)\b", "경영진·구조조정", 2.5),
    (r"\b(upgrad\w*|downgrad\w*|price target|raises? target|cuts? target|initiates?)\b", "애널리스트 의견", 2.0),
    (r"\b(plunge[sd]?|surge[sd]?|soar\w*|tumble[sd]?|jump[sd]?|sinks?|rall(y|ies|ied)|crash\w*|record high|all-time high|sell-?off|slump\w*)\b", "주가 급등락", 2.5),
    (r"\b(fed|fomc|cpi|inflation|rate cuts?|yields?|treasury|jobs report|gdp|powell)\b", "거시경제", 2.0),
    (r"\b(launch\w*|unveil\w*|chips?|ai model|breakthrough|approval|fda|trial|recall|data cent(er|re)s?)\b", "제품·기술", 1.5),
]
CLICK = __import__("re").compile(r"(better buy|should you|stock a buy|here'?s why|worth buying|buy now|motley fool|retire|dividend stock|passive income|\d+ stocks|zero signs|trustee|\$\d[\d,]* (invested|investment))", __import__("re").I)
SRC_UP = ("reuters.com", "cnbc.com", "bloomberg.com", "wsj.com", "ft.com", "marketwatch.com", "barrons.com", "investing.com", "apnews.com")
SRC_DN = ("fool.com", "247wallst.com", "stocktwits.com", "thestreet.com")


def translate_ko(text):
    """구글 번역 비공식 엔드포인트(키 없음). 실패하면 None → 영어 원문 유지."""
    import time
    text = (text or "").strip()
    if not text or _HAN.search(text):
        return text or None
    try:
        r = requests.get("https://translate.googleapis.com/translate_a/single", headers=UA, timeout=15, params={"client": "gtx", "sl": "en", "tl": "ko", "dt": "t", "q": text[:1500]})
        r.raise_for_status()
        out = "".join(seg[0] for seg in r.json()[0] if seg and seg[0]).strip()
        time.sleep(0.1)
        return out or None
    except Exception:
        return None


def _cut(text, n=170):
    if len(text) <= n:
        return text
    t = text[:n]
    k = max(t.rfind("다. "), t.rfind(". "), t.rfind("다."))
    return (t[:k + 1] if k > n * 0.5 else t.rstrip() + "…").strip()


def _words(t):
    import re
    return {w for w in re.findall(r"[a-z0-9가-힣]+", t.lower()) if len(w) > 3}


def pick_briefing(news, start, end, cap, top=10):
    """news: data/news.json items. start/end: UTC ISO. 규칙 점수로 핵심 기사 top건 선별."""
    import re
    import math
    from urllib.parse import urlparse
    by = {}
    for tk, its in news.items():
        for x in its:
            e = by.setdefault(x["l"].split("?")[0], dict(x, k=[]))
            if tk not in e["k"]:
                e["k"].append(tk)
    pool = [x for x in by.values() if start <= x["d"] <= end]
    rank = {t: i for i, t in enumerate(sorted(cap, key=lambda t: -(cap.get(t) or 0)))}
    n = max(len(rank), 1)
    scored = []
    for x in pool:
        text = x["t"] + " " + x.get("s", "")
        sc, labels = 0.0, []
        for pat, lab, w in KW:
            if re.search(pat, text, re.I):
                sc += w
                labels.append((w, lab))
        sc = min(sc, 6.0)
        host = (urlparse(x["l"]).hostname or "").replace("www.", "")
        sc += 1.5 if host.endswith(SRC_UP) else (-1.0 if host.endswith(SRC_DN) else (0.5 if "yahoo" in host else 0))
        if CLICK.search(x["t"]):
            sc -= 2.5
        best = min((rank.get(t, n) for t in x["k"]), default=n)
        sc += 2.0 * (1 - best / n) + min(len(x["k"]) - 1, 3) * 0.6
        prim = min(x["k"], key=lambda t: rank.get(t, n))
        lab = max(labels)[1] if labels else "일반"
        scored.append((sc, x["d"], x, prim, lab))
    scored.sort(key=lambda z: (z[0], z[1]), reverse=True)
    chosen, per, seen = [], {}, []
    for sc, d, x, prim, lab in scored:
        w = _words(x["t"])
        if any(len(w & v) / max(len(w | v), 1) >= 0.5 for v in seen):
            continue
        if per.get(prim, 0) >= 2:
            continue
        per[prim] = per.get(prim, 0) + 1
        seen.append(w)
        chosen.append(dict(x, prim=prim, lab=lab, sc=round(sc, 2)))
        if len(chosen) >= top:
            break
    return len(pool), chosen


def update_briefing(mode="auto"):
    """mode: auto(현재 미국 동부시간 기준 창에 맞으면 생성) | pre | post(강제). data/briefing.json에 최근 14개 보관."""
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    now = dt.datetime.now(ET)
    hm = now.hour * 60 + now.minute
    kind = mode if mode in ("pre", "post") else None
    if kind is None:
        if now.weekday() < 5 and 8 * 60 <= hm < 9 * 60 + 30:
            kind = "pre"
        elif now.weekday() < 5 and hm >= 16 * 60:
            kind = "post"
        else:
            print("브리핑 생성 시간대가 아님 (ET", now.strftime("%a %H:%M"), ")")
            return
    day = now.strftime("%Y-%m-%d")
    store = load("briefing.json", {"b": []})
    if mode == "auto" and any(b["day"] == day and b["kind"] == kind for b in store["b"]):
        print("이미 생성됨", day, kind)
        return
    close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if kind == "pre":
        end = now
        start = close - dt.timedelta(days=1)
        while start.weekday() > 4:
            start -= dt.timedelta(days=1)
    else:
        start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        end = min(now, close)
    u = lambda d: d.astimezone(dt.timezone.utc).isoformat(timespec="minutes")  # noqa: E731
    news = load("news.json", {"items": {}})["items"]
    cap = load("mcap.json", {"usd": {}}).get("usd", {})
    total, items = pick_briefing(news, u(start), u(end), cap)
    from collections import Counter
    cnt = Counter(t for x in items for t in x["k"][:3])
    labs = Counter(x["lab"] for x in items)
    for x in items:
        x["ko"] = x.get("tk") or translate_ko(x["t"]) or x["t"]
        x["ks"] = x["sk"] if x.get("tk") else (_cut(translate_ko(x.get("s", "")) or "") if x.get("s") else "")
        x["tr"] = bool(_HAN.search(x["ko"]))
    name = "장 시작 전" if kind == "pre" else "장 마감 후"
    span = "전 거래일 마감 이후" if kind == "pre" else "오늘 정규장 시간(09:30~16:00 ET)"
    top = ", ".join(f"{t}({c}건)" for t, c in cnt.most_common(3))
    lb = ", ".join(f"{l} {c}건" for l, c in labs.most_common(4))
    summ = (f"{span} 수집된 기사 {total}건 중 핵심 {len(items)}건을 선별했습니다." if items else f"{span} 수집된 기사가 없습니다.")
    if items:
        summ += f" 가장 많이 언급된 종목은 {top}입니다. 분류는 {lb} 순입니다."
    store["b"] = [b for b in store["b"] if not (b["day"] == day and b["kind"] == kind)]
    store["b"].append({"day": day, "kind": kind, "name": name, "gen": dt.datetime.now(KST).isoformat(timespec="minutes"), "total": total, "summary": summ,
                       "items": [{"ko": x["ko"], "ks": x["ks"], "t": x["t"], "l": x["l"], "d": x["d"], "src": x["src"], "k": x["k"][:4], "lab": x["lab"], "tr": x["tr"]} for x in items]})
    store["b"].sort(key=lambda b: (b["day"], b["kind"] == "post"), reverse=True)
    store["b"] = store["b"][:14]
    save("briefing.json", store)
    print("브리핑", day, kind, len(items), "건")


if __name__ == "__main__":
    now = dt.datetime.now(KST)
    if len(sys.argv) > 1 and sys.argv[1] == "news":  # 뉴스만 빠르게 갱신 (몇 시간마다)
        update_news(load("cta.json", {"tickers": {}}))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "calendar":  # 일정(경제지표 결과·실적 일정)만 갱신
        update_calendar(load("cta.json", {"tickers": {}}))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] in ("insiders", "funds"):  # 내부자 거래 / 13F만 갱신
        {"insiders": update_insiders, "funds": update_funds}[sys.argv[1]](load("cta.json", {"tickers": {}}))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "targets":  # 목표가만 갱신
        update_targets(load("cta.json", {"tickers": {}}))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "briefing":  # 최신 뉴스 수집 후 브리핑 생성: briefing [auto|pre|post]
        mode = sys.argv[2] if len(sys.argv) > 2 else "auto"
        update_news(load("cta.json", {"tickers": {}}))
        update_briefing(mode)
        sys.exit(0)
    m = load("market.json", {"series": {}, "snap": {}, "fg": {}})
    cta = load("cta.json", {"tickers": {}})
    update_market(m)
    update_fg(m)
    update_cta(cta)
    update_mcap(cta)
    update_targets(cta)
    update_insiders(cta)
    update_funds(cta)
    update_news(cta)
    update_briefing("auto")
    update_calendar(cta)
    last = m["series"].get("ES", {}).get("dates", ["----"])[-1]
    m["asof"] = cta["asof"] = now.isoformat(timespec="minutes")
    m["label"] = f"미국장 {int(last[:2])}/{int(last[2:])} 종가"
    save("market.json", m)
    save("cta.json", cta)
    print("완료", now)
