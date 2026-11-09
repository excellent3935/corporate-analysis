"""data/*.json + content/ → _site/ 정적 사이트 생성. GitHub Actions가 매일 실행한다."""
import re, os, shutil, math, json, sys, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from ctalib import signals, fmt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "_site")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
open(os.path.join(OUT, ".nojekyll"), "w").close()

# ---------------- data ----------------
M = json.load(open(os.path.join(ROOT, "data", "market.json"), encoding="utf-8"))
CTA = json.load(open(os.path.join(ROOT, "data", "cta.json"), encoding="utf-8"))["tickers"]
SER = M["series"]; SNAP = M["snap"]; FG = M["fg"]
_D = os.path.dirname(os.path.abspath(__file__))
KST = dt.timezone(dt.timedelta(hours=9))
ASOF = dt.datetime.fromisoformat(M["asof"]).astimezone(KST)
STAMP = f"{ASOF:%Y.%m.%d %H:%M} KST 갱신 · {M['label']}"
def sign(v, d=2, pct=False):
    s = f"{v:+,.{d}f}"
    return s + ("%" if pct else "")
def cls(v): return "up" if v > 0 else ("down" if v < 0 else "")

def spark(vals, w=160, h=40, color=None):
    lo, hi = min(vals), max(vals); rng = hi - lo or 1
    pts = [(i * w / (len(vals) - 1), h - 3 - (v - lo) / rng * (h - 6)) for i, v in enumerate(vals)]
    col = color or ("#16a34a" if vals[-1] >= vals[0] else "#dc2626")
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<svg class="spk" viewBox="0 0 {w} {h}" preserveAspectRatio="none"><path d="{d} L{w},{h} L0,{h} Z" fill="{col}" fill-opacity=".08"/><path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>'

def bigchart(vals, dates, w=640, h=230):
    pad_l, pad_r, pad_t, pad_b = 8, 58, 12, 24
    def ma(k): return [None if i < k - 1 else sum(vals[i - k + 1:i + 1]) / k for i in range(len(vals))]
    m20, m50 = ma(20), ma(50)
    allv = vals + [x for x in m50 if x]
    lo, hi = min(allv), max(allv); rng = hi - lo
    lo -= rng * .05; hi += rng * .05; rng = hi - lo
    X = lambda i: pad_l + i * (w - pad_l - pad_r) / (len(vals) - 1)
    Y = lambda v: pad_t + (hi - v) / rng * (h - pad_t - pad_b)
    path = lambda arr: "M" + " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(arr) if v is not None)
    col = "#16a34a" if vals[-1] >= vals[-21] else "#dc2626"
    g = ""
    for t in range(5):
        v = lo + rng * (t + .5) / 5; y = Y(v)
        g += f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="gl"/><text x="{w-pad_r+6}" y="{y+4:.1f}" class="ax">{v:,.0f}</text>'
    for i, d in enumerate(dates):
        if d.endswith("01") or (i > 0 and d[:2] != dates[i - 1][:2]):
            g += f'<text x="{X(i):.1f}" y="{h-6}" class="ax" text-anchor="middle">{int(d[:2])}월</text>'
    last = vals[-1]
    g += f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{Y(last):.1f}" y2="{Y(last):.1f}" stroke="{col}" stroke-dasharray="3 3" stroke-width="1"/>'
    g += f'<rect x="{w-pad_r+2}" y="{Y(last)-9:.1f}" width="54" height="18" rx="3" fill="{col}"/><text x="{w-pad_r+29}" y="{Y(last)+4:.1f}" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">{last:,.0f}</text>'
    return (f'<svg class="big" viewBox="0 0 {w} {h}">{g}<path d="{path(vals)} L{X(len(vals)-1):.1f},{h-pad_b} L{X(0):.1f},{h-pad_b} Z" fill="{col}" fill-opacity=".07"/>'
            f'<path d="{path(m50)}" fill="none" style="stroke:var(--ma50)" stroke-width="1.2" opacity=".7"/><path d="{path(m20)}" fill="none" stroke="#2563eb" stroke-width="1.2"/>'
            f'<path d="{path(vals)}" fill="none" stroke="{col}" stroke-width="1.8"/></svg>')

def stock_chart(dates, vals, show=190, w=720, h=280):
    def ma(k): return [None if i < k - 1 else sum(vals[i - k + 1:i + 1]) / k for i in range(len(vals))]
    m20, m50, m200 = ma(20)[-show:], ma(50)[-show:], ma(200)[-show:]
    v, dd = vals[-show:], dates[-show:]
    allv = v + [x for x in m20 + m50 + m200 if x]
    lo, hi = min(allv), max(allv); rng = hi - lo; lo -= rng * .05; hi += rng * .05; rng = hi - lo
    pl, pr, pt, pb = 8, 70, 12, 24
    X = lambda i: pl + i * (w - pl - pr) / (len(v) - 1); Y = lambda x: pt + (hi - x) / rng * (h - pt - pb)
    path = lambda a: "M" + " L".join(f"{X(i):.1f},{Y(x):.1f}" for i, x in enumerate(a) if x is not None)
    col = "#16a34a" if v[-1] >= v[-21] else "#dc2626"
    g = ""
    for t in range(5):
        y0 = lo + rng * (t + .5) / 5
        g += f'<line x1="{pl}" x2="{w-pr}" y1="{Y(y0):.1f}" y2="{Y(y0):.1f}" class="gl"/><text x="{w-pr+6}" y="{Y(y0)+4:.1f}" class="ax">{y0:,.0f}</text>'
    for i, d in enumerate(dd):
        if i > 0 and d[:2] != dd[i - 1][:2]: g += f'<text x="{X(i):.1f}" y="{h-6}" class="ax" text-anchor="middle">{int(d[:2])}월</text>'
    g += (f'<rect x="{w-pr+2}" y="{Y(v[-1])-9:.1f}" width="66" height="18" rx="3" fill="{col}"/>'
          f'<text x="{w-pr+35}" y="{Y(v[-1])+4:.1f}" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">{v[-1]:,.0f}</text>')
    return (f'<svg class="big" viewBox="0 0 {w} {h}">{g}<path d="{path(v)} L{X(len(v)-1):.1f},{h-pb} L{X(0):.1f},{h-pb} Z" fill="{col}" fill-opacity=".07"/>'
            f'<path d="{path(m200)}" fill="none" stroke="#d97706" stroke-width="1.3"/><path d="{path(m50)}" fill="none" style="stroke:var(--ma50)" stroke-width="1.2" opacity=".7"/>'
            f'<path d="{path(m20)}" fill="none" stroke="#2563eb" stroke-width="1.2"/><path d="{path(v)}" fill="none" stroke="{col}" stroke-width="1.8"/></svg>')

def gauge(score):
    cx, cy, r = 110, 104, 84
    segs = [(0, 25, "#dc2626"), (25, 45, "#f97316"), (45, 55, "#a3a3a3"), (55, 75, "#84cc16"), (75, 100, "#16a34a")]
    out = ""
    for a, b, c in segs:
        t1, t2 = math.pi * (1 - a / 100), math.pi * (1 - b / 100)
        x1, y1 = cx + r * math.cos(t1), cy - r * math.sin(t1); x2, y2 = cx + r * math.cos(t2), cy - r * math.sin(t2)
        out += f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 0 1 {x2:.1f},{y2:.1f}" stroke="{c}" stroke-width="16" fill="none"/>'
    t = math.pi * (1 - score / 100); nx, ny = cx + (r - 22) * math.cos(t), cy - (r - 22) * math.sin(t)
    out += f'<line id="fgneedle" x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" style="stroke:var(--ink)" stroke-width="3" stroke-linecap="round"/><circle cx="{cx}" cy="{cy}" r="6" style="fill:var(--ink)"/>'
    for v, lab in [(0, "0"), (25, "25"), (50, "50"), (75, "75"), (100, "100")]:
        tt = math.pi * (1 - v / 100); out += f'<text x="{cx+(r+16)*math.cos(tt):.1f}" y="{cy-(r+16)*math.sin(tt)+4:.1f}" text-anchor="middle" class="ax">{lab}</text>'
    return f'<svg viewBox="0 0 220 120" class="gauge">{out}</svg>'

# ---------------- reports ----------------
def body_of(path):
    s = open(path, encoding="utf-8").read()
    if "<body>" in s:
        s = s[s.index("<body>") + 6:]; s = s[:s.rindex("</body>")] if "</body>" in s else s
    return s

TERMS = ["마이크론", "마벨", "루멘텀", "D램", "낸드", "알파벳", "구글", "마이크로소프트", "아마존", "엔비디아", "앤스로픽", "오픈AI", "삼성전자", "SK하이닉스", "AWS", "Azure", "HBM", "DRAM", "NAND",
         "데이터센터", "클라우드", "TPU", "코파일럿", "제미나이", "트레이니엄"]
def highlight(html):
    parts = re.split(r"(<[^>]+>)", html); out = []; inside_hl = 0; skip = 0
    for p in parts:
        if p.startswith("<"):
            tag = p[1:].split()[0].lower().strip("/>") if len(p) > 2 else ""
            if re.match(r"<(h1|h2|h3|h4|th|table|div class=\"kicker|strong|b|a)\b", p): skip += 1 if not p.startswith("</") else 0
            if re.match(r"</(h1|h2|h3|h4|th|table|strong|b|a)>", p): skip = max(0, skip - 1)
            out.append(p); continue
        if skip == 0:
            for t in TERMS:
                p = re.sub(rf"(?<![가-힣A-Za-z]){re.escape(t)}", f"\x00{t}\x01", p, count=2)
            p = p.replace("\x00", '<span class="kw">').replace("\x01", "</span>")
        out.append(p)
    return "".join(out)

def merged(srcs):
    parts = [body_of(srcs[0])]
    for x in srcs[1:]:
        b = body_of(x)
        b = re.sub(r'<div class="kicker">.*?</div>\s*<h1>(.*?)</h1>\s*<div class="meta">.*?</div>', lambda m: '<div class="part"><span>PART 2</span>' + m.group(1).split(':')[0].replace('마이크론 ','').replace('알파벳 ','') + '</div>', b, count=1, flags=re.S)
        parts.append(b)
    h = "".join(parts)
    if len(parts) > 1:
        h = re.sub(r'(<h2><span class="n">\d+</span>정리하며 발견한[^<]*)</h2>', r'\1 (실적 편)</h2>', h, count=1)
        h = re.sub(r'(<h2><span class="n">\d+</span>정리하며 발견한[^<]*?)(</h2>)(?![\s\S]*정리하며 발견한)', r'\1 (심층 편)\2', h)
    h = re.sub(r'짝이 되는 「[^」]+」에 정리했다', '이 페이지 2부(심층 기업분석)에 이어서 정리했다', h)
    n = [0]
    def num(m): n[0] += 1; return f'<span class="n">{n[0]:02d}</span>'
    return re.sub(r'<span class="n">\d+</span>', num, h)

def bullify(html, folder):
    html = html.replace(' class="pb"', "")
    html = re.sub(r'<span class="n">0?(\d+)</span>', lambda m: f"{int(m.group(1))}. ", html)
    html = re.sub(r'src="([^"/]+\.(png|jpg))"', lambda m: f'src="{folder}/{m.group(1)}" loading="lazy"', html)
    # drop header block (kicker/h1/meta) – rendered by page shell
    html = re.sub(r'<div class="kicker">.*?</div>\s*<h1>.*?</h1>\s*<div class="meta">(.*?)</div>', lambda m: f'<div class="meta">{m.group(1)}</div>', html, count=1, flags=re.S)
    html = re.sub(r"<table", '<div class="tw"><table', html); html = html.replace("</table>", "</table></div>")
    return highlight(html)

for d in sorted(os.listdir(CONTENT)):
    os.makedirs(f"{OUT}/{d}")
    for f in os.listdir(f"{CONTENT}/{d}"):
        if f.endswith((".png", ".jpg")): shutil.copy(f"{CONTENT}/{d}/{f}", f"{OUT}/{d}/{f}")

REPORTS = [  # file, folder, srcs, title, ticker, company, tag, sub, cover bg, stock line, url
 ("micron.html", "mu", [CONTENT + "/mu/report.html", CONTENT + "/mu/body2.html"], "Micron Technology 기업분석", "MU", "Micron Technology, Inc.", "반도체", "8개 분기 실적 · DRAM 수요 · 이평선·CTA", "#eef2ff", "반도체 · 시총 $780.7B · 직원 약 6.1만 명", "https://www.micron.com"),
 ("alphabet.html", "googl", [CONTENT + "/googl/body.html"], "Alphabet 기업분석", "GOOGL", "Alphabet Inc. Class A", "빅테크", "클라우드 +103% · FCF 마이너스 · CTA -0.75", "#ecfdf5", "인터넷 서비스 · 시총 $3.47T · 직원 204,757명", "https://abc.xyz"),
 ("microsoft.html", "msft", [CONTENT + "/msft/body.html"], "Microsoft 기업분석", "MSFT", "Microsoft Corporation", "빅테크", "Azure +48% · FCF 플러스 · 천장 테스트", "#f0f9ff", "패키지 소프트웨어 · 시총 $3.94T", "https://www.microsoft.com"),
 ("amazon.html", "amzn", [CONTENT + "/amzn/body.html"], "Amazon 기업분석", "AMZN", "Amazon.com, Inc.", "빅테크", "AWS 재가속 · 설비투자 $77B · 박스권", "#fff7ed", "인터넷 유통 · 시총 $2.80T", "https://www.amazon.com"),
 ("nvidia.html", "nvda", [CONTENT + "/nvda/body.html"], "NVIDIA 기업분석", "NVDA", "NVIDIA Corporation", "반도체", "매출 $96B · 가이던스 $108B · 약정 $279B", "#f0fdf4", "반도체 · 시총 $4.50T", "https://www.nvidia.com"),
 ("marvell.html", "mrvl", [CONTENT + "/mrvl/body.html"], "Marvell 기업분석", "MRVL", "Marvell Technology, Inc.", "반도체", "맞춤형 칩·광 연결 · 루멘텀 인수", "#f5f3ff", "반도체 · 시총 $123.8B", "https://www.marvell.com"),
 ("samsung.html", "sec", [CONTENT + "/sec/body.html"], "삼성전자 기업분석", "005930", "삼성전자", "반도체", "분기 영업이익 107조 · HBM4 · 주주환원", "#eff6ff", "반도체·전자 · 시총 약 1,390조 원", "https://www.samsung.com/sec"),
 ("skhynix.html", "skh", [CONTENT + "/skh/body.html"], "SK하이닉스 기업분석", "000660", "SK하이닉스", "반도체", "이익률 80% · 장기계약 · 2030년 부족", "#fef2f2", "메모리 반도체 · 시총 약 1,018조 원", "https://www.skhynix.com"),
 ("tsmc.html", "tsm", [CONTENT + "/tsm/body.html"], "TSMC 기업분석", "TSM", "Taiwan Semiconductor Manufacturing Co.", "반도체", "매출 $46.7B · 2나노 8% · 가이던스 +58%", "#f0fdfa", "반도체 위탁생산 · 시총 $1.78T", "https://www.tsmc.com"),
 ("broadcom.html", "avgo", [CONTENT + "/avgo/body.html"], "Broadcom 기업분석", "AVGO", "Broadcom Inc.", "반도체", "AI 반도체 +221% · VMware · 52주 신저가", "#fff1f2", "반도체·소프트웨어 · 시총 $1.40T", "https://www.broadcom.com"),
 ("amd.html", "amd", [CONTENT + "/amd/body.html"], "AMD 기업분석", "AMD", "Advanced Micro Devices, Inc.", "반도체", "데이터센터 +97% · 헬리오스 · 4Q $17B", "#f1f5f9", "반도체 · 시총 $733B", "https://www.amd.com"),
 ("intel.html", "intc", [CONTENT + "/intc/body.html"], "Intel 기업분석", "INTC", "Intel Corporation", "반도체", "DCAI +78% · 이익률 43% · 4Q 가이던스 쇼크", "#eef6ff", "반도체 · 시총 $299B", "https://www.intel.com"),
 ("qualcomm.html", "qcom", [CONTENT + "/qcom/body.html"], "Qualcomm 기업분석", "QCOM", "QUALCOMM Incorporated", "반도체", "자동차 +89% · 핸드셋 -26% · 데이터센터 $5B", "#f0f4ff", "반도체(팹리스) · 시총 $177B", "https://www.qualcomm.com"),
 ("oracle.html", "orcl", [CONTENT + "/orcl/body.html"], "Oracle 기업분석", "ORCL", "Oracle Corporation", "소프트웨어", "OCI +121% · RPO $664B · FCF 마이너스", "#fff5f5", "소프트웨어·클라우드 · 시총 $351B", "https://www.oracle.com"),
 ("palantir.html", "pltr", [CONTENT + "/pltr/body.html"], "Palantir 기업분석", "PLTR", "Palantir Technologies Inc.", "소프트웨어", "매출 +96% · 순이익률 49% · TCV 둔화", "#f4f4f5", "소프트웨어 · 시총 $386B", "https://www.palantir.com"),
 ("meta.html", "meta", [CONTENT + "/meta/body.html"], "Meta 기업분석", "META", "Meta Platforms, Inc.", "빅테크", "매출 +26% · 이익률 20% · 설비투자 $140B", "#eef4ff", "인터넷 서비스 · 시총 $1.56T", "https://about.meta.com"),
 ("coreweave.html", "crwv", [CONTENT + "/crwv/body.html"], "CoreWeave 기업분석", "CRWV", "CoreWeave, Inc.", "소프트웨어", "AI 클라우드 · 잔고 $104B · 부채 $35B", "#f5f3ff", "AI 클라우드 · 시총 $25.6B", "https://www.coreweave.com"),
 ("tesla.html", "tsla", [CONTENT + "/tsla/body.html"], "Tesla 기업분석", "TSLA", "Tesla, Inc.", "빅테크", "로보택시·FSD 174만 · 영업이익률 2.6%", "#fff1f2", "자동차·에너지·AI · 시총 $1.42T", "https://www.tesla.com"),
 ("spacex.html", "spcx", [CONTENT + "/spcx/body.html"], "SpaceX 기업분석", "SPCX", "Space Exploration Technologies Corp.", "빅테크", "매출 +161% · AI(SI) $76억 · 첫 흑자", "#f1f5f9", "우주·통신·AI · 시총 $1.82T", "https://www.spacex.com"),
 ("dell.html", "dell", [CONTENT + "/dell/body.html"], "Dell 기업분석", "DELL", "Dell Technologies Inc.", "반도체", "AI 서버 잔고 $950억 · 매출 +58%", "#eff6ff", "IT 하드웨어 · 시총 $2,089억", "https://www.dell.com"),
 ("sandisk.html", "sndk", [CONTENT + "/sndk/body.html"], "Sandisk 기업분석", "SNDK", "Sandisk Corporation", "반도체", "매출총이익률 85% · 8:1 분할", "#fef2f2", "메모리 반도체 · 시총 $1,188억", "https://www.sandisk.com"),
 ("crowdstrike.html", "crwd", [CONTENT + "/crwd/body.html"], "CrowdStrike 기업분석", "CRWD", "CrowdStrike Holdings, Inc.", "소프트웨어", "순신규 ARR +51% · AI 보안", "#fff1f2", "사이버 보안 · 시총 $2,221억", "https://www.crowdstrike.com"),
 ("nebius.html", "nbis", [CONTENT + "/nbis/body.html"], "Nebius 기업분석", "NBIS", "Nebius Group N.V.", "소프트웨어", "AI 클라우드 · 매출 +454% · 선수금 $60억", "#f7fee7", "AI 클라우드 · 시총 $352억", "https://nebius.com"),
 ("apple.html", "aapl", [CONTENT + "/aapl/body.html"], "Apple 기업분석", "AAPL", "Apple Inc.", "빅테크", "FY26 매출 $479B · 아이폰 듀오 · 메모리 비용", "#f8fafc", "소비자 전자 · 시총 $4.98T", "https://www.apple.com"),
 ("eli-lilly.html", "lly", [CONTENT + "/lly/body.html"], "Eli Lilly 기업분석", "LLY", "Eli Lilly and Company", "헬스케어", "비만약 매출 66% · PEG 0.92 · CTA +1.0", "#fdf2f8", "제약 · 시총 $1.27T", "https://www.lilly.com"),
 ("jpmorgan.html", "jpm", [CONTENT + "/jpm/body.html"], "JPMorgan Chase 기업분석", "JPM", "JPMorgan Chase & Co.", "금융", "ROTCE 20% · PEG 0.79 · P/TBV 3배", "#eff6ff", "은행 · 시총 $889B", "https://www.jpmorganchase.com"),
 ("unitedhealth.html", "unh", [CONTENT + "/unh/body.html"], "UnitedHealth 기업분석", "UNH", "UnitedHealth Group Incorporated", "헬스케어", "이익 V자 회복 · MCR 88.4%", "#f0f9ff", "건강보험·의료 · 시총 $353B", "https://www.unitedhealthgroup.com"),
 ("cocacola.html", "ko", [CONTENT + "/ko/body.html"], "Coca-Cola 기업분석", "KO", "The Coca-Cola Company", "소비재", "영업이익률 33% · PEG 2.3 · 사상 최고가", "#fef2f2", "음료 · 시총 $412B", "https://www.coca-colacompany.com"),
 ("walmart.html", "wmt", [CONTENT + "/wmt/body.html"], "Walmart 기업분석", "WMT", "Walmart Inc.", "소비재", "이커머스 +23% · PER 45배", "#eff6ff", "유통 · 시총 $996B", "https://corporate.walmart.com"),
 ("costco.html", "cost", [CONTENT + "/cost/body.html"], "Costco 기업분석", "COST", "Costco Wholesale Corporation", "소비재", "회원비 = 영업이익 51% · PER 51배", "#fef2f2", "회원제 유통 · 시총 $467B", "https://www.costco.com"),
 ("ionq.html", "ionq", [CONTENT + "/ionq/body.html"], "IonQ 기업분석", "IONQ", "IonQ, Inc.", "양자", "양자 · 매출 +336% · 런웨이 약 3년", "#f5f3ff", "양자컴퓨팅 · 시총 $14.0B", "https://ionq.com"),
]
def _price(tk):
    e = CTA.get(tk, {})
    if "close" not in e: return ("-", "", "")
    ch = e.get("chg", 0)
    return (fmt(e["close"], e.get("cur", "$")), f"{ch:+.2f}%", "up" if ch > 0 else ("down" if ch < 0 else ""))
PRICE = {r[4]: _price(r[4]) for r in REPORTS}
EXCH = {"005930": "KRX", "000660": "KRX", "TSM": "NYSE", "ORCL": "NYSE", "DELL": "NYSE", "LLY": "NYSE", "JPM": "NYSE", "UNH": "NYSE", "KO": "NYSE", "IONQ": "NYSE"}

MONO = {"005930": "삼성", "000660": "SK"}
LOGO = {"NVDA": "nvidia", "AAPL": "apple", "GOOGL": "alphabet", "MSFT": "microsoft", "AMZN": "amazon", "MU": "micron-technology", "MRVL": "marvell-tech",
        "005930": "samsung", "TSM": "taiwan-semiconductor", "AVGO": "broadcom", "AMD": "advanced-micro-devices", "INTC": "intel", "QCOM": "qualcomm",
        "ORCL": "oracle", "PLTR": "palantir", "META": "meta-platforms", "CRWV": "coreweave",
        "TSLA": "tesla", "SPCX": "spacex", "DELL": "dell", "SNDK": "sandisk", "CRWD": "crowdstrike", "NBIS": "nebius-group-nv",
        "LLY": "eli-lilly", "JPM": "jpmorgan-chase", "UNH": "unitedhealth", "KO": "coca-cola", "WMT": "walmart", "COST": "costco-wholesale", "IONQ": "ionq"}  # 트레이딩뷰 공개 로고 (SK하이닉스는 없어 글자 배지 유지)
def _icon(r):
    tk = r[4]; mono = f'<span class="mono">{MONO.get(tk, tk)}</span>'
    if tk == "000660": return f'<img class="logo" src="skh/logo.png" alt="{r[5]} 로고">'
    if tk not in LOGO: return mono
    fb = mono.replace('"', "&quot;")
    return (f'<img class="logo" src="https://s3-symbol-logo.tradingview.com/{LOGO[tk]}--big.svg" alt="{r[5]} 로고" loading="lazy" '
            f'onerror="this.outerHTML=\'{fb}\'">')
ICON = {r[4]: _icon(r) for r in REPORTS}
CSS = """
.top .thm{flex:none;margin-left:10px;width:34px;height:30px;border-radius:8px;border:1px solid var(--line);background:transparent;color:var(--ink);cursor:pointer;font-size:15px;line-height:1;display:flex;align-items:center;justify-content:center}.top .thm:hover{background:var(--hover)}.top .thm .sun{display:none}html[data-theme=dark] .top .thm .sun{display:inline}html[data-theme=dark] .top .thm .moon{display:none}
:root{--ma50:#111111;--hover:#f3f4f6;--navy:#111111;--blue:#2563eb;--ink:#0d0d0d;--ink2:#374151;--muted:#6b7280;--line:#e5e7eb;--soft:#f7f7f8;--red:#2563eb;--up:#16a34a;--down:#dc2626}
*{box-sizing:border-box}
body{margin:0;font-family:"Pretendard Variable",Pretendard,"Noto Sans KR",system-ui,sans-serif;color:var(--ink);background:#fafafa;line-height:1.65;font-size:15px}
a{color:inherit}
.top{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);color:#111;border-bottom:1px solid var(--line)}
.top .in{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:6px;padding:10px 20px;overflow-x:auto;white-space:nowrap}
.top .brand{display:flex;align-items:center;gap:9px;margin-right:18px;text-decoration:none;color:#111}.top .brand .mk{width:26px;height:26px;border-radius:7px;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;letter-spacing:-.5px}.top .brand .w{font-weight:800;letter-spacing:2.5px;font-size:14px}.top .brand .w small{font-weight:500;letter-spacing:1px;color:#9ca3af;margin-left:6px;font-size:11px}
.top a.nv{color:#6b7280;text-decoration:none;padding:6px 11px;border-radius:7px;font-size:14px}
.top a.nv.on,.top a.nv:hover{background:#f3f4f6;color:#111}
.top .st{margin-left:auto;font-size:12px;color:#9ca3af}
main.home{max-width:1180px;margin:0 auto;padding:22px 20px 60px}.intro{padding:34px 0 8px}.intro .ey{font-size:12px;letter-spacing:4px;color:#2563eb;font-weight:700}.intro h1{font-size:34px;line-height:1.3;margin:8px 0 10px;letter-spacing:-.5px}.intro p{color:#4b5563;max-width:720px;margin:0}
.sech{display:flex;align-items:baseline;gap:10px;margin:28px 0 12px}
.sech h2{font-size:21px;margin:0;color:#111;letter-spacing:-.3px}.sech .sm{font-size:12.5px;color:var(--muted)}
.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.fut .nm{font-size:13px;color:var(--muted)}.fut .px{font-size:24px;font-weight:800;margin:2px 0}.fut .ch{font-size:13px;font-weight:700}
svg.big{width:100%;height:auto;display:block;margin-top:8px}
.gl{stroke:#eef0f4;stroke-width:1}.ax{font-size:10.5px;fill:#9aa0a8}
.leg{font-size:11.5px;color:var(--muted);margin-top:2px}.leg i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin:0 4px 0 8px}
.fgwrap{display:grid;grid-template-columns:300px 1fr 1fr;gap:16px;align-items:center}
.gauge{width:100%;max-width:280px}.fgnum{text-align:center;margin-top:-8px}.fgnum b{font-size:40px;color:var(--down)}.fgnum div{font-weight:700;color:var(--down)}
.hist td,.comp td{padding:5px 6px;border-bottom:1px solid var(--line);font-size:13.5px}
.bar{height:7px;background:#eef0f4;border-radius:4px;overflow:hidden;width:110px;display:inline-block;vertical-align:middle}.bar span{display:block;height:100%}
.tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px 12px}
.tile .nm{font-size:12px;color:var(--muted)}.tile .px{font-size:18px;font-weight:800;margin-top:2px}.tile .ch{font-size:12px;font-weight:700}
.tile svg.spk{width:100%;height:34px;display:block;margin-top:6px}
.up{color:var(--up)}.down{color:var(--down)}
.curve{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px}
.note{font-size:12px;color:var(--muted);margin-top:10px}
.pills{display:flex;gap:8px;margin:6px 0 14px}.pill{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 14px;font-size:13px;cursor:pointer;font-family:inherit}
.pill.on{background:#111;color:#fff;border-color:#111}
.books{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.book{text-decoration:none;color:var(--ink)}
.cover{aspect-ratio:3/4;border-radius:14px;padding:16px;color:#111;border:1px solid var(--line);display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden;box-shadow:none;transition:transform .15s}.book:hover .cover{transform:translateY(-3px)}.cover .ico{position:absolute;right:16px;top:16px;width:46px;height:46px;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.08)}.cover .ico svg{width:28px;height:28px}
.cover .bdg{position:absolute;top:16px;left:16px;background:#111;color:#fff;font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px}
.cover .tk{font-size:11.5px;letter-spacing:2px;color:#6b7280;margin-top:34px}.cover .emb{position:absolute;left:50%;top:56%;transform:translate(-50%,-50%);width:96px;height:96px;border-radius:50%;background:#fff;box-shadow:0 4px 18px rgba(15,23,42,.10),0 0 0 6px rgba(255,255,255,.55);display:flex;align-items:center;justify-content:center}.cover .emb .mono{font-size:21px}
.logo{width:100%;height:100%;object-fit:cover;border-radius:inherit;display:block}.cover .emb,.prembox .ic,.stock .lg{overflow:hidden}.cover .emb .logo{border-radius:50%}.cover .emb{top:50%;width:132px;height:132px}.cover .emb>span{display:flex;align-items:center;justify-content:center;width:100%;height:100%;border-radius:50%;overflow:hidden}.cover .emb .mono{font-size:28px}
.bdtool{display:flex;justify-content:flex-end;margin:0 0 10px}#ctaboard.brief .xd{display:none}#ctaboard.brief td{padding-top:5px;padding-bottom:5px}#ctaboard.brief .small{display:none}#ctaboard.brief td br{display:none}#ctaboard.brief td.r span{margin-left:8px}
.pager{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:12px}.pager button{min-width:34px;height:32px;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;cursor:pointer;font-family:inherit;font-size:13px}.pager button.on{background:var(--ink);color:var(--soft);border-color:var(--ink)}.pager button:disabled{opacity:.35;cursor:default}.pager .pi{font-size:12px;color:var(--muted);margin-left:8px}
.tvmini{height:330px;margin:8px -6px 0}.fhd{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}.ivs{display:flex;gap:4px}.ivb{border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:6px;padding:2px 8px;font-size:12px;cursor:pointer;font-family:inherit}.ivb.on{background:var(--ink);color:var(--soft);border-color:var(--ink)}.tvw iframe,.tvbox iframe{color-scheme:light}.fut .lv{font-size:10px;font-weight:800;letter-spacing:1px;color:#fff;background:#dc2626;border-radius:4px;padding:1px 5px;margin-left:4px;vertical-align:1px;animation:lvb 1.6s infinite}@keyframes lvb{50%{opacity:.45}}
.hm{position:relative;padding:0;overflow:hidden}.hmbar{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;font-size:12px;color:var(--muted);border-bottom:1px solid var(--line);flex-wrap:wrap}
.hmst .live,.livedot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22c55e;margin-right:6px;animation:hmp 1.6s infinite}@keyframes hmp{50%{opacity:.25}}.hmst .dn{color:var(--down)}
.hmfoot{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding:8px 12px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted)}.hmlg{display:flex;white-space:nowrap}.hmlg span{padding:4px 10px;font-size:11px;font-weight:700;color:#fff;min-width:40px;text-align:center}.hmck{cursor:pointer}.hmck input{margin-right:3px;vertical-align:-2px}
.hmctl{display:flex;align-items:center;gap:12px;padding:8px 12px;border-bottom:1px solid var(--line);flex-wrap:wrap;font-size:12px;color:var(--muted)}.hmctl label{display:flex;align-items:center;gap:6px}
.hmctl select{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:5px 8px;max-width:150px}.hmvw{margin-left:auto;display:flex;gap:6px}.hmvw .pill{padding:5px 12px;font-size:12px}
.hmbox{position:relative;height:620px;background:#262930;overflow:hidden}.hmbox[hidden],.hmlist[hidden]{display:none}
.hs{position:absolute;height:14px;line-height:14px;padding:0 3px;font-size:11px;font-weight:600;color:#e6e8ee;background:#262930;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;z-index:1;cursor:pointer}.hs.d1{height:11px;line-height:11px;font-size:9px;font-weight:500;color:#c6cad4;background:#262930;cursor:default}.hs.d0:hover{color:#fff;text-decoration:underline}
.hc{position:absolute;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;color:#fff;overflow:hidden;cursor:pointer;line-height:1.1;outline:1px solid #262930;outline-offset:-.5px}.hc b{font-weight:700}.hc i{font-style:normal;opacity:.92}.hc img{border-radius:4px;background:#fff;object-fit:contain;flex:none;margin-bottom:2px}.hc:hover{filter:brightness(1.15);z-index:3}.hmhl{display:none;position:absolute;border:2px solid #ffd60a;box-sizing:border-box;pointer-events:none;z-index:4}
.hmlist{max-height:620px;overflow:auto;padding:6px 8px 10px}.hmlist details{border-bottom:1px solid var(--line)}.hmlist summary{display:flex;align-items:center;gap:10px;padding:9px 6px;cursor:pointer;list-style:none;font-size:13.5px}.hmlist summary::-webkit-details-marker{display:none}
.hmlist summary:before{content:"›";display:inline-block;width:12px;color:var(--muted);transition:transform .15s}.hmlist details[open]>summary:before{transform:rotate(90deg)}.hmlist .ln{font-weight:700;color:var(--ink);flex:1;min-width:0}.hmlist .li .ln{font-weight:600;font-size:13px}.hmlist .lcn{color:var(--muted);font-size:12px}.hmlist summary em{font-style:normal;font-weight:700;min-width:64px;text-align:right}
.hmlist .li{margin-left:14px;border-bottom:0}.hmlist .li summary{padding:6px}
.lr{display:grid;grid-template-columns:22px 54px minmax(0,1fr) 82px 66px 62px;align-items:center;gap:8px;padding:5px 6px 5px 22px;font-size:12.5px;border-top:1px dashed var(--line)}.lr b{color:var(--ink)}.lr .nm{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lr .px,.lr .cp{text-align:right;color:var(--ink2)}.lr em{font-style:normal;font-weight:700;text-align:right}.lr img{border-radius:50%;background:#fff;object-fit:contain}.lgx{width:20px;height:20px}.hmempty{padding:30px;text-align:center;color:var(--muted)}
.hmtip{display:none;position:absolute;z-index:9;pointer-events:none;background:#1f222b;color:#f3f4f6;border:1px solid #3b4050;border-radius:8px;width:250px;font-size:12px;line-height:1.4;box-shadow:0 8px 28px rgba(0,0,0,.5);overflow:hidden}
.hmtip .th{padding:8px 12px;font-size:11.5px;font-weight:600;color:#cbd0dc;border-bottom:1px solid #343947}.hmtip .tm{padding:9px 12px 10px;border-bottom:1px solid #343947}.hmtip .tm b{font-size:16px}.hmtip .tm span{color:#9aa1b2;margin-left:4px}
.hmtip .tp{margin-top:4px}.hmtip .tp u{text-decoration:none;font-size:15px;font-weight:700;margin-right:6px}.hmtip .ts{color:#9aa1b2;font-size:11px;margin-top:2px}
.hmtip .tl{padding:4px 0}.hmtip .tr{display:grid;grid-template-columns:54px 1fr 64px;gap:6px;padding:4px 12px;align-items:center}.hmtip .tr.on{background:#2b3040}.hmtip .tr span{text-align:right;color:#cbd0dc}.hmtip .tr em{font-style:normal;font-weight:700;text-align:right}.hmtip .tmore{padding:4px 12px 3px;color:#8b92a3;font-size:11px}
.hmtip .up{color:#34d36b}.hmtip .down{color:#ff6b6e}
@media(max-width:560px){.hmbox{height:480px}.hmlist{max-height:480px}.hmbar{font-size:11px}.hmctl{gap:8px}.hmctl select{max-width:118px}.lr{grid-template-columns:20px 46px minmax(0,1fr) 62px 56px;padding-left:12px}.lr .cp{display:none}.hmlg span{font-size:9.5px}.hmlg{gap:5px}}
.hmap{height:620px;padding:6px;overflow:hidden}.hmap iframe{color-scheme:light}@media(max-width:560px){.hmap{height:480px}}
.tile.live{padding:10px 8px 4px}.tile.live .nm{padding:0 4px}.tvtile{height:150px;margin:0 -2px}.tvtile iframe{color-scheme:light}.dly{font-size:10px;font-weight:700;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:2px}.tiles>.tile:not(.live){display:flex;flex-direction:column}.tiles>.tile:not(.live) svg.spk{margin-top:auto}.dly.on{color:#16a34a;border-color:rgba(22,163,74,.4)}.oneline{font-size:13px;color:var(--ink2);margin-top:10px}
.board a.bn{display:flex;align-items:center;gap:10px}.board .bl0{width:28px;height:28px;border-radius:50%;overflow:hidden;flex:none;background:var(--soft);display:flex;align-items:center;justify-content:center}.board .bl0 .mono{font-size:9px}
.mono{font-weight:800;letter-spacing:-.5px;color:#111;line-height:1;white-space:nowrap}.prembox .ic .mono{font-size:9.5px}.stock .lg .mono{font-size:13px}.cover .ct{font-size:21px;font-weight:800;line-height:1.25}
.cover .cs{font-size:11.5px;color:#4b5563}.cover>svg{position:absolute;left:0;right:0;bottom:44px;width:100%;height:38%;opacity:.9}
.book .bt{font-size:14px;font-weight:700;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.book .ba{font-size:12px;color:var(--muted)}
.book .bp{font-size:13.5px;font-weight:700;margin-top:2px}
.book .btn{display:block;text-align:center;background:#111;color:#fff;border-radius:999px;padding:8px;font-size:12.5px;font-weight:700;margin-top:8px}
.cmp table{width:100%;border-collapse:collapse;font-size:13.5px}.cmp th{background:#f3f4f6;text-align:left;padding:7px 9px;color:var(--navy);border-top:1.5px solid var(--navy)}.cmp td{padding:7px 9px;border-bottom:1px solid var(--line)}
.ins{display:grid;grid-template-columns:1fr 1fr;gap:12px}.ins div{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px;font-size:14px}.ins b{display:block;color:var(--navy);margin-bottom:4px}
.tag{display:inline-block;font-size:11.5px;font-weight:700;padding:1px 7px;border-radius:4px;margin-right:4px}
.g{background:#dcf3ec;color:#17785f}.b{background:#fde3e6;color:#b3263a}.y{background:#fdf1d6;color:#9a6a09}.bl{background:#e1e9fa;color:#2f5aa8}
.tape{max-width:1180px;margin:0 auto;padding:4px 20px 0}
.tvlink{display:inline-block;margin-top:8px;font-size:13.5px;font-weight:700;color:#2563eb;text-decoration:none}
.tvbox{border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:4px 0 6px}
.ctabox{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:18px 0}.ctabox .hd{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}.ctabox .hd span{font-size:12px;color:var(--muted)}
.ctabox .sc{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:8px 0}.ctabox .sc .tag{font-size:15px;padding:4px 10px}.ctabox .mv{font-size:13.5px}.ctabox .tr{margin-left:auto;text-align:right}.ctabox .tr svg{width:200px;height:36px}.ctabox .tr small{display:block;font-size:11px;color:var(--muted)}
.ctabox .mas{font-size:12.5px;color:var(--muted);margin-top:6px}
.board td{vertical-align:middle}.board .r{text-align:right}.board a{color:inherit;text-decoration:none}.board .small{font-size:11.5px;color:var(--muted)}.board svg.spk{width:90px;height:22px}
.dots i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:3px}.dots i.pg{background:#16a34a}.dots i.pr{background:#dc2626}.dots i:nth-child(4){margin-right:8px}.dots i:nth-child(3){margin-right:8px}
footer{max-width:1180px;margin:0 auto;padding:10px 20px 40px;font-size:12px;color:var(--muted)}

.readwrap{display:grid;grid-template-columns:230px 1fr;min-height:100vh;background:#fff}
.side{border-right:1px solid var(--line);padding:18px 14px;position:sticky;top:46px;height:calc(100vh - 46px);overflow:auto;background:#fff}
.side .h{font-size:12px;color:var(--muted);margin:14px 6px 6px}
.side a{display:block;text-decoration:none;font-size:14px;padding:7px 8px;border-radius:7px;color:#222}
.side a.on,.side a:hover{background:#f2f2f3}
.side .prem{background:#f7f7f8;border-radius:12px;padding:10px;margin:14px 0}
.side .prem a{color:#374151}.side .prem a.on,.side .prem a:hover{background:#fff;color:#111}
.side .prem .t{font-size:11px;letter-spacing:1.5px;opacity:.7;margin:2px 8px 6px}
.read{max-width:768px;margin:0 auto;padding:22px 22px 80px;font-size:16px;line-height:1.65;width:100%}
.rhead{display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:22px}
.rhead a{text-decoration:none;font-size:20px;color:#333}.rhead .t{font-size:14.5px;font-weight:600}.rhead .a{font-size:12px;color:var(--muted)}
.prembox{border:1px solid var(--line);background:#fafafa;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px;margin-bottom:18px;font-size:13.5px}
.prembox .ic{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid var(--line);display:flex;align-items:center;justify-content:center;flex:none}.prembox .ic svg{width:24px;height:24px}
.prembox .k{font-size:11px;letter-spacing:1.5px;color:#2563eb;font-weight:700}
.hero{border-radius:14px;overflow:hidden;border:1px solid var(--line)}
.hero img{width:100%;display:block}.cap{font-size:12.5px;color:var(--muted);margin:6px 2px 18px}
.stock{border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;gap:14px;align-items:center;margin:18px 0 6px}
.stock .lg svg{width:30px;height:30px}.stock .lg{width:52px;height:52px;border-radius:12px;background:#f5f5f5;display:flex;align-items:center;justify-content:center;font-weight:800;color:#555;font-size:13px}
.stock .n{font-size:18px;font-weight:700}.stock .n small{font-size:12px;color:var(--muted);font-weight:500;letter-spacing:1px;margin-left:6px}
.stock .s{font-size:13px;color:var(--muted)}.stock .u{font-size:13px;color:var(--red)}
.stock .p{margin-left:auto;text-align:right;font-weight:800;font-size:18px}.stock .p small{display:block;font-size:12.5px}
.read .kw{color:var(--red)}
.read .part{margin:56px 0 8px;padding:18px 0 0;border-top:2px solid #111;font-size:22px;font-weight:700}.read .part span{display:block;font-size:11.5px;letter-spacing:3px;color:#2563eb;margin-bottom:4px}
.read .meta{font-size:13px;color:var(--muted);background:var(--soft);border-radius:10px;padding:10px 14px;margin:8px 0 18px}
.read h2{font-size:20px;font-weight:600;margin:38px 0 10px;line-height:1.6}
.read h3{font-size:17px;font-weight:600;margin:26px 0 8px}
.read p{margin:10px 0}
.read .dark{background:#111;color:#fff;border-radius:12px;padding:16px 18px;margin:14px 0}
.read .dark .lab{font-size:11px;letter-spacing:3px;opacity:.7}.read .dark .txt{font-size:16.5px;font-weight:700;line-height:1.65}
.read .box{background:rgba(245,245,246,.9);border-radius:12px;padding:14px 18px;margin:14px 0;font-size:15px}
.read .box b.t{font-size:14px}
.read .tw{overflow-x:auto;margin:12px 0}
.read table{width:100%;border-collapse:collapse;font-size:14px}
.read th{text-align:left;padding:8px 9px;border-bottom:2px solid #111;font-weight:600;white-space:nowrap}
.read td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
.read td.r,.read th.r{text-align:right;white-space:nowrap}
.read tr.hl td{background:#fff7e6;font-weight:600}
.read img.ch{width:100%;margin:10px 0;border-radius:8px}
.read .two{display:flex;gap:12px;flex-wrap:wrap}.read .two>div{flex:1;min-width:250px}
.read .card{border:1px solid var(--line);border-radius:12px;padding:13px 16px}
.read .card h4{margin:0 0 6px;font-size:15.5px}
.read .sum3{background:var(--soft);border-left:3px solid #111;padding:10px 16px;margin:14px 0;border-radius:0 10px 10px 0}
.read .small{font-size:13px;color:var(--muted)}
.read .strat{display:flex;gap:10px;margin:10px 0;flex-wrap:wrap}.read .strat div{flex:1;min-width:150px;text-align:center;border:1px solid var(--line);border-radius:12px;padding:10px}
.read .strat .k{font-size:12px;color:var(--muted)}.read .strat .v{font-size:20px;font-weight:800}
.read ul,.read ol{padding-left:22px}.read li{margin:4px 0}
.endnav{display:flex;justify-content:space-between;gap:12px;margin-top:40px;border-top:1px solid var(--line);padding-top:16px;font-size:14px}
.endnav a{text-decoration:none;color:#333}
/* ---------- dark mode ---------- */
html[data-theme=dark]{color-scheme:dark;--ma50:#d1d5db;--hover:var(--hover);--navy:#e5e7eb;--ink:var(--navy);--ink2:#c3c7ce;--muted:#9aa1ac;--line:var(--line);--soft:var(--soft);--red:var(--blue);--blue:var(--blue);--up:#22c55e;--down:#f87171}
html[data-theme=dark] body{background:var(--paper)}
html[data-theme=dark] .top{background:rgba(18,19,22,.9);color:var(--ink)}
html[data-theme=dark] .top .brand{color:var(--ink)}html[data-theme=dark] .top .brand .mk{background:var(--navy);color:#111}
html[data-theme=dark] .top a.nv{color:var(--muted)}html[data-theme=dark] .top a.nv.on,html[data-theme=dark] .top a.nv:hover{background:var(--hover);color:var(--ink)}
html[data-theme=dark] .intro .ey,html[data-theme=dark] .prembox .k,html[data-theme=dark] .read .part span,html[data-theme=dark] .tvlink{color:var(--blue)}
html[data-theme=dark] .sech h2{color:var(--ink)}
html[data-theme=dark] .panel,html[data-theme=dark] .tile,html[data-theme=dark] .ins div,html[data-theme=dark] .pill{background:var(--card)}
html[data-theme=dark] .pill{color:var(--ink)}html[data-theme=dark] .pill.on{background:var(--navy);color:#111;border-color:var(--navy)}
html[data-theme=dark] .gl{stroke:var(--line)}html[data-theme=dark] .ax{fill:#7d8490}
html[data-theme=dark] .bar{background:var(--line)}
html[data-theme=dark] .cover{background:color-mix(in srgb,var(--cbg) 9%,var(--card))!important;color:var(--ink)}
html[data-theme=dark] .cover .ico,html[data-theme=dark] .cover .emb{background:var(--hover);box-shadow:0 4px 18px rgba(0,0,0,.4),0 0 0 6px rgba(255,255,255,.04)}
html[data-theme=dark] .cover .bdg,html[data-theme=dark] .book .btn{background:var(--navy);color:#111}
html[data-theme=dark] .cover .tk,html[data-theme=dark] .cover .cs{color:var(--muted)}
html[data-theme=dark] .mono{color:var(--ink)}
html[data-theme=dark] .cmp th{background:var(--soft)}
html[data-theme=dark] .g{background:rgba(34,197,94,.15);color:#4ade80}html[data-theme=dark] .b{background:rgba(248,113,113,.15);color:#fca5a5}
html[data-theme=dark] .y{background:rgba(250,204,21,.14);color:#facc15}html[data-theme=dark] .bl{background:rgba(96,165,250,.15);color:var(--blue)}
html[data-theme=dark] .readwrap,html[data-theme=dark] .side{background:var(--paper)}
html[data-theme=dark] .side a{color:var(--ink2)}html[data-theme=dark] .side a.on,html[data-theme=dark] .side a:hover{background:var(--hover);color:var(--ink)}
html[data-theme=dark] .side .prem{background:var(--soft)}html[data-theme=dark] .side .prem a{color:var(--ink2)}html[data-theme=dark] .side .prem a.on,html[data-theme=dark] .side .prem a:hover{background:var(--line);color:var(--ink)}
html[data-theme=dark] .rhead a,html[data-theme=dark] .endnav a{color:var(--ink2)}
html[data-theme=dark] .prembox{background:var(--card)}html[data-theme=dark] .prembox .ic,html[data-theme=dark] .stock .lg{background:var(--hover);color:var(--ink2)}
html[data-theme=dark] .read .part{border-top-color:var(--ink)}
html[data-theme=dark] .read .dark{background:var(--soft);color:#f3f4f6;border:1px solid var(--line)}
html[data-theme=dark] .read .box{background:var(--soft)}
html[data-theme=dark] .read th{border-bottom-color:#4b5058}
html[data-theme=dark] .read tr.hl td{background:rgba(250,204,21,.09)}
html[data-theme=dark] .read .sum3{border-left-color:var(--ink2)}
html[data-theme=dark] .read img.ch,html[data-theme=dark] .hero img{filter:brightness(.88) contrast(1.05)}
html[data-theme=dark] [style*="color:#b3263a"]{color:#fca5a5!important}html[data-theme=dark] [style*="color:#17785f"]{color:#4ade80!important}
html[data-theme=dark] [style*="border-top:1px solid #e5e7eb"]{border-top-color:var(--line)!important}
@media(max-width:1000px){.grid3,.curve,.ins{grid-template-columns:1fr}.fgwrap{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(3,1fr)}.books{grid-template-columns:repeat(3,1fr)}.readwrap{grid-template-columns:1fr}.side{display:none}}
@media(max-width:560px){.tiles{grid-template-columns:repeat(2,1fr)}.books{grid-template-columns:repeat(2,1fr)}}
/* ---------- mobile ---------- */
.readwrap>*{min-width:0}.board{overflow-x:auto}.board .dots{white-space:nowrap}
@media(max-width:640px){
body{font-size:14px}
.top .in{padding:8px 12px;gap:2px;overflow:visible}.top .brand{margin-right:6px;gap:7px}.top .brand .w{display:none}
.top a.nv{padding:5px 8px;font-size:13px}.top .st{display:none}.top .thm{margin-left:auto;width:32px;height:28px;font-size:14px}
main.home{padding:12px 14px 40px}.intro{padding:14px 0 0}.intro h1{font-size:25px}
.sech{flex-wrap:wrap;gap:2px 8px;margin:24px 0 10px}.sech h2{font-size:18px;white-space:nowrap}.sech .sm{flex-basis:100%;font-size:11.5px}
.panel{padding:12px 12px;border-radius:12px}.fhd .ivs{width:100%}.ivb{flex:1;padding:4px 0}.tvmini{height:300px}
.fgwrap{gap:10px}.gauge{max-width:240px;margin:0 auto;display:block}
.tiles{gap:8px}.tvtile{height:136px}
.pills{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;margin:4px -14px 12px;padding:0 14px}.pills::-webkit-scrollbar{display:none}.pill{flex:none;padding:6px 12px;font-size:12.5px}
.bdtool .pills{margin:0;padding:0}
.board td,.board th{padding:6px 6px;font-size:12.5px}.board .tag{white-space:nowrap;font-size:11px;padding:1px 5px;margin:0}.board td.r{white-space:nowrap}.board .bl0{width:24px;height:24px}.board a.bn{gap:7px}
#ctaboard:not(.brief) .dots i{width:9px;height:9px;margin-right:2px}
.pager button{min-width:30px;height:30px}.pager .pi{display:none}
.books{gap:12px}.cover{padding:12px;border-radius:12px}.cover .bdg{top:12px;left:12px;font-size:10px}.cover .tk{font-size:10px;letter-spacing:1px;margin-top:28px}
.cover .emb{width:84px!important;height:84px!important}.cover .cs{font-size:10.5px;line-height:1.4}
.book .bt{font-size:13px}.book .ba{font-size:11px}.book .bp{font-size:12.5px}.book .btn{padding:7px;font-size:12px}
.read{padding:14px 14px 60px;font-size:15px}.rhead{margin-bottom:14px}.prembox{padding:10px 12px;font-size:12.5px}
.stock{padding:12px;gap:10px;flex-wrap:wrap}.stock .lg{width:42px;height:42px}.stock .n{font-size:16px}.stock .u{word-break:break-all}.stock .p{font-size:16px}
.read table{font-size:12.5px}.read th,.read td{padding:6px 6px}.read .two>div{min-width:100%}
.ctabox{padding:12px}.ctabox .tr{margin-left:0;text-align:left}.ctabox .tr svg{width:160px}
.endnav{flex-direction:column}
footer{padding:10px 14px 30px}
}

/* ================= research-report theme ================= */
body{word-break:keep-all;overflow-wrap:break-word}.tag{white-space:nowrap}.read td .tag,.ctabox td .tag{margin-right:0}
@media(max-width:640px){.ctabox th:nth-child(2),.ctabox td:nth-child(2){display:none}.ctabox table{font-size:12.5px}.ctabox th,.ctabox td{padding:6px 5px}.ctabox td:last-child,.ctabox th:last-child{text-align:right;width:1%}
.read td,.read th{min-width:56px}.read th{white-space:nowrap}}
:root{--navy:#1c1c1e;--gold:#9b2242;--paper:#f6f5f3;--card:#ffffff;--ink:#18181b;--ink2:#3f3f46;--muted:#71717a;--line:#e3e0dc;--soft:#efece8;--hover:#ebe7e2;--ma50:#1c1c1e;--blue:#1f4e8c;--red:#1f4e8c;--bar:#1c1c1e;--up:#15803d;--down:#b91c1c;--serif:"Noto Serif KR","Nanum Myeongjo",Georgia,serif}
body{background:var(--paper);color:var(--ink)}
.top{background:var(--bar);border-bottom:0;box-shadow:inset 0 -2px 0 var(--gold);color:#fff}
.top .brand{color:#fff}.top .brand .mk{background:var(--gold);color:#fff;border-radius:2px;font-family:var(--serif);font-weight:700;font-size:13px}
.top .brand .w{font-family:var(--serif);font-weight:700;letter-spacing:3px;color:#fff}.top .st{color:rgba(255,255,255,.55)}
.top a.nv{color:rgba(255,255,255,.72);border-radius:2px}.top a.nv.on,.top a.nv:hover{background:transparent;color:#fff;box-shadow:inset 0 -2px 0 var(--gold)}
.top .thm{border-radius:2px;color:#fff;border-color:rgba(255,255,255,.28)}.top .thm:hover{background:rgba(255,255,255,.08)}
.intro{padding:40px 0 18px;border-bottom:1px solid var(--line)}.intro .ey{color:var(--gold);letter-spacing:3px;font-size:11.5px}
.intro h1{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:36px;letter-spacing:-.5px}
.sech{margin:40px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--navy);position:relative}.sech:after{content:"";position:absolute;left:0;bottom:-1px;width:56px;height:3px;background:var(--gold)}
.sech h2{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:22px}
.panel,.tile,.ins div,.ctabox,.stock,.prembox,.read .card,.read .strat div,.tvbox,.hero{background:var(--card);border-color:var(--line);border-radius:4px}
.panel{box-shadow:0 1px 0 rgba(15,35,66,.04)}
.pill{border-radius:2px;background:var(--card);border-color:var(--line);color:var(--ink2)}.pill.on{background:var(--navy);border-color:var(--navy);color:#fff}
.ivb{border-radius:2px}.ivb.on{background:var(--navy);border-color:var(--navy);color:#fff}
.pager button{border-radius:2px}.pager button.on{background:var(--navy);border-color:var(--navy);color:#fff}
.cmp th{background:transparent;color:var(--navy);border-top:2px solid var(--navy);border-bottom:1px solid var(--navy);font-size:12px;letter-spacing:.5px}
.tag{border-radius:2px}.g{background:#e3efe6;color:#15803d}.b{background:#f6e3e1;color:#a61b1b}.y{background:#f3ecd9;color:#8a6a1f}.bl{background:#e2e9f3;color:#1f4e8c}
.fut .lv{border-radius:2px;background:var(--down)}.dly{border-radius:2px}
.gl{stroke:#e8e2d5}.bar{background:#ebe5d8;border-radius:1px}
/* tiles */
.books{grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
.tcard{min-width:0;aspect-ratio:1/1;display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:4px;padding:12px;text-decoration:none;color:var(--ink);transition:border-color .15s,transform .15s;position:relative}
.tcard:hover{border-color:var(--gold);transform:translateY(-2px)}.tcard:before{content:"";position:absolute;left:0;top:0;right:0;height:3px;background:var(--navy);border-radius:4px 4px 0 0;opacity:0;transition:opacity .15s}.tcard:hover:before{opacity:1}
.tl-top{display:flex;justify-content:space-between;align-items:center;gap:6px}.tl-tag{font-size:10.5px;color:var(--gold);font-weight:700;letter-spacing:.5px}.tl-tk{font-size:10.5px;color:var(--muted);letter-spacing:1px}
.tl-logo{flex:1;display:flex;align-items:center;justify-content:center}.tl-logo .logo{width:52px;height:52px;border-radius:50%;box-shadow:0 0 0 1px var(--line)}.tl-logo .mono{font-size:15px;color:var(--ink)}
.tl-nm{font-family:var(--serif);font-weight:700;font-size:14px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--navy)}
.tl-px{font-size:12.5px;font-weight:700;margin-top:2px;white-space:nowrap}.tl-px span{font-weight:600;margin-left:4px}
/* report pages */
.readwrap,.side{background:var(--paper)}.side{border-right-color:var(--line)}.side a{border-radius:2px}.side a.on,.side a:hover{background:var(--hover);color:var(--navy)}
.side .prem{background:transparent;border-top:1px solid var(--line);border-radius:0;padding:10px 0}.side .prem a.on{box-shadow:inset 3px 0 0 var(--gold);background:var(--card)}
.read{background:transparent}.rhead{border-bottom:2px solid var(--navy)}.rhead .t{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:16px}
.prembox .k,.read .part span{color:var(--gold)}
.read h2{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:21px;border-bottom:1px solid var(--line);padding-bottom:6px}
.read h3{font-family:var(--serif);font-weight:600;color:var(--navy)}
.read .part{font-family:var(--serif);border-top:3px double var(--navy);color:var(--navy)}
.read .dark{background:var(--navy);border-radius:4px;border-left:4px solid var(--gold)}
.read .box{background:var(--soft);border-radius:4px}.read .meta{background:var(--soft);border-radius:4px}
.read th{border-bottom:2px solid var(--navy);color:var(--navy)}.read tr.hl td{background:#f7e9ec}
.read .sum3{border-left:3px solid var(--gold);background:var(--soft);border-radius:0 4px 4px 0}
.read .kw{color:var(--gold)}.tvlink{color:var(--blue)}
.endnav{border-top:2px solid var(--navy)}
footer{border-top:1px solid var(--line);margin-top:20px;padding-top:16px}
/* dark */
html[data-theme=dark]{--navy:#f1eeea;--gold:#d65a7c;--paper:var(--paper);--card:var(--card);--ink:#ebe9e6;--ink2:#c4c2bf;--muted:#8f8d8a;--line:var(--line);--soft:var(--soft);--hover:var(--hover);--ma50:#d4d4d8;--blue:var(--blue);--red:var(--blue);--bar:#09090a;--up:#34d399;--down:#f87171}
html[data-theme=dark] body{background:var(--paper)}
html[data-theme=dark] .top{background:var(--bar)}
html[data-theme=dark] .top .brand .mk{background:var(--gold);color:#fff}html[data-theme=dark] .top .brand{color:#fff}html[data-theme=dark] .top a.nv{color:rgba(255,255,255,.7)}html[data-theme=dark] .top a.nv.on,html[data-theme=dark] .top a.nv:hover{background:transparent;color:#fff}
html[data-theme=dark] .panel,html[data-theme=dark] .tile,html[data-theme=dark] .pill,html[data-theme=dark] .prembox{background:var(--card)}
html[data-theme=dark] .pill{color:var(--ink2)}html[data-theme=dark] .pill.on,html[data-theme=dark] .ivb.on,html[data-theme=dark] .pager button.on{background:var(--gold);border-color:var(--gold);color:#fff}
html[data-theme=dark] .cmp th{background:transparent;border-top-color:var(--gold);border-bottom-color:var(--line)}
html[data-theme=dark] .gl{stroke:var(--line)}html[data-theme=dark] .bar{background:var(--line)}
html[data-theme=dark] .readwrap,html[data-theme=dark] .side{background:var(--paper)}html[data-theme=dark] .side .prem{background:transparent}
html[data-theme=dark] .side a.on,html[data-theme=dark] .side a:hover,html[data-theme=dark] .side .prem a.on,html[data-theme=dark] .side .prem a:hover{background:var(--hover);color:var(--navy)}
html[data-theme=dark] .read .dark{background:var(--soft);border:1px solid var(--line);border-left:4px solid var(--gold);color:var(--ink)}
html[data-theme=dark] .read .box,html[data-theme=dark] .read .sum3{background:var(--soft)}html[data-theme=dark] .read tr.hl td{background:rgba(140,230,194,.08)}
html[data-theme=dark] .read th{border-bottom-color:var(--gold)}html[data-theme=dark] .read .kw{color:var(--gold)}
html[data-theme=dark] .tl-logo .logo{box-shadow:0 0 0 1px var(--line)}html[data-theme=dark] .tcard:before{background:var(--gold)}
html[data-theme=dark] .intro .ey,html[data-theme=dark] .prembox .k,html[data-theme=dark] .read .part span{color:var(--gold)}
html[data-theme=dark] .read .part{border-top-color:var(--gold)}html[data-theme=dark] .sech{border-bottom-color:var(--line)}
@media(max-width:1000px){.books{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:640px){.books{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.tcard{aspect-ratio:auto;min-height:150px}.tcard{padding:9px}.tl-logo .logo{width:40px;height:40px}.tl-nm{font-size:12px}.tl-px{font-size:11px}.tl-px span{display:block;margin:0}.tl-tag,.tl-tk{font-size:9.5px}.intro h1{font-size:26px}.sech h2{font-size:19px}}
@media(max-width:380px){.books{grid-template-columns:repeat(2,minmax(0,1fr))}}
/* ===== 블랙 & 베이지 ===== */
:root{--navy:#141210;--gold:#7A6445;--paper:#F1E9DA;--card:#F9F5EB;--ink:#161412;--ink2:#443C31;--muted:#6E6454;--line:#D9CDB4;--soft:#E8DEC9;--hover:#E2D6BD;--ma50:#141210;--blue:#6B5638;--red:#6B5638;--bar:#141210;--up:#2E7D4F;--down:#B3382C}
.top{box-shadow:inset 0 -2px 0 #E6D8BF;color:#E6D8BF}.top .brand,.top .brand .w{color:#E6D8BF}.top .brand .mk{background:#E6D8BF;color:#141210}.top .st{color:rgba(230,216,191,.7)}
.top a.nv{color:rgba(230,216,191,.82);font-weight:600}.top a.nv.on,.top a.nv:hover{color:#fff;box-shadow:inset 0 -2px 0 #E6D8BF}.top .thm{color:#E6D8BF;border-color:rgba(230,216,191,.4)}.top .thm:hover{background:rgba(230,216,191,.12)}
.pill.on,.ivb.on,.pager button.on{background:#141210;color:#E6D8BF;border-color:#141210}.sech:after{background:#141210}
html[data-theme=dark]{--navy:#E6D8BF;--gold:#D8C7A0;--paper:#0E0D0C;--card:#171513;--soft:#1F1C19;--line:#34302A;--hover:#26221E;--ink:#EFE6D4;--ink2:#CFC3AB;--muted:#9A8F7C;--ma50:#CFC3AB;--blue:#D8C7A0;--red:#D8C7A0;--bar:#050505;--up:#4ade80;--down:#f87171}
html[data-theme=dark] .top{box-shadow:inset 0 -2px 0 #E6D8BF;color:#E6D8BF}html[data-theme=dark] .top .brand,html[data-theme=dark] .top .brand .w{color:#E6D8BF}html[data-theme=dark] .top .brand .mk{background:#E6D8BF;color:#141210}html[data-theme=dark] .top a.nv{color:rgba(230,216,191,.82)}html[data-theme=dark] .top a.nv.on,html[data-theme=dark] .top a.nv:hover{color:#fff}html[data-theme=dark] .top .thm{color:#E6D8BF;border-color:rgba(230,216,191,.4)}
.hm .hmtip{width:290px;max-width:calc(100% - 8px)}.hmtip .tm{position:relative}.hmtip .tm .sk{position:absolute;right:12px;top:10px;margin:0}.hmtip .tm .sk svg{display:block}.hmtip .tr{grid-template-columns:50px 1fr 62px 58px}.hmtip .tr svg{justify-self:center}.hmtip .sp0{display:block;height:1px;background:#3b4050;width:54px;justify-self:center}
@media(max-width:560px){.hm .hmtip{width:250px}.hmtip .tr{grid-template-columns:44px 1fr 56px 52px}}
.lv{background:#141210!important;color:#E6D8BF!important}html[data-theme=dark] .lv{background:#E6D8BF!important;color:#141210!important}
html[data-theme=dark] .pill.on,html[data-theme=dark] .ivb.on,html[data-theme=dark] .pager button.on{background:#E6D8BF;color:#141210;border-color:#E6D8BF}html[data-theme=dark] .sech:after{background:#E6D8BF}
"""
THEME_INIT = "<script>(function(){try{var t=localStorage.getItem('theme')}catch(e){}if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t)})()</script>"
THEME_JS = """<script>(function(){var R=document.documentElement;
function tv(sel){document.querySelectorAll(sel||'.tvw').forEach(function(c){var cfg=JSON.parse(c.dataset.cfg);var dk=R.getAttribute('data-theme')==='dark'?'dark':'light';if('colorTheme' in cfg)cfg.colorTheme=dk;else cfg.theme=dk;
c.innerHTML='<div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>';var s=document.createElement('script');s.type='text/javascript';s.src=c.dataset.src;s.async=true;s.innerHTML=JSON.stringify(cfg);c.appendChild(s);});}
var IV='60';try{IV=localStorage.getItem('futIv')||'60'}catch(e){}
function setIv(v,re){IV=v;document.querySelectorAll('.futw').forEach(function(c){var g=JSON.parse(c.dataset.cfg);g.interval=v;c.dataset.cfg=JSON.stringify(g);});
document.querySelectorAll('.ivb').forEach(function(x){x.classList.toggle('on',x.dataset.iv===v)});try{localStorage.setItem('futIv',v)}catch(e){}if(re)tv('.futw');}
document.querySelectorAll('.ivb').forEach(function(x){x.addEventListener('click',function(){setIv(x.dataset.iv,true)})});if(document.querySelector('.futw'))setIv(IV,false);
tv();var b=document.querySelector('.thm');if(b)b.addEventListener('click',function(){var t=R.getAttribute('data-theme')==='dark'?'light':'dark';R.setAttribute('data-theme',t);try{localStorage.setItem('theme',t)}catch(e){}tv();});})();</script>"""
FONT = '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet">'


# --------------- live widgets (TradingView 공식 위젯: 방문자 브라우저가 직접 시세를 받음) ---------------
def tv_symbol(tk):
    return f'{EXCH.get(tk, "NASDAQ")}:{tk}'

def tv_chart(tk, h=440, folder=""):
    if EXCH.get(tk) == "KRX":  # 한국 종목은 트레이딩뷰 위젯에서 라이선스상 표시되지 않음 → 매일 받은 일봉으로 직접 그림
        px = CTA.get(tk, {}).get("px")
        chart = (f'<div class="panel">{stock_chart(px["d"], px["c"])}<div class="leg"><i style="background:#2563eb"></i>20일선<i style="background:var(--ma50)"></i>50일선'
                 f'<i style="background:#d97706"></i>200일선 · 최근 9개월 일봉 종가 · 매일 자동 갱신</div></div>') if px else f'<div class="hero"><img src="{folder}/tv_clean.jpg" alt="{tk} 일봉 차트"></div>'
        return chart + f'<a class="tvlink" href="https://www.tradingview.com/chart/?symbol={tv_symbol(tk)}" target="_blank" rel="noopener">트레이딩뷰에서 실시간 차트 보기 →</a>'
    cfg = {"autosize": True, "symbol": tv_symbol(tk), "interval": "D", "timezone": "Asia/Seoul", "theme": "light", "style": "1",
           "locale": "kr", "allow_symbol_change": False, "hide_side_toolbar": True, "calendar": False, "support_host": "https://www.tradingview.com",
           "studies": [{"id": "MASimple@tv-basicstudies", "inputs": {"length": 20}}, {"id": "MASimple@tv-basicstudies", "inputs": {"length": 50}},
                       {"id": "MASimple@tv-basicstudies", "inputs": {"length": 200}}]}
    return (f'<div class="tvbox" style="height:{h}px"><div class="tradingview-widget-container tvw" style="height:100%;width:100%" '
            f'data-src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" data-cfg=\'{json.dumps(cfg)}\'></div></div>')

def tv_tape():
    syms = [{"proName": "FOREXCOM:NSXUSD", "title": "나스닥100"}, {"proName": "FOREXCOM:SPXUSD", "title": "S&P500"}, {"proName": "FOREXCOM:DJI", "title": "다우"},
            {"proName": "FX_IDC:USDKRW", "title": "원/달러"}] + [{"proName": tv_symbol(r[4]), "title": r[3].replace(" 기업분석", "")} for r in REPORTS if r[4] not in ("005930", "000660")]
    cfg = {"symbols": syms, "showSymbolLogo": True, "isTransparent": True, "displayMode": "adaptive", "colorTheme": "light", "locale": "kr"}
    return ('<div class="tape"><div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div>'
            f'<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{json.dumps(cfg, ensure_ascii=False)}</script></div></div>')

def score_tag(sc):
    if sc is None: return '<span class="tag y">대기</span>'
    if sc >= 0.5: return f'<span class="tag g">매수 {sc:+.2f}</span>'
    if sc > -0.5: return f'<span class="tag y">중립 {sc:+.2f}</span>'
    return f'<span class="tag b">매도 {sc:+.2f}</span>'

def cta_box(tk):
    e = CTA.get(tk, {}); sig, sc = signals(e)
    if sig is None:
        return '<div class="ctabox"><div class="hd"><b>자동 CTA 신호</b><span>다음 자동 갱신 후 표시됩니다</span></div></div>'
    cur = e.get("cur", "$"); F = lambda v: fmt(v, cur)
    rows = "".join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td><td><span class="tag {"g" if v > 0 else "b"}">{"매수" if v > 0 else "매도"}</span></td></tr>' for a, b, c, v in sig)
    mas = " · ".join(f'{k[1:]}일 {F(e[k])}' for k in ("s5", "s20", "s50", "s100", "s200") if e.get(k))
    trend = spark(e["hist"], 200, 36, "#2563eb") if len(e.get("hist", [])) > 5 else ""
    atrp = f' · ATR {e["atr"] / e["close"] * 100:.1f}%' if e.get("atr") else ""
    return (f'<div class="ctabox"><div class="hd"><b>자동 CTA 신호</b><span>{e.get("date","")} 종가 기준 · 매일 자동 계산</span></div>'
            f'<div class="sc">{score_tag(sc)}<div class="mv">종가 {F(e["close"])} · {f'200일선 대비 {(e["close"]/e["s200"]-1)*100:+.1f}%' if e.get("s200") else '상장 기간이 짧아 200일선 없음'}'
            f'{atrp}</div>{f"<div class=tr>{trend}<small>최근 60거래일 점수 추이</small></div>" if trend else ""}</div>'
            f'<div class="tw"><table><tr><th>규칙</th><th>기준</th><th>현재 값</th><th>신호</th></tr>{rows}</table></div>'
            f'<div class="mas">이동평균선: {mas}</div>'
            f'<div class="small">아래 본문의 차트 분석(3장)은 리포트 작성 시점(2026.11.06 종가) 기준이고, 이 박스는 매일 갱신됩니다.</div></div>')

def cta_board():
    rows = []
    for r in REPORTS:
        tk = r[4]; e = CTA.get(tk, {}); sig, sc = signals(e)
        dots = "".join(f'<i class="{"pg" if x[3] > 0 else "pr"}" title="{x[0]}"></i>' for x in sig) if sig else '<span class="small">대기</span>'
        d200 = f'{((e["close"]/e["s200"]-1)*100 if e.get("s200") else 0):+.1f}%' if e.get("s200") else "-"
        trend = spark(e["hist"], 90, 22, "#2563eb") if len(e.get("hist", [])) > 5 else ""
        px, ch, c = PRICE[tk]
        live = ""
        if sig and tk not in ("005930", "000660"):
            _mk = {"1개월 모멘텀": "m1", "3개월 모멘텀": "m3", "6개월 모멘텀": "m6", "12개월 모멘텀": "m12"}
            _s = []
            for x in sig:
                if x[0] == "장기 추세 필터": _s.append([x[0], e["s200"], 0])
                elif x[0] == "돈키언 채널": _s.append([x[0], (e["dh55"] + e["dl55"]) / 2, 0])
                elif x[0] in _mk: _s.append([x[0], e[_mk[x[0]]], 0])
                else: _s.append([x[0], None, x[3]])
            live = f" data-q='{tk}' data-c='{json.dumps({'s200': e.get('s200'), 's': _s}, ensure_ascii=False)}'"
        rows.append((sc if sc is not None else -9, f'<tr{live}><td><a class="bn" href="{r[0]}"><span class="bl0">{ICON[tk]}</span><span><b>{r[3].replace(" 기업분석","")}</b><br><span class="small">{tk}</span></span></a></td><td class="r">{px}<br><span class="{c}">{ch}</span></td>'
                    f'<td class="r xd">{d200}</td><td class="dots xd">{dots}</td><td class="xd">{trend}</td><td>{score_tag(sc)}</td></tr>'))
    rows.sort(key=lambda x: -x[0])
    return ('<div class="bdtool"><div class="pills" style="margin:0"><button class="pill on" data-v="full">전체 보기</button><button class="pill" data-v="brief">간략히 보기</button></div></div>'
            '<div class="panel cmp board" id="ctaboard"><table><thead><tr><th>기업</th><th class="r">종가</th><th class="r xd">200일선 대비</th><th class="xd">8개 신호 (추세3·채널·모멘텀4)</th><th class="xd">점수 추이</th><th>CTA</th></tr></thead><tbody>'
            + "".join(x[1] for x in rows) + '</tbody></table></div><div class="pager" id="ctapager"></div>')

def fg_label(v):
    return "극단적 공포" if v < 25 else ("공포" if v < 45 else ("중립" if v <= 55 else ("탐욕" if v < 75 else "극단적 탐욕")))

def shell(title, inner, on="home"):
    nav = "".join(f'<a class="nv {"on" if on == k else ""}" href="{h}">{t}</a>' for k, h, t in
                  [("home", "index.html", "홈"), ("market", "index.html#market", "시장 지표"), ("heatmap", "index.html#heatmap", "히트맵"), ("reports", "index.html#reports", "기업분석")])
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>{FONT}{THEME_INIT}<style>{CSS}</style></head><body>
<div class="top"><div class="in"><a class="brand" href="index.html"><span class="mk">CA</span><span class="w">CORPORATE ANALYSIS</span></a>{nav}<span class="st">{STAMP}</span><button class="thm" type="button" aria-label="다크 모드 전환" title="다크 모드 전환"><span class="sun">☀</span><span class="moon">☾</span></button></div></div>
{inner}{THEME_JS}</body></html>"""

def cover(r):  # 작은 정사각 타일
    f, d, src, title, tk, comp, tag, sub, bg, line, url = r
    px, ch, c = PRICE[tk]
    dq = f' data-q="{tk}"' if tk not in ("005930", "000660") else ""
    return (f'<a class="book tcard" data-tag="{tag}"{dq} href="{f}" title="{sub}"><div class="tl-top"><span class="tl-tag">{tag}</span><span class="tl-tk">{tk}</span></div>'
            f'<div class="tl-logo">{ICON[tk]}</div><div class="tl-nm">{title.replace(" 기업분석","")}</div>'
            f'<div class="tl-px">{px} <span class="{c}">{ch}</span></div></a>')

# --------------- read pages ---------------
def side(active):
    items = "".join(f'<a class="{"on" if r[0] == active else ""}" href="{r[0]}">{r[3]}</a>' for r in REPORTS)
    return (f'<aside class="side"><a href="index.html">🏠 홈</a><a href="index.html#market">📈 시장 지표</a><a href="index.html#reports">📚 기업분석</a>'
            f'<div class="prem"><div class="t" style="color:var(--muted)">REPORTS</div>{items}</div>'
            f'<div class="h">자료 기준</div><div style="font-size:12px;color:var(--muted);padding:0 8px">각 사 IR 실적 발표문·컨퍼런스콜·10-K, 트레이딩뷰(11/6 종가). 작도 없는 기본 차트만 사용.</div></aside>')

for i, r in enumerate(REPORTS):
    f, d, src, title, tk, comp, tag, sub, cols, line, url = r
    body = bullify(merged(src), d)
    px, ch, c = PRICE[tk]
    hero_img = f"{d}/tv_clean.jpg"
    prev = REPORTS[i - 1] if i > 0 else None; nxt = REPORTS[i + 1] if i < len(REPORTS) - 1 else None
    endnav = '<div class="endnav">' + (f'<a href="{prev[0]}">← {prev[3]}</a>' if prev else "<span></span>") + (f'<a href="{nxt[0]}">{nxt[3]} →</a>' if nxt else "<span></span>") + "</div>"
    inner = f"""<div class="readwrap">{side(f)}<div class="read">
<div class="rhead"><a href="index.html#reports">←</a><div><div class="t">{title}</div><div class="a">Corporate Analysis · 2026.11</div></div></div>
<div class="prembox"><div class="ic">{ICON[tk]}</div><div><div class="k">REPORT · {tag}</div>{sub} — 8개 분기 공시·컨퍼런스콜과 트레이딩뷰 데이터를 바탕으로 정리했습니다.</div></div>
{tv_chart(tk, folder=d)}<div class="cap">{comp} {"일봉 차트 (이동평균선 20·50·200) · 한국 종목은 트레이딩뷰 위젯 미지원으로 직접 계산" if EXCH.get(tk) == "KRX" else "실시간 차트 (트레이딩뷰 위젯, 이동평균선 20·50·200) · 시세는 거래소별로 실시간 또는 지연"}</div>
<div class="stock"><div class="lg">{ICON[tk]}</div><div><div class="n">{comp} <small>({tk})</small></div><div class="s">{line}</div><div class="u">{url}</div></div><div class="p">{px}<small class="{c}">{ch}</small></div></div>
{cta_box(tk)}{body}{endnav}</div></div>"""
    open(f"{OUT}/{f}", "w", encoding="utf-8").write(shell(title, inner, "reports"))

# --------------- home ---------------
LIVE = {"NQ": ("FOREXCOM:NSXUSD", "나스닥100"), "ES": ("FOREXCOM:SPXUSD", "S&P500"), "YM": ("FOREXCOM:DJI", "다우존스")}
FUT_IV = [("60", "1시간"), ("240", "4시간"), ("D", "1일"), ("W", "1주")]
def fut(k, name, sym):  # 실시간: 트레이딩뷰 차트 위젯 (CME 선물은 위젯에서 막혀 있어 거의 24시간 거래되는 지수 CFD로 표시)
    p, pc, ab = SNAP[k]; tvs, short = LIVE[k]
    cfg = {"autosize": True, "symbol": tvs, "interval": "60", "timezone": "Asia/Seoul", "theme": "light", "style": "1", "locale": "kr",
           "hide_top_toolbar": True, "hide_side_toolbar": True, "hide_legend": False, "hide_volume": True, "allow_symbol_change": False,
           "save_image": False, "calendar": False, "support_host": "https://www.tradingview.com",
           "studies": [{"id": "MASimple@tv-basicstudies", "inputs": {"length": 20}}]}
    pills = "".join(f'<button class="ivb{" on" if v == "60" else ""}" data-iv="{v}">{t}</button>' for v, t in FUT_IV)
    return (f'<div class="panel fut live"><div class="fhd"><div class="nm">{name} · 실시간 <span class="lv">LIVE</span></div><div class="ivs">{pills}</div></div>'
            f'<div class="tvmini"><div class="tradingview-widget-container tvw futw" style="height:100%;width:100%" '
            f'data-src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" data-cfg=\'{json.dumps(cfg, ensure_ascii=False)}\'></div></div>'
            f'<div class="leg">{short} 지수 CFD({tvs.split(":")[1]}) · 이동평균 20 · {sym} 전일 종가 {p:,.2f} <span class="{cls(pc)}">({sign(pc, 2, True)})</span> · 선물과 약간 차이 날 수 있음</div></div>')
def tile_live(name, sym, rng="1M"):  # 트레이딩뷰 미니 시세 위젯 (실시간)
    cfg = {"symbol": sym, "width": "100%", "height": "100%", "locale": "kr", "dateRange": rng, "colorTheme": "light",
           "isTransparent": True, "autosize": True, "largeChartUrl": "", "chartOnly": False, "noTimeScale": True}
    return (f'<div class="tile live"><div class="nm">{name} <span class="lvd"></span></div><div class="tvtile"><div class="tradingview-widget-container tvw" style="height:100%;width:100%" '
            f'data-src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" data-cfg=\'{json.dumps(cfg, ensure_ascii=False)}\'></div></div></div>')
MACRO_LIVE = [("VIX 변동성 지수", None), ("달러 인덱스 (DXY)", "PEPPERSTONE:USDX"), ("원/달러 환율", "FX_IDC:USDKRW"), ("달러/엔 환율", "FX:USDJPY"),
              ("WTI 유가", "TVC:USOIL"), ("금 선물 (GC)", None)]
# 트레이딩뷰가 위젯에 막아 둔 심볼(VIX 지수·미국 20년물·일본 국채)은 매일 받는 종가 타일로 표시
RATE_LIVE = [("미국 2년물", None), ("미국 10년물", None), ("미국 20년물", None), ("미국 30년물", None),
             ("일본 2년물", None), ("일본 10년물", None)]
CNBC_SYM = {"VIX 변동성 지수": ".VIX", "금 선물 (GC)": "@GC.1", "미국 2년물": "US2Y", "미국 10년물": "US10Y", "미국 30년물": "US30Y", "미국 20년물": "US20Y", "일본 2년물": "JP2Y", "일본 10년물": "JP10Y"}  # 1분마다 CNBC 시세로 덮어씀
DAILY_KEY = {"VIX 변동성 지수": ("VIX", "", 2, ""), "금 선물 (GC)": ("GC", "$", 1, ""), "미국 2년물": ("US02Y", "%", 2, "%p"), "미국 10년물": ("US10Y", "%", 2, "%p"), "미국 20년물": ("US20Y", "%", 2, "%p"), "미국 30년물": ("US30Y", "%", 2, "%p"), "일본 2년물": ("JP02Y", "%", 2, "%p"), "일본 10년물": ("JP10Y", "%", 2, "%p")}
def tile_any(n, y):
    if y: return tile_live(n, y)
    k, u, d, au = DAILY_KEY[n]
    if k not in SNAP or k not in SER: return ""
    t = tile(k, f'{n} <span class="dly">일간</span>', u, d, au)
    return t.replace('<div class="tile">', f'<div class="tile poll" data-q="{CNBC_SYM[n]}" data-y="{1 if u == "%" else 0}" data-d="{d}" data-pre="{"$" if u == "$" else ""}">', 1)
def heatmap():  # 자체 제작 S&P500 히트맵 (Finviz 방식): CNBC 실시간 시세를 방문자 브라우저에서 1분마다 받아 그림
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from finviz_ko import SEC_KO, IND_KO
    d = {}
    for line in open(os.path.join(_D, "finviz_groups.txt"), encoding="utf-8").read().splitlines():
        if ":" in line:
            k, v = line.split(":", 1); sec, ind = k.split("|")
            d.setdefault(SEC_KO[sec], {})[IND_KO[ind]] = v.split()
    js = open(os.path.join(_D, "heatmap.js"), encoding="utf-8").read().replace("__DATA__", json.dumps(d, ensure_ascii=False))
    return ('<div class="panel hm" id="hm"><div class="hmbar"><span id="hmst" class="hmst">불러오는 중…</span></div>'
            '<div class="hmctl"><label>그룹 <select id="hmg"><option value="si">섹터 › 산업</option><option value="s">섹터</option><option value="n">그룹 없음</option></select></label>'
            '<label>섹터 <select id="hms"><option value="">전체</option></select></label>'
            '<label>크기 <select id="hmz"><option value="cap">시가총액</option><option value="eq">동일</option></select></label>'
            '<label class="hmck"><input type="checkbox" id="hmlogo"> 로고</label>'
            '<span class="hmvw"><button class="pill on" data-v="map" type="button">히트맵</button><button class="pill" data-v="list" type="button">목록</button></span></div>'
            '<div id="hmbox" class="hmbox"></div><div id="hmlist" class="hmlist" hidden></div>'
            '<div class="hmfoot"><span>색은 오늘의 등락률(%)입니다. 빨강 하락 · 검정 보합 · 초록 상승</span><span class="hmlg" id="hmlg"></span></div>'
            '<div id="hmtip" class="hmtip"></div></div><script>' + js + '</script>')
def fut_daily(k, name, sym):
    p, pc, ab = SNAP[k]
    return (f'<div class="panel fut"><div class="nm">{name} · {sym}</div><div class="px">{p:,.2f}</div><div class="ch {cls(pc)}">{sign(ab)} ({sign(pc, 2, True)})</div>'
            f'{bigchart(SER[k]["close"], SER[k]["dates"])}<div class="leg"><i style="background:#2563eb"></i>20일선<i style="background:var(--ma50)"></i>50일선 · 최근 6개월 일봉 종가</div></div>')
def tile(k, name, unit="", d=2, absunit=""):
    p, pc, ab = SNAP[k]
    chg = f"{ab:+.2f}%p" if absunit == "%p" else f"{sign(ab, d)} ({sign(pc, 2, True)})"
    pre="$" if unit=="$" else ""; unit="" if unit=="$" else unit
    return f'<div class="tile"><div class="nm">{name}</div><div class="px">{pre}{p:,.{d}f}{unit}</div><div class="ch {cls(ab)}">{chg}</div>{spark(SER[k]["close"])}</div>'

hist_rows = "".join(f'<tr><td>{a}</td><td style="text-align:right;font-weight:700">{v:.0f}</td><td style="color:var(--muted)">{lab}</td></tr>' for a, v, lab in
                    [(a, FG[k], fg_label(FG[k])) for a, k in [("현재", "score"), ("전일 종가", "prev"), ("1주 전", "w"), ("1개월 전", "m"), ("1년 전", "y")]])
def bcol(v): return "#dc2626" if v < 25 else ("#f97316" if v < 45 else ("#a3a3a3" if v <= 55 else ("#84cc16" if v < 75 else "#16a34a")))
comp_rows = "".join(f'<tr><td><b>{a}</b><br><span style="font-size:12px;color:var(--muted)">{s}</span></td><td><span class="bar"><span style="width:{v}%;background:{bcol(v)}"></span></span> {v}</td><td style="font-size:12.5px;color:{bcol(v)};font-weight:700">{lab}</td></tr>' for a, s, v, lab in FG["comp"])

def curve_svg(pts, title):
    w, h = 520, 190; xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    lo, hi = min(ys) - .2, max(ys) + .2
    X = lambda i: 30 + i * (w - 60) / (len(pts) - 1); Y = lambda v: 15 + (hi - v) / (hi - lo) * (h - 45)
    path = "M" + " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ys))
    dots = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.5" fill="#2f5aa8"/><text x="{X(i):.1f}" y="{Y(v)-8:.1f}" text-anchor="middle" font-size="11" font-weight="700" style="fill:var(--ink)">{v:.3f}%</text><text x="{X(i):.1f}" y="{h-8}" text-anchor="middle" class="ax">{xs[i]}</text>' for i, v in enumerate(ys))
    return f'<div class="panel"><div style="font-weight:700;color:var(--ink);font-size:14px">{title}</div><svg viewBox="0 0 {w} {h}" style="width:100%">{"".join(f"<line x1=30 x2={w-30} y1={Y(lo+(hi-lo)*t/4):.1f} y2={Y(lo+(hi-lo)*t/4):.1f} class=gl />" for t in range(5))}<path d="{path}" fill="none" stroke="#2f5aa8" stroke-width="2"/>{dots}</svg></div>'

_vix = SNAP.get("VIX", [0])[0]; _fg = FG["score"]
ONE_LINE = (f'VIX {_vix:.1f}·공포탐욕 {_fg:.0f}로 <b class="{"down" if _fg < 45 else ("up" if _fg > 55 else "")}">{fg_label(_fg)}</b> 구간. '
            + ("변동성이 높아 단기 급등락에 유의." if _vix >= 20 else "변동성은 안정적인 편."))
RATE_NAMES = [("US02Y", "미국 2년물 · US02Y"), ("US10Y", "미국 10년물 · US10Y"), ("US20Y", "미국 20년물 · US20Y"), ("US30Y", "미국 30년물 · US30Y"), ("JP02Y", "일본 2년물 · JP02Y"), ("JP10Y", "일본 10년물 · JP10Y")]
_rates = [(k, n) for k, n in RATE_NAMES if k in SNAP and k in SER][:6]
RATE_TILES = "".join(tile(k, n, "%", 3, "%p") for k, n in _rates)
RATE_SUB = " · ".join(n for _, n in _rates)
CTA_DATE = max((e.get("date", "") for e in CTA.values()), default="")

CTA_JS = open(os.path.join(_D, "cta.js"), encoding="utf-8").read()
FG_JS = open(os.path.join(_D, "fg.js"), encoding="utf-8").read()
CARDS_JS = open(os.path.join(_D, "cards.js"), encoding="utf-8").read()
home = f"""<main class="home">
<div class="intro"><div class="ey">EQUITY RESEARCH · {ASOF:%Y.%m.%d}</div><h1>실적과 공시로 읽는 기업,<br>숫자로 확인하는 시장</h1></div>
<section id="market">
<div class="sech"><h2>미국 지수 선물</h2><span class="sm">{STAMP}</span></div>
<div class="grid3">{fut("NQ","나스닥100 선물","NQ1!")}{fut("ES","S&P500 선물","ES1!")}{fut("YM","다우존스 선물","YM1!")}</div>

<div class="sech" id="heatmap"><h2>S&amp;P500 히트맵</h2><span class="sm">실시간 · 섹터 › 산업 묶음 · 칸 크기 = 시가총액, 색 = 전일 종가 대비 등락률 · CNBC 시세 1분 갱신 · 섹터·산업 분류 Finviz 기준</span></div>
{heatmap()}

<div class="sech"><h2>CNN 공포·탐욕 지수</h2><span class="sm" id="fgasof">Fear &amp; Greed Index · CNN 기준 {FG["asof"]}</span></div>
<div class="panel fgwrap">
<div>{gauge(FG["score"])}<div class="fgnum" id="fgnum"><b style="color:{bcol(FG["score"])}">{FG["score"]:.0f}</b><div style="color:{bcol(FG["score"])}">{FG["rating"]}</div></div>
<div style="margin-top:10px" id="fgspk">{spark(FG["hist"], 260, 46, bcol(FG["score"]))}</div><div class="note" style="text-align:center;margin-top:2px">최근 약 3.5개월 추이</div></div>
<table class="hist" id="fghist" style="width:100%;border-collapse:collapse"><tr><td colspan="3" style="font-weight:700;color:var(--ink)">시점별 비교</td></tr>{hist_rows}</table>
<table class="comp" id="fgcomp" style="width:100%;border-collapse:collapse"><tr><td colspan="3" style="font-weight:700;color:var(--ink)">7개 구성 지표</td></tr>{comp_rows}</table>
</div>

<div class="sech"><h2>변동성 · 달러 · 환율 · 원자재</h2><span class="sm">실시간 · 트레이딩뷰 (달러 인덱스·유가는 CFD 시세) · VIX·금 선물은 CNBC 시세 1분 갱신</span></div>
<div class="tiles">{"".join(tile_any(n, y) for n, y in MACRO_LIVE)}</div>
<div class="note oneline"><b>한 줄 해석</b> · {ONE_LINE} <span style="opacity:.7">(전일 종가 기준)</span></div>

<div class="sech"><h2>국채 금리</h2><span class="sm">CNBC 시세 1분 갱신 · 소수점 둘째 자리</span></div>
<div class="tiles">{"".join(tile_any(n, y) for n, y in RATE_LIVE)}</div>

<div class="note">데이터: Yahoo Finance(선물·지수·환율·원자재), 미국 재무부·일본 재무성(국채 금리), CNN Business(공포·탐욕 지수). 매일 미국장 마감 후(06:30 KST)와 한국장 마감 후(16:00 KST) 자동 갱신됩니다. 선물·히트맵·변동성·환율·원자재·국채 금리 칸과 기업별 차트는 트레이딩뷰 위젯으로 장중에 실시간(일부 지연) 반영됩니다.</div>
</section>

<section id="cta">
<div class="sech"><h2>CTA 스코어보드</h2><span class="sm">8개 추세추종 신호 평균 · 이동평균 {CTA_DATE} 종가 기준 · 현재가 1분 갱신(미국 종목)</span></div>
{cta_board()}
<div class="note">점수 +1은 8개 신호가 모두 매수, -1은 모두 매도입니다. 추세추종(CTA) 자금의 움직임을 흉내 낸 자체 계산 모델이며, 실제 증권사 CTA 포지션 데이터가 아닙니다.</div>
</section>

<section id="reports">
<div class="sech"><h2>기업분석</h2><span class="sm">실적 + 심층 분석 통합 · 31개 기업 · 미국 종목 등락률 1분 갱신</span></div>
<div class="pills"><button class="pill on" data-f="all">전체</button><button class="pill" data-f="반도체">반도체</button><button class="pill" data-f="빅테크">빅테크</button><button class="pill" data-f="소프트웨어">소프트웨어·클라우드</button><button class="pill" data-f="양자">양자컴퓨팅</button><button class="pill" data-f="헬스케어">헬스케어</button><button class="pill" data-f="금융">금융</button><button class="pill" data-f="소비재">소비재</button></div>
<div class="books">{"".join(cover(r) for r in REPORTS)}</div>

</section>
</main>
<footer>개인 학습용 분석이며 특정 종목의 매수·매도를 권유하지 않습니다. 모든 투자의 책임은 개인에게 있습니다.</footer>
<script>{FG_JS}{CARDS_JS}{CTA_JS}</script>
<script>(function(){{const T=[...document.querySelectorAll('.tile.poll')];if(!T.length)return;
const U='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols='+T.map(t=>encodeURIComponent(t.dataset.q)).join('|');
const n=v=>parseFloat(String(v).replace(/[%,+]/g,''));
async function upd(){{try{{const j=await (await fetch(U,{{cache:'no-store'}})).json();const Q={{}};(j.FormattedQuoteResult.FormattedQuote||[]).forEach(q=>Q[q.symbol]=q);
const now=new Date().toLocaleTimeString('ko-KR',{{hour:'2-digit',minute:'2-digit',hour12:false}});
T.forEach(t=>{{const q=Q[t.dataset.q];if(!q||q.last==null)return;const L=n(q.last);if(isNaN(L))return;let C=n(q.change);if(isNaN(C)){{const pv0=n(q.previous_day_closing);C=isNaN(pv0)?0:L-pv0;}}const y=t.dataset.y==='1';
const D=+(t.dataset.d||2),F=v=>v.toLocaleString('en-US',{{minimumFractionDigits:D,maximumFractionDigits:D}});t.querySelector('.px').textContent=y?L.toFixed(D)+'%':(t.dataset.pre||'')+F(L);const c=t.querySelector('.ch');const pv=n(q.previous_day_closing);
c.textContent=y?(C>=0?'+':'')+C.toFixed(D)+'%p':(C>=0?'+':'')+F(C)+' ('+(C>=0?'+':'')+(pv?(C/pv*100):0).toFixed(2)+'%)';
c.className='ch '+(C>0?'up':C<0?'down':'');const b=t.querySelector('.dly');if(b){{b.textContent='1분 · '+now;b.classList.add('on');}}}});}}catch(e){{}}}}
upd();setInterval(()=>{{if(!document.hidden)upd();}},60000);document.addEventListener('visibilitychange',()=>{{if(!document.hidden)upd();}});}})();
(function(){{const B=document.getElementById('ctaboard'),P=document.getElementById('ctapager');if(!B)return;const rows=[...B.querySelectorAll('tbody tr')],N=10,pages=Math.ceil(rows.length/N);let cur=0;
function show(i){{cur=i;rows.forEach((r,k)=>r.style.display=(k>=i*N&&k<(i+1)*N)?'':'none');if(pages<2){{P.innerHTML='';return;}}
let h='<button data-p="'+(i-1)+'"'+(i===0?' disabled':'')+'>‹</button>';for(let k=0;k<pages;k++)h+='<button data-p="'+k+'" class="'+(k===i?'on':'')+'">'+(k+1)+'</button>';
h+='<button data-p="'+(i+1)+'"'+(i===pages-1?' disabled':'')+'>›</button><span class="pi">'+(i*N+1)+'–'+Math.min((i+1)*N,rows.length)+' / '+rows.length+'개</span>';P.innerHTML=h;}}
P.addEventListener('click',e=>{{const b=e.target.closest('button');if(b&&!b.disabled)show(+b.dataset.p);}});show(0);
let v=matchMedia('(max-width:640px)').matches?'brief':'full';try{{v=localStorage.getItem('ctaView')||v}}catch(e){{}}const vb=document.querySelectorAll('[data-v]');
function setV(x){{B.classList.toggle('brief',x==='brief');vb.forEach(b=>b.classList.toggle('on',b.dataset.v===x));try{{localStorage.setItem('ctaView',x)}}catch(e){{}}}}
vb.forEach(b=>b.addEventListener('click',()=>setV(b.dataset.v)));setV(v);}})();
document.querySelectorAll('.pill[data-f]').forEach(p=>p.addEventListener('click',()=>{{document.querySelectorAll('.pill[data-f]').forEach(x=>x.classList.toggle('on',x===p));const f=p.dataset.f;document.querySelectorAll('.book').forEach(b=>b.style.display=(f==='all'||b.dataset.tag===f)?'':'none');}}));</script>"""
open(f"{OUT}/index.html", "w", encoding="utf-8").write(shell("Corporate Analysis — 시장 지표 · 기업분석", home, "home"))
print("ok", sorted(os.listdir(OUT)))
