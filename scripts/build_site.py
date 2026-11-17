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
 ("micron.html", "mu", [CONTENT + "/mu/body.html"], "Micron Technology 기업분석", "MU", "Micron Technology, Inc.", "반도체", "FQ4 매출 +379% · 영업이익률 81% · CTA -0.50", "#eef2ff", "반도체 · 직원 약 6.1만 명", "https://www.micron.com"),
 ("alphabet.html", "googl", [CONTENT + "/googl/body.html"], "Alphabet 기업분석", "GOOGL", "Alphabet Inc. Class A", "빅테크", "클라우드 +103% · FCF 마이너스 · CTA -0.75", "#ecfdf5", "인터넷 서비스 · 직원 204,757명", "https://abc.xyz"),
 ("microsoft.html", "msft", [CONTENT + "/msft/body.html"], "Microsoft 기업분석", "MSFT", "Microsoft Corporation", "빅테크", "Azure +48% · PER 27.7배 · CTA +1.00", "#f0f9ff", "패키지 소프트웨어", "https://www.microsoft.com"),
 ("amazon.html", "amzn", [CONTENT + "/amzn/body.html"], "Amazon 기업분석", "AMZN", "Amazon.com, Inc.", "빅테크", "AWS +39% · FCF -$424억 · CTA +0.50", "#fff7ed", "인터넷 유통", "https://www.amazon.com"),
 ("nvidia.html", "nvda", [CONTENT + "/nvda/body.html"], "NVIDIA 기업분석", "NVDA", "NVIDIA Corporation", "반도체", "FY27Q2 매출 +106% · PER 23.6배 · CTA -0.75", "#f0fdf4", "반도체", "https://www.nvidia.com"),
 ("marvell.html", "mrvl", [CONTENT + "/mrvl/body.html"], "Marvell 기업분석", "MRVL", "Marvell Technology, Inc.", "반도체", "FY28 가이던스 $18B · 루멘텀 인수 · CTA -0.50", "#f5f3ff", "반도체", "https://www.marvell.com"),
 ("samsung.html", "sec", [CONTENT + "/sec/body.html"], "삼성전자 기업분석", "005930", "삼성전자", "반도체", "영업이익 107조 · EV/영업이익 2.8배 · CTA -0.50", "#eff6ff", "반도체·전자", "https://www.samsung.com/sec"),
 ("skhynix.html", "skh", [CONTENT + "/skh/body.html"], "SK하이닉스 기업분석", "000660", "SK하이닉스", "반도체", "영업이익률 80% · EV/EBITDA 2.6배 · CTA -0.50", "#fef2f2", "메모리 반도체", "https://www.skhynix.com"),
 ("tsmc.html", "tsm", [CONTENT + "/tsm/body.html"], "TSMC 기업분석", "TSM", "Taiwan Semiconductor Manufacturing Co.", "반도체", "3Q26 매출 +41% · PER 24.2배 · CTA -0.50", "#f0fdfa", "반도체 위탁생산", "https://www.tsmc.com"),
 ("broadcom.html", "avgo", [CONTENT + "/avgo/body.html"], "Broadcom 기업분석", "AVGO", "Broadcom Inc.", "반도체", "AI +221% · PER 37.5배 · CTA -1.00", "#fff1f2", "반도체·소프트웨어", "https://www.broadcom.com"),
 ("amd.html", "amd", [CONTENT + "/amd/body.html"], "AMD 기업분석", "AMD", "Advanced Micro Devices, Inc.", "반도체", "데이터센터 +97% · PER 97.6배 · CTA -0.25", "#f1f5f9", "반도체", "https://www.amd.com"),
 ("intel.html", "intc", [CONTENT + "/intc/body.html"], "Intel 기업분석", "INTC", "Intel Corporation", "반도체", "DCAI +78% · GAAP 적자 · CTA -0.50", "#eef6ff", "반도체", "https://www.intel.com"),
 ("qualcomm.html", "qcom", [CONTENT + "/qcom/body.html"], "Qualcomm 기업분석", "QCOM", "QUALCOMM Incorporated", "반도체", "자동차 +89% · 핸드셋 -26% · 데이터센터 $5B", "#f0f4ff", "반도체(팹리스)", "https://www.qualcomm.com"),
 ("oracle.html", "orcl", [CONTENT + "/orcl/body.html"], "Oracle 기업분석", "ORCL", "Oracle Corporation", "소프트웨어", "OCI +121% · RPO $664B · FCF 마이너스", "#fff5f5", "소프트웨어·클라우드", "https://www.oracle.com"),
 ("palantir.html", "pltr", [CONTENT + "/pltr/body.html"], "Palantir 기업분석", "PLTR", "Palantir Technologies Inc.", "소프트웨어", "매출 +96% · 순이익률 49% · TCV 둔화", "#f4f4f5", "소프트웨어", "https://www.palantir.com"),
 ("meta.html", "meta", [CONTENT + "/meta/body.html"], "Meta 기업분석", "META", "Meta Platforms, Inc.", "빅테크", "매출 +26% · 이익률 20% · 설비투자 $140B", "#eef4ff", "인터넷 서비스", "https://about.meta.com"),
 ("coreweave.html", "crwv", [CONTENT + "/crwv/body.html"], "CoreWeave 기업분석", "CRWV", "CoreWeave, Inc.", "데이터센터", "AI 클라우드 · 잔고 $104B · 부채 $35B", "#f5f3ff", "AI 클라우드", "https://www.coreweave.com"),
 ("tesla.html", "tsla", [CONTENT + "/tsla/body.html"], "Tesla 기업분석", "TSLA", "Tesla, Inc.", "빅테크", "FSD 174만 · 영업이익률 2.6% · PER 394배", "#fff1f2", "자동차·에너지·AI", "https://www.tesla.com"),
 ("spacex.html", "spcx", [CONTENT + "/spcx/body.html"], "SpaceX 기업분석", "SPCX", "Space Exploration Technologies Corp.", "우주항공", "매출 +161% · AI(SI) $76억 · 첫 흑자", "#f1f5f9", "우주·통신·AI", "https://www.spacex.com"),
 ("dell.html", "dell", [CONTENT + "/dell/body.html"], "Dell 기업분석", "DELL", "Dell Technologies Inc.", "반도체", "AI 서버 잔고 $950억 · 매출 +58%", "#eff6ff", "IT 하드웨어", "https://www.dell.com"),
 ("sandisk.html", "sndk", [CONTENT + "/sndk/body.html"], "Sandisk 기업분석", "SNDK", "Sandisk Corporation", "반도체", "매출총이익률 85% · PER 6.7배 · CTA -0.50", "#fef2f2", "메모리 반도체", "https://www.sandisk.com"),
 ("crowdstrike.html", "crwd", [CONTENT + "/crwd/body.html"], "CrowdStrike 기업분석", "CRWD", "CrowdStrike Holdings, Inc.", "사이버 보안", "순신규 ARR +51% · AI 보안", "#fff1f2", "사이버 보안", "https://www.crowdstrike.com"),
 ("nebius.html", "nbis", [CONTENT + "/nbis/body.html"], "Nebius 기업분석", "NBIS", "Nebius Group N.V.", "데이터센터", "AI 클라우드 · 매출 +571% · 첫 영업흑자", "#f7fee7", "AI 클라우드", "https://nebius.com"),
 ("apple.html", "aapl", [CONTENT + "/aapl/body.html"], "Apple 기업분석", "AAPL", "Apple Inc.", "빅테크", "FY26 매출 $479B · 아이폰 듀오 · 메모리 비용", "#f8fafc", "소비자 전자", "https://www.apple.com"),
 ("eli-lilly.html", "lly", [CONTENT + "/lly/body.html"], "Eli Lilly 기업분석", "LLY", "Eli Lilly and Company", "헬스케어", "비만약 매출 66% · PEG 0.92 · CTA +1.0", "#fdf2f8", "제약", "https://www.lilly.com"),
 ("jpmorgan.html", "jpm", [CONTENT + "/jpm/body.html"], "JPMorgan Chase 기업분석", "JPM", "JPMorgan Chase & Co.", "금융", "ROTCE 20% · PEG 0.79 · P/TBV 3배", "#eff6ff", "은행", "https://www.jpmorganchase.com"),
 ("texas-instruments.html", "txn", [CONTENT + "/txn/body.html"], "Texas Instruments 기업분석", "TXN", "Texas Instruments Incorporated", "반도체", "TTM PER 38배 · CTA 강한 매수", "#eff6ff", "아날로그 반도체", "https://www.ti.com"),
 ("ast-spacemobile.html", "asts", [CONTENT + "/asts/body.html"], "AST SpaceMobile 기업분석", "ASTS", "AST SpaceMobile, Inc.", "우주항공", "위성 직접 통신 · 현금 소진 점검", "#f5f3ff", "통신 위성", "https://www.ast-science.com"),
 ("rocket-lab.html", "rklb", [CONTENT + "/rklb/body.html"], "Rocket Lab 기업분석", "RKLB", "Rocket Lab Corporation", "우주항공", "발사·우주시스템 · 흑자 전환 점검", "#f5f3ff", "우주", "https://www.rocketlabusa.com"),
 ("servicenow.html", "now", [CONTENT + "/now/body.html"], "ServiceNow 기업분석", "NOW", "ServiceNow, Inc.", "소프트웨어", "엔터프라이즈 AI 워크플로 · 분할 후 PER 74배", "#f5f3ff", "SaaS", "https://www.servicenow.com"),
 ("salesforce.html", "crm", [CONTENT + "/crm/body.html"], "Salesforce 기업분석", "CRM", "Salesforce, Inc.", "소프트웨어", "PEG 0.33 · GAAP 왜곡 점검", "#f5f3ff", "SaaS", "https://www.salesforce.com"),
 ("reddit.html", "rddt", [CONTENT + "/rddt/body.html"], "Reddit 기업분석", "RDDT", "Reddit, Inc.", "커뮤니티", "PEG 0.11 · 광고 성장", "#fff7ed", "소셜 플랫폼", "https://www.redditinc.com"),
 ("supermicro.html", "smci", [CONTENT + "/smci/body.html"], "Super Micro Computer 기업분석", "SMCI", "Super Micro Computer, Inc.", "데이터센터", "PER 6.0배 · PEG 0.02", "#eff6ff", "AI 서버", "https://www.supermicro.com"),
 ("iren.html", "iren", [CONTENT + "/iren/body.html"], "IREN 기업분석", "IREN", "IREN Limited", "데이터센터", "AI 클라우드 전환 · 적자", "#f5f3ff", "AI 인프라", "https://www.iren.com"),
 ("western-digital.html", "wdc", [CONTENT + "/wdc/body.html"], "Western Digital 기업분석", "WDC", "Western Digital Corporation", "컴퓨터 하드웨어", "HDD AI 수요 · PER 11배", "#eff6ff", "저장장치", "https://www.westerndigital.com"),
 ("vertiv.html", "vrt", [CONTENT + "/vrt/body.html"], "Vertiv 기업분석", "VRT", "Vertiv Holdings Co", "데이터센터", "유기적 주문 +100% · 주가 -47%", "#eff6ff", "데이터센터 전력·냉각", "https://www.vertiv.com"),
 ("coherent.html", "cohr", [CONTENT + "/cohr/body.html"], "Coherent 기업분석", "COHR", "Coherent Corp.", "광통신", "광통신 · FCF -$18억", "#eff6ff", "광 트랜시버", "https://www.coherent.com"),
 ("strategy.html", "mstr", [CONTENT + "/mstr/body.html"], "Strategy 기업분석", "MSTR", "Strategy Inc.", "코인", "BTC 848,517개 · mNAV 0.77", "#f5f3ff", "비트코인 보유", "https://www.strategy.com"),
 ("unitedhealth.html", "unh", [CONTENT + "/unh/body.html"], "UnitedHealth 기업분석", "UNH", "UnitedHealth Group Incorporated", "헬스케어", "이익 V자 회복 · MCR 88.4%", "#f0f9ff", "건강보험·의료", "https://www.unitedhealthgroup.com"),
 ("cocacola.html", "ko", [CONTENT + "/ko/body.html"], "Coca-Cola 기업분석", "KO", "The Coca-Cola Company", "소비재", "3Q 판매량 +5% · PEG 2.34(조정 약 2.5) · CTA +1.00", "#fef2f2", "음료", "https://www.coca-colacompany.com"),
 ("walmart.html", "wmt", [CONTENT + "/wmt/body.html"], "Walmart 기업분석", "WMT", "Walmart Inc.", "소비재", "이커머스 +23% · PER 45배", "#eff6ff", "유통", "https://corporate.walmart.com"),
 ("costco.html", "cost", [CONTENT + "/cost/body.html"], "Costco 기업분석", "COST", "Costco Wholesale Corporation", "소비재", "회원비 = 영업이익 51% · PER 51배", "#fef2f2", "회원제 유통", "https://www.costco.com"),
 ("ionq.html", "ionq", [CONTENT + "/ionq/body.html"], "IonQ 기업분석", "IONQ", "IonQ, Inc.", "양자", "양자 · 매출 +336% · 런웨이 약 3년", "#f5f3ff", "양자컴퓨팅", "https://ionq.com"),
 ("ibm.html", "ibm", [CONTENT + "/ibm/body.html"], "IBM 기업분석", "IBM", "International Business Machines Corporation", "소프트웨어", "현금 창출 · 조정 PEG 1.65 · CTA +0.50", "#eef2ff", "IT 서비스·소프트웨어", "https://www.ibm.com"),
 ("unusual-machines.html", "umac", [CONTENT + "/umac/body.html"], "Unusual Machines 기업분석", "UMAC", "Unusual Machines, Inc.", "드론", "미국산 드론 부품 · 매출 +551% · CTA -0.50", "#f0fdf4", "드론 부품", "https://unusualmachines.com"),
 ("joby.html", "joby", [CONTENT + "/joby/body.html"], "Joby Aviation 기업분석", "JOBY", "Joby Aviation, Inc.", "드론", "에어택시 · 현금 $22억 · CTA -0.75", "#f0f9ff", "전기 에어택시", "https://www.jobyaviation.com"),
 ("archer.html", "achr", [CONTENT + "/achr/body.html"], "Archer Aviation 기업분석", "ACHR", "Archer Aviation Inc.", "드론", "에어택시·방산 · 현금 $13.5억 · CTA -1.00", "#f5f3ff", "전기 에어택시", "https://archer.com"),
 ("ondas.html", "onds", [CONTENT + "/onds/body.html"], "Ondas 기업분석", "ONDS", "Ondas Inc.", "드론", "자율 드론 방산 · 매출 +100% · CTA -1.00", "#fff7ed", "자율 드론·방산", "https://www.ondas.com"),
 ("ge-vernova.html", "gev", [CONTENT + "/gev/body.html"], "GE Vernova 기업분석", "GEV", "GE Vernova Inc.", "전력·에너지", "수주잔고 $1,970억 · PER 21배 · CTA -0.75", "#ecfdf5", "발전 설비", "https://www.gevernova.com"),
 ("constellation.html", "ceg", [CONTENT + "/ceg/body.html"], "Constellation Energy 기업분석", "CEG", "Constellation Energy Corporation", "전력·에너지", "원전·전력 · 조정 PEG 0.68 · CTA +0.25", "#f7fee7", "전력", "https://www.constellationenergy.com"),
 ("bloom-energy.html", "be", [CONTENT + "/be/body.html"], "Bloom Energy 기업분석", "BE", "Bloom Energy Corporation", "전력·에너지", "온사이트 전력 · 매출 +138% · CTA -0.50", "#fef2f2", "연료전지", "https://www.bloomenergy.com"),
 ("vistra.html", "vst", [CONTENT + "/vst/body.html"], "Vistra 기업분석", "VST", "Vistra Corp.", "전력·에너지", "전력 · PER 18배 · CTA -1.00", "#eef2ff", "전력", "https://vistracorp.com"),
 ("coinbase.html", "coin", [CONTENT + "/coin/body.html"], "Coinbase 기업분석", "COIN", "Coinbase Global, Inc.", "코인", "3Q 흑자는 평가이익 · CTA -1.00", "#f0f9ff", "가상자산 거래소", "https://www.coinbase.com"),
 ("circle.html", "crcl", [CONTENT + "/crcl/body.html"], "Circle 기업분석", "CRCL", "Circle Internet Group, Inc.", "코인", "스테이블코인 · 준비금 수익 감소 · CTA -1.00", "#f0fdf4", "스테이블코인", "https://www.circle.com"),
 ("robinhood.html", "hood", [CONTENT + "/hood/body.html"], "Robinhood 기업분석", "HOOD", "Robinhood Markets, Inc.", "금융", "온라인 증권 · 매출 기록 · CTA -0.50", "#ecfdf5", "온라인 증권", "https://robinhood.com"),
 ("jnj.html", "jnj", [CONTENT + "/jnj/body.html"], "Johnson & Johnson 기업분석", "JNJ", "Johnson & Johnson", "헬스케어", "제약·의료기기 · 조정 PEG 10.3 · CTA +1.00", "#fff7ed", "제약·의료기기", "https://www.jnj.com"),
 ("illumina.html", "ilmn", [CONTENT + "/ilmn/body.html"], "Illumina 기업분석", "ILMN", "Illumina, Inc.", "헬스케어", "시퀀싱 · 조정 PEG 2.19 · CTA +0.25", "#f5f3ff", "유전체 시퀀싱", "https://www.illumina.com"),
 ("abbvie.html", "abbv", [CONTENT + "/abbv/body.html"], "AbbVie 기업분석", "ABBV", "AbbVie Inc.", "헬스케어", "제약 · 조정 PEG 0.64 · CTA +1.00", "#f7fee7", "제약", "https://www.abbvie.com"),
 ("boeing.html", "ba", [CONTENT + "/ba/body.html"], "Boeing 기업분석", "BA", "The Boeing Company", "방산", "항공기 · 손실 축소 · CTA -1.00", "#fef2f2", "항공우주", "https://www.boeing.com"),
 ("ge.html", "ge", [CONTENT + "/ge/body.html"], "GE Aerospace 기업분석", "GE", "GE Aerospace", "방산", "조정 PER 43.1배 · 조정 PEG 1.68 · CTA +0.25", "#eff6ff", "항공 엔진", "https://www.geaerospace.com"),
 ("rtx.html", "rtx", [CONTENT + "/rtx/body.html"], "RTX 기업분석", "RTX", "RTX Corporation", "방산", "조정 PER 26.5배 · 조정 PEG 1.37 · CTA +0.50", "#f0f9ff", "항공우주·방산", "https://www.rtx.com"),
 ("lockheed.html", "lmt", [CONTENT + "/lmt/body.html"], "Lockheed Martin 기업분석", "LMT", "Lockheed Martin Corporation", "방산", "PER 21.2배 · PEG 산출 불가 · CTA +0.75", "#eef2ff", "방산", "https://www.lockheedmartin.com"),
 ("axon.html", "axon", [CONTENT + "/axon/body.html"], "Axon Enterprise 기업분석", "AXON", "Axon Enterprise, Inc.", "방산", "S&S +43% · 조정 PEG 5.0 · CTA -1.00", "#fefce8", "공공안전", "https://www.axon.com"),
 ("bofa.html", "bac", [CONTENT + "/bac/body.html"], "Bank of America 기업분석", "BAC", "Bank of America Corporation", "금융", "PEG 0.85 · 일회성 제외 0.60 · CTA -0.75", "#fef2f2", "은행", "https://www.bankofamerica.com"),
 ("wellsfargo.html", "wfc", [CONTENT + "/wfc/body.html"], "Wells Fargo 기업분석", "WFC", "Wells Fargo & Company", "금융", "PER 12.1배 · PEG 0.72 · CTA +0.50", "#fff7ed", "은행", "https://www.wellsfargo.com"),
 ("visa.html", "v", [CONTENT + "/v/body.html"], "Visa 기업분석", "V", "Visa Inc.", "금융", "조정 PER 32.1배 · 조정 PEG 2.03 · CTA +1.00", "#eff6ff", "결제", "https://www.visa.com"),
 ("mastercard.html", "ma", [CONTENT + "/ma/body.html"], "Mastercard 기업분석", "MA", "Mastercard Incorporated", "금융", "조정 PER 33.5배 · 조정 PEG 1.48 · CTA +1.00", "#fff1f2", "결제", "https://www.mastercard.com"),
 ("mpmaterials.html", "mp", [CONTENT + "/mp/body.html"], "MP Materials 기업분석", "MP", "MP Materials Corp.", "희토류", "매출 +176% · 일회성 포함 · CTA -1.00", "#f5f3ff", "희토류·자석", "https://mpmaterials.com"),
 ("lam.html", "lrcx", [CONTENT + "/lrcx/body.html"], "Lam Research 기업분석", "LRCX", "Lam Research Corporation", "반도체", "FQ 매출 +54% · PEG 0.70 · CTA -0.75", "#ecfdf5", "반도체 장비", "https://www.lamresearch.com"),
 ("appliedmaterials.html", "amat", [CONTENT + "/amat/body.html"], "Applied Materials 기업분석", "AMAT", "Applied Materials, Inc.", "반도체", "FQ4 매출 +53% · 조정 PEG 0.78 · CTA -0.75", "#f0fdf4", "반도체 장비", "https://www.appliedmaterials.com"),
 ("kla.html", "klac", [CONTENT + "/klac/body.html"], "KLA 기업분석", "KLAC", "KLA Corporation", "반도체", "FQ1 매출 +29% · 조정 PEG 2.09 · CTA -0.75", "#eef2ff", "반도체 장비", "https://www.kla.com"),
 ("teradyne.html", "ter", [CONTENT + "/ter/body.html"], "Teradyne 기업분석", "TER", "Teradyne, Inc.", "반도체", "3Q 매출 +70% · 두 분기 정체 · CTA -0.75", "#fdf4ff", "반도체 테스트", "https://www.teradyne.com"),
 ("hims.html", "hims", [CONTENT + "/hims/body.html"], "HIMS & HERS 기업분석", "HIMS", "Hims & Hers Health, Inc.", "헬스케어", "매출 +49% · 총이익률 57% · CTA -0.75", "#fdf2f8", "디지털 헬스", "https://www.forhims.com"),
 ("tempus.html", "tem", [CONTENT + "/tem/body.html"], "Tempus AI 기업분석", "TEM", "Tempus AI, Inc.", "헬스케어", "매출 +23% · 조정 EBITDA 흑자 · CTA +0.75", "#f0fdfa", "AI 정밀의료", "https://www.tempus.com"),
 ("novonordisk.html", "nvo", [CONTENT + "/nvo/body.html"], "Novo Nordisk 기업분석", "NVO", "Novo Nordisk A/S", "헬스케어", "알약 54억 DKK · 조정 영업이익 +27% · CTA -0.75", "#eff6ff", "비만·당뇨 제약", "https://www.novonordisk.com"),
 ("crispr.html", "crsp", [CONTENT + "/crsp/body.html"], "CRISPR Therapeutics 기업분석", "CRSP", "CRISPR Therapeutics AG", "헬스케어", "카스제비 $0.99억 · 런웨이 약 6년 · CTA -1.00", "#fef2f2", "유전자 편집", "https://www.crisprtx.com"),
 ("dwave.html", "qbts", [CONTENT + "/qbts/body.html"], "D-Wave Quantum 기업분석", "QBTS", "D-Wave Quantum Inc.", "양자", "수주 +611% · 런웨이 약 3.5년 · CTA -1.00", "#f5f3ff", "양자 어닐링", "https://www.dwavequantum.com"),
 ("rigetti.html", "rgti", [CONTENT + "/rgti/body.html"], "Rigetti Computing 기업분석", "RGTI", "Rigetti Computing, Inc.", "양자", "9개월 매출 +110% · 3Q -28% · CTA -1.00", "#faf5ff", "초전도 양자컴퓨터", "https://www.rigetti.com"),
 ("datadog.html", "ddog", [CONTENT + "/ddog/body.html"], "Datadog 기업분석", "DDOG", "Datadog, Inc.", "소프트웨어", "매출 +35% · PEG 1.82 · CTA -0.75", "#faf5ff", "클라우드 관측", "https://www.datadoghq.com"),
 ("pepsico.html", "pep", [CONTENT + "/pep/body.html"], "PepsiCo 기업분석", "PEP", "PepsiCo, Inc.", "소비재", "PEG 0.35(조정 약 2.4) · CTA +0.25", "#fff7ed", "음료·스낵", "https://www.pepsico.com"),
 ("lumentum.html", "lite", [CONTENT + "/lite/body.html"], "Lumentum 기업분석", "LITE", "Lumentum Holdings Inc.", "광통신", "FQ1 매출 +137% · 조정 PEG 약 0.17(기저효과) · CTA -0.50", "#f0f9ff", "광통신 부품 · AI 데이터센터", "https://www.lumentum.com"),
 ("arista.html", "anet", [CONTENT + "/anet/body.html"], "Arista Networks 기업분석", "ANET", "Arista Networks, Inc.", "데이터센터", "3Q 매출 +58.5% · PEG 1.33 · CTA +0.50", "#eef2ff", "데이터센터 네트워킹", "https://www.arista.com"),
 ("paloalto.html", "panw", [CONTENT + "/panw/body.html"], "Palo Alto Networks 기업분석", "PANW", "Palo Alto Networks, Inc.", "사이버 보안", "NGS ARR +63% · 조정 PEG 약 5.7 · CTA 0.00", "#faf5ff", "사이버 보안 플랫폼", "https://www.paloaltonetworks.com"),
 ("nike.html", "nke", [CONTENT + "/nke/body.html"], "Nike 기업분석", "NKE", "NIKE, Inc.", "소비재", "FQ1 매출 -4% · PEG 2.61 · CTA -0.25", "#fff7ed", "스포츠 신발·의류", "https://www.nike.com"),
 ("ferrari.html", "race", [CONTENT + "/race/body.html"], "Ferrari 기업분석", "RACE", "Ferrari N.V.", "소비재", "3Q 매출 +7% · PEG 6.13 · CTA +0.50", "#fef2f2", "럭셔리 슈퍼카", "https://www.ferrari.com"),
 ("applovin.html", "app", [CONTENT + "/app/body.html"], "AppLovin 기업분석", "APP", "AppLovin Corporation", "소프트웨어", "3Q 매출 +55% · PEG 0.30 · CTA +0.25", "#f0fdf4", "AI 광고 플랫폼", "https://www.applovin.com"),
 ("arm.html", "arm", [CONTENT + "/arm/body.html"], "Arm Holdings 기업분석", "ARM", "Arm Holdings plc", "반도체", "FQ2 매출 +27% · PEG 18.99(조정 약 5.0) · CTA -0.50", "#eef2ff", "CPU 설계 IP", "https://www.arm.com"),
 ("netflix.html", "nflx", [CONTENT + "/nflx/body.html"], "Netflix 기업분석", "NFLX", "Netflix, Inc.", "빅테크", "3Q 매출 +12% · PEG 0.41(일회성 제외 약 0.96) · CTA -1.00", "#fef2f2", "스트리밍", "https://www.netflix.com"),
 ("cerebras.html", "cbrs", [CONTENT + "/cbrs/body.html"], "Cerebras 기업분석", "CBRS", "Cerebras Systems Inc.", "반도체", "3Q 코어 매출 +70% · PEG 산출 불가 · CTA -1.00", "#faf5ff", "AI 추론 인프라", "https://www.cerebras.ai"),
 ("astera-labs.html", "alab", [CONTENT + "/alab/body.html"], "Astera Labs 기업분석", "ALAB", "Astera Labs, Inc.", "반도체", "3Q 매출 +154% · PEG 0.73 · CTA -0.50", "#f0f9ff", "AI 연결 반도체", "https://www.asteralabs.com"),
 ("synopsys.html", "snps", [CONTENT + "/snps/body.html"], "Synopsys 기업분석", "SNPS", "Synopsys, Inc.", "소프트웨어", "FQ3 매출 +42% · 비GAAP 영업이익률 41.6% · CTA +0.50", "#eef2ff", "반도체 설계 소프트웨어", "https://www.synopsys.com"),
 ("verisign.html", "vrsn", [CONTENT + "/vrsn/body.html"], "VeriSign 기업분석", "VRSN", "VeriSign, Inc.", "소프트웨어", "영업이익률 67% · PEG 4.07 · CTA +1.00", "#f0f9ff", "도메인 레지스트리", "https://www.verisign.com"),
 ("credo.html", "crdo", [CONTENT + "/crdo/body.html"], "Credo Technology 기업분석", "CRDO", "Credo Technology Group Holding Ltd", "반도체", "FQ1 매출 +115% · PEG 0.16 · CTA -1.00", "#ecfdf5", "AI 연결 반도체", "https://www.credosemi.com"),
 ("onsemi.html", "on", [CONTENT + "/on/body.html"], "onsemi 기업분석", "ON", "ON Semiconductor Corporation", "반도체", "3Q AI 데이터센터 +175% · GAAP PEG 0.35(조정 약 2.5) · CTA -0.75", "#ecfdf5", "전력·센서 반도체", "https://www.onsemi.com"),
 ("analogdevices.html", "adi", [CONTENT + "/adi/body.html"], "Analog Devices 기업분석", "ADI", "Analog Devices, Inc.", "반도체", "FQ3 매출 +40% · PEG 0.42(조정 약 0.63) · CTA +0.50", "#eff6ff", "아날로그·혼합신호 반도체", "https://www.analog.com"),
 ("merck.html", "mrk", [CONTENT + "/mrk/body.html"], "Merck 기업분석", "MRK", "Merck & Co., Inc.", "헬스케어", "3Q 매출 +5% · PEG 산출 불가 · CTA +1.00", "#f0fdfa", "제약·백신", "https://www.merck.com"),
 ("moderna.html", "mrna", [CONTENT + "/mrna/body.html"], "Moderna 기업분석", "MRNA", "Moderna, Inc.", "헬스케어", "3Q 첫 흑자 · 적자로 PEG 산출 불가 · CTA +0.75", "#fff1f2", "mRNA 백신·치료제", "https://www.modernatx.com"),
 ("target.html", "tgt", [CONTENT + "/tgt/body.html"], "Target 기업분석", "TGT", "Target Corporation", "소비재", "2Q 비교매출 +3.8% · PEG 1.35(환급 제외 산출 불가) · CTA +0.75", "#fef2f2", "대형 할인점", "https://corporate.target.com"),
 ("humana.html", "hum", [CONTENT + "/hum/body.html"], "Humana 기업분석", "HUM", "Humana Inc.", "헬스케어", "3Q 매출 +26% · PEG 산출 불가 · CTA +1.00", "#f0fdfa", "메디케어 보험", "https://www.humana.com"),
 ("uber.html", "uber", [CONTENT + "/uber/body.html"], "Uber 기업분석", "UBER", "Uber Technologies, Inc.", "소비재", "3Q 예약액 +20% · GAAP PEG 산출 불가(비GAAP 추정 약 0.64) · CTA -1.00", "#f3f4f6", "승차·배달 플랫폼", "https://www.uber.com"),
 ("intuit.html", "intu", [CONTENT + "/intu/body.html"], "Intuit 기업분석", "INTU", "Intuit Inc.", "소프트웨어", "FY26 매출 +14% · PEG 1.01(비GAAP 약 0.70) · CTA 0.00", "#eff6ff", "세금·회계 소프트웨어", "https://www.intuit.com"),
]
def _price(tk):
    e = CTA.get(tk, {})
    if "close" not in e: return ("-", "", "")
    ch = e.get("chg", 0)
    return (fmt(e["close"], e.get("cur", "$")), f"{ch:+.2f}%", "up" if ch > 0 else ("down" if ch < 0 else ""))
# 시가총액(USD) 큰 순서로 정렬 — data/mcap.json은 매일 update_data.py가 갱신한다. 값이 없는 새 종목은 맨 뒤(등록 순서 유지).
try:
    _CAP = json.load(open(os.path.join(ROOT, "data", "mcap.json"), encoding="utf-8")).get("usd", {})
except (OSError, ValueError):
    _CAP = {}
REPORTS.sort(key=lambda r: -(_CAP.get(r[4]) or 0))

def _pbase(tk):
    """가격 기준일 표기 — 시세는 장 종료 후에만 갱신되므로 실시간으로 오해하지 않게 종가 날짜를 보여 준다."""
    d = CTA.get(tk, {}).get("date", "")
    return f"{int(d[5:7])}/{int(d[8:10])} 종가" if len(d) >= 10 else ""

PRICE = {r[4]: _price(r[4]) for r in REPORTS}
EXCH = {"TGT": "NYSE", "HUM": "NYSE", "UBER": "NYSE", "NOW": "NYSE", "CRM": "NYSE", "RDDT": "NYSE", "VRT": "NYSE", "COHR": "NYSE", "005930": "KRX", "000660": "KRX", "TSM": "NYSE", "ORCL": "NYSE", "DELL": "NYSE", "LLY": "NYSE", "JPM": "NYSE", "UNH": "NYSE", "KO": "NYSE", "IONQ": "NYSE", "IBM": "NYSE", "JOBY": "NYSE", "ACHR": "NYSE", "GEV": "NYSE", "BE": "NYSE", "VST": "NYSE", "CRCL": "NYSE", "JNJ": "NYSE", "ABBV": "NYSE", "BA": "NYSE", "UMAC": "AMEX", "GE": "NYSE", "RTX": "NYSE", "LMT": "NYSE", "BAC": "NYSE", "WFC": "NYSE", "V": "NYSE", "MA": "NYSE", "MP": "NYSE", "HIMS": "NYSE", "NVO": "NYSE", "ANET": "NYSE", "NKE": "NYSE", "RACE": "NYSE", "MRK": "NYSE"}

MONO = {"005930": "삼성", "000660": "SK"}
LOGO = {"TGT": "target", "HUM": "humana", "UBER": "uber", "INTU": "intuit", "ON": "on-semiconductor", "ADI": "analog-devices", "MRK": "merck-and-co", "MRNA": "moderna", "NVDA": "nvidia", "AAPL": "apple", "GOOGL": "alphabet", "MSFT": "microsoft", "AMZN": "amazon", "MU": "micron-technology", "MRVL": "marvell-tech",
        "005930": "samsung", "TSM": "taiwan-semiconductor", "AVGO": "broadcom", "AMD": "advanced-micro-devices", "INTC": "intel", "QCOM": "qualcomm",
        "ORCL": "oracle", "PLTR": "palantir", "META": "meta-platforms", "CRWV": "coreweave",
        "TSLA": "tesla", "SPCX": "spacex", "DELL": "dell", "SNDK": "sandisk", "CRWD": "crowdstrike", "NBIS": "nebius-group-nv",
        "LLY": "eli-lilly", "JPM": "jpmorgan-chase", "UNH": "unitedhealth", "KO": "coca-cola", "WMT": "walmart", "COST": "costco-wholesale", "IONQ": "ionq",
        "TXN": "texas-instruments", "ASTS": "ast-spacemobile", "RKLB": "rocket-lab", "NOW": "servicenow", "CRM": "salesforce", "RDDT": "reddit", "SMCI": "super-micro-computer",
        "IREN": "iren", "WDC": "western-digital", "VRT": "vertiv-holdings", "COHR": "coherent", "MSTR": "microstrategy", "IBM": "international-bus-mach", "UMAC": "unusual-machines", "JOBY": "joby-aviation", "ACHR": "archer-aviation", "ONDS": "ondas", "GEV": "ge-verona", "CEG": "constellation-energy", "BE": "bloom-energy", "VST": "vistra-energy", "COIN": "coinbase", "CRCL": "circle-internet-group-inc", "HOOD": "robinhood", "JNJ": "johnson-and-johnson", "ILMN": "illumina", "ABBV": "abbvie", "BA": "boeing", "GE": "ge-aerospace", "RTX": "raytheon", "LMT": "lockheed-martin", "AXON": "axon-enterprise", "BAC": "bank-of-america", "WFC": "wells-fargo", "V": "visa", "MA": "mastercard", "MP": "mp-materials", "LRCX": "lam-research", "AMAT": "applied-materials", "KLAC": "kla-tencor", "TER": "teradyne", "HIMS": "hims-and-hers-health", "TEM": "tempus-ai", "NVO": "novo-nordisk", "CRSP": "crispr-therapeutics-ag", "QBTS": "d-wave-quantum", "RGTI": "rigetti-computing-redeemable", "DDOG": "datadog", "SNPS": "synopsys", "VRSN": "verisign", "CRDO": "credo-technology-ltd", "PEP": "pepsico", "LITE": "lumentum-hldgs", "ANET": "arista-networks", "PANW": "palo-alto-networks", "NKE": "nike", "RACE": "ferrari", "APP": "applovin-cdr-cad-hedged", "ARM": "arm", "NFLX": "netflix", "CBRS": "cerebras-systems", "ALAB": "astera-labs"}  # 트레이딩뷰 공개 로고 (SK하이닉스는 없어 글자 배지 유지)
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
.ctaw .ivs{margin:6px 0}.ctaw .ivb{padding:5px 12px;font-size:13px}.ctaw .cap{margin-top:4px}.tvlink{display:inline-block;margin-top:8px;font-size:13.5px;font-weight:700;color:#2563eb;text-decoration:none}
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
.stock .p{margin-left:auto;text-align:right;font-weight:800;font-size:18px}.stock .p small{display:block;font-size:12.5px}.stock .p .pbase{font-size:11px;font-weight:500;color:var(--muted);margin-top:1px}
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
.bsw{display:flex;align-items:center;gap:10px;margin:2px 0 8px}.bsw input{flex:1;max-width:340px;font:inherit;font-size:13px;padding:7px 12px;border:1px solid var(--line);border-radius:3px;background:var(--card);color:var(--ink)}.bsw input:focus{outline:none;border-color:var(--gold)}#bsn{font-size:12px;color:var(--muted)}
.pills{flex-wrap:wrap;gap:5px;margin:4px 0 12px}.pill{padding:3px 10px;font-size:11.5px;white-space:nowrap}
@media(max-width:560px){.pills{flex-wrap:nowrap}.bsw input{max-width:none}}
.stabs{display:flex;gap:4px;margin:2px 0 12px;border-bottom:1px solid var(--line)}.stab{font:inherit;font-size:13.5px;font-weight:600;padding:8px 16px;border:0;background:transparent;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}.stab:before{content:"- ";opacity:.5}.stab.on{color:var(--ink);border-bottom-color:var(--ink)}
#pegboard td.rk,#pegboard th.rk{width:34px;text-align:center;color:var(--muted);font-size:12px}#pegboard td.rm{font-size:11.5px;color:var(--muted);line-height:1.4;min-width:150px}
@media(max-width:640px){#pegboard{overflow-x:auto;-webkit-overflow-scrolling:touch}#pegboard table{width:max-content;min-width:100%}#pegboard td.rm,#pegboard th:last-child{width:190px;min-width:190px;max-width:190px;white-space:normal}#pegboard th:nth-child(2),#pegboard td:nth-child(2){width:128px;min-width:128px;max-width:128px;white-space:normal;position:sticky;left:0;z-index:2;background:var(--card);box-shadow:1px 0 0 var(--line)}.stab{padding:8px 12px;font-size:13px}}
.vis{text-align:center;font-size:11px;color:var(--muted);opacity:.7;padding:18px 0 22px;letter-spacing:.02em}
.cnst{text-align:center;font-size:11.5px;color:var(--muted);margin:-2px 0 6px}.cnst .dn{display:inline-block;width:7px;height:7px;border-radius:50%;background:#dc2626;margin-right:6px}.cnst .live{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22c55e;margin-right:6px;animation:hmp 1.6s infinite}
"""
THEME_INIT = "<script>(function(){try{var t=localStorage.getItem('theme')}catch(e){}if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t)})()</script><script>(function(){var of=window.fetch,last=0,bad=0;function pad(n){return('0'+n).slice(-2)}function show(){var e=document.getElementById('cnst');if(!e)return;if(!last){e.innerHTML='<span class=\"dn\"></span>CNBC 시세 · 대기 중';return}var d=new Date(last),age=(Date.now()-last)/1000,ok=age<150;e.innerHTML='<span class=\"'+(ok?'live':'dn')+'\"></span>CNBC 시세 '+(ok?'1분마다 갱신':'갱신 지연')+' · 마지막 '+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds())}window.fetch=function(u){var q=String(u&&u.url||u),p=of.apply(this,arguments);if(q.indexOf('quote.cnbc.com')>-1)p.then(function(r){if(r&&r.ok){last=Date.now();show()}}).catch(function(){});return p};document.addEventListener('DOMContentLoaded',show);setInterval(show,5000)})();</script>"
THEME_JS = """<script>(function(){var R=document.documentElement;
function tv(sel){document.querySelectorAll(sel||'.tvw').forEach(function(c){var cfg=JSON.parse(c.dataset.cfg);var dk=R.getAttribute('data-theme')==='dark'?'dark':'light';if('colorTheme' in cfg)cfg.colorTheme=dk;else cfg.theme=dk;
c.innerHTML='<div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>';var s=document.createElement('script');s.type='text/javascript';s.src=c.dataset.src;s.async=true;s.innerHTML=JSON.stringify(cfg);c.appendChild(s);});}
function setIv(card,v,re){var c=card.querySelector('.futw');if(!c)return;var g=JSON.parse(c.dataset.cfg);g.interval=v;c.dataset.cfg=JSON.stringify(g);
card.querySelectorAll('.ivb').forEach(function(x){x.classList.toggle('on',x.dataset.iv===v)});try{localStorage.setItem('futIv_'+card.dataset.k,v)}catch(e){}if(re)tv_one(c);}
function tv_one(c){c.id=c.id||('f'+Math.random().toString(36).slice(2));var m=c.id;c.dataset.one='1';tv('#'+m);c.removeAttribute('data-one');}
document.querySelectorAll('.fut').forEach(function(card){var iv='60';try{iv=localStorage.getItem('futIv_'+card.dataset.k)||'60'}catch(e){}
card.querySelectorAll('.ivb').forEach(function(x){x.addEventListener('click',function(){setIv(card,x.dataset.iv,true)})});setIv(card,iv,false);});
document.querySelectorAll('.ctaw').forEach(function(w){var c=w.querySelector('.ctw');w.querySelectorAll('.cvb').forEach(function(x){x.addEventListener('click',function(){c.dataset.cfg=x.dataset.k==='W'?c.dataset.cw:c.dataset.cd;w.querySelectorAll('.cvb').forEach(function(y){y.classList.toggle('on',y===x)});c.id=c.id||('c'+Math.random().toString(36).slice(2));tv('#'+c.id);})})});
tv();var b=document.querySelector('.thm');if(b)b.addEventListener('click',function(){var t=R.getAttribute('data-theme')==='dark'?'light':'dark';R.setAttribute('data-theme',t);try{localStorage.setItem('theme',t)}catch(e){}tv();});})();</script>"""
FONT = '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet">'


# --------------- live widgets (TradingView 공식 위젯: 방문자 브라우저가 직접 시세를 받음) ---------------
def tv_symbol(tk):
    return f'{EXCH.get(tk, "NASDAQ")}:{tk}'

KX_NAME = {"005930": "삼성전자", "000660": "SK하이닉스"}
KX_CSS = '.kxc{background:#14171c;color:#e8eaed;border-radius:20px;padding:22px 20px 14px;margin:6px 0 10px;font-family:inherit}\n.kxc .tk{font-size:13px;color:#8b929c;font-weight:600}.kxc .kd{font-size:13px;color:#8b929c;margin-top:10px;height:18px}.kxc .kp{font-size:34px;font-weight:800;letter-spacing:-.5px;margin-top:2px;color:#fff}\n.kxc .kc{font-size:14px;font-weight:600;margin-top:2px;height:20px}.kxc .up{color:#ff5a5f}.kxc .dn{color:#4c8dff}.kxc .kch{margin-top:12px}\n.kxc .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.kxc .chip{border:0;border-radius:999px;padding:6px 11px;font:600 12px inherit;font-family:inherit;background:#1f242b;color:#8b929c;display:flex;align-items:center;gap:6px;cursor:pointer}\n.kxc .chip i{width:8px;height:8px;border-radius:50%;display:inline-block}.kxc .chip.on{background:#262c35;color:#e8eaed}\n.kxc .seg{display:flex;background:#1b1f25;border-radius:12px;padding:3px;margin-top:12px}.kxc .seg button{flex:1;border:0;background:none;color:#8b929c;font-weight:600;font-size:13px;font-family:inherit;padding:8px;border-radius:9px;cursor:pointer}.kxc .seg button.on{background:#2a3039;color:#fff}\n.kxc .note{font-size:11.5px;color:#5f6670;margin-top:10px}'
KX_JS = '\nconst MA_DEF=[[5,\'#ef4444\',\'5일\'],[20,\'#facc15\',\'20일\'],[50,\'#22c55e\',\'50일\'],[100,\'#3b82f6\',\'100일\'],[200,\'#a855f7\',\'200일\']];\nconst WK=[\'일\',\'월\',\'화\',\'수\',\'목\',\'금\',\'토\'];\nfunction sma(a,n){return a.map((_,i)=>i<n-1?null:a.slice(i-n+1,i+1).reduce((s,x)=>s+x,0)/n)}\nfunction fmtDate(s){const d=new Date(s+\'T00:00:00\');return `${d.getFullYear()}. ${String(d.getMonth()+1).padStart(2,\'0\')}. ${String(d.getDate()).padStart(2,\'0\')} (${WK[d.getDay()]})`}\nfunction won(v){return Math.round(v).toLocaleString(\'ko-KR\')}\nfunction chart(opt){\n  const RAW=opt.raw, MAS=Object.fromEntries(MA_DEF.map(([n])=>[n,sma(RAW.c,n)]));\n  const host=opt.host; let on=new Set(opt.ma), span=opt.span;\n  const svgNS=\'http://www.w3.org/2000/svg\';\n  function draw(){\n    const W=host.clientWidth, H=opt.h, P=opt.pad;\n    const n=RAW.c.length, a=Math.max(0,n-span), C=RAW.c.slice(a), D=RAW.d.slice(a);\n    const lines=[...on].map(k=>[k,MA_DEF.find(m=>m[0]==k)[1],MAS[k].slice(a)]);\n    let pool=C.slice(); lines.forEach(l=>l[2].forEach(v=>v!=null&&pool.push(v)));\n    let mn=Math.min(...pool), mx=Math.max(...pool), r=mx-mn; mn-=r*.06; mx+=r*.06; r=mx-mn;\n    const X=i=>P.l+i*(W-P.l-P.r)/(C.length-1), Y=v=>P.t+(mx-v)/r*(H-P.t-P.b);\n    const path=A=>{let s=\'\',m=false;A.forEach((v,i)=>{if(v==null)return;s+=(m?\'L\':\'M\')+X(i).toFixed(1)+\',\'+Y(v).toFixed(1);m=true});return s};\n    const up=C[C.length-1]>=C[0], col=up?opt.up:opt.down;\n    let g=\'\';\n    const st=(()=>{const raw=r/4,p=Math.pow(10,Math.floor(Math.log10(raw)));return [1,2,2.5,5,10].map(m=>m*p).find(x=>x>=raw)})();for(let v=Math.ceil(mn/st)*st;v<=mx;v+=st){g+=`<line x1="${P.l}" x2="${W-P.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="${opt.grid}" stroke-width="1" ${opt.dash?\'stroke-dasharray="3 4"\':\'\'}/>`;if(opt.axis)g+=`<text x="${W-P.r+6}" y="${Y(v)+4}" fill="${opt.axisc}" font-size="11">${won(v)}</text>`}\n    let pm=null,mk=0;const every=(W<520&&C.length>100)?2:1;D.forEach((s,i)=>{const m=s.slice(5,7);if(pm&&m!=pm&&opt.months&&(mk++%every===0))g+=`<text x="${X(i)}" y="${H-6}" fill="${opt.axisc}" font-size="11" text-anchor="middle">${+m}월</text>`;pm=m});\n    const id=\'g\'+Math.random().toString(36).slice(2);\n    g+=`<defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${col}" stop-opacity="${opt.area}"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>`;\n    g+=`<path d="${path(C)}L${X(C.length-1)},${H-P.b}L${X(0)},${H-P.b}Z" fill="url(#${id})"/>`;\n    lines.forEach(([k,c,L])=>g+=`<path d="${path(L)}" fill="none" stroke="${c}" stroke-width="${opt.maw}" opacity="${opt.mao}"/>`);\n    g+=`<path d="${path(C)}" fill="none" stroke="${col}" stroke-width="${opt.lw}" stroke-linejoin="round"/>`;\n    g+=`<g class="hv" style="display:none"><line class="vx" y1="${P.t}" y2="${H-P.b}" stroke="${opt.cross}" stroke-width="1" ${opt.dash?\'stroke-dasharray="3 3"\':\'\'}/><circle class="dt" r="5" fill="${col}" stroke="${opt.ring}" stroke-width="2"/></g>`;\n    host.innerHTML=`<svg width="${W}" height="${H}" style="display:block;touch-action:pan-y;cursor:crosshair">${g}</svg>`;\n    const svg=host.querySelector(\'svg\'), hv=svg.querySelector(\'.hv\'), vx=svg.querySelector(\'.vx\'), dt=svg.querySelector(\'.dt\');\n    const idx=x=>Math.max(0,Math.min(C.length-1,Math.round((x-P.l)/(W-P.l-P.r)*(C.length-1))));\n    function show(ev){const b=svg.getBoundingClientRect();const i=idx(ev.clientX-b.left);const x=X(i),yv=Y(C[i]);\n      hv.style.display=\'\';vx.setAttribute(\'x1\',x);vx.setAttribute(\'x2\',x);dt.setAttribute(\'cx\',x);dt.setAttribute(\'cy\',yv);\n      const prev=i>0?C[i-1]:C[i];opt.onHover({date:D[i],price:C[i],chg:C[i]-prev,pct:(C[i]/prev-1)*100,x,y:yv,W,H,ma:lines.map(([k,c,L])=>[k,c,L[i]])});}\n    function hide(){hv.style.display=\'none\';opt.onHover(null)}\n    svg.addEventListener(\'pointermove\',show);svg.addEventListener(\'pointerdown\',show);\n    svg.addEventListener(\'pointerleave\',hide);svg.addEventListener(\'pointercancel\',hide);\n    svg.addEventListener(\'touchmove\',e=>{if(e.cancelable)e.preventDefault()},{passive:false});\n    opt.onHover(null);\n  }\n  let lw=0;new ResizeObserver(()=>{if(host.clientWidth!==lw){lw=host.clientWidth;draw()}}).observe(host);\n  return {setSpan(s){span=s;draw()},toggle(k){on.has(k)?on.delete(k):on.add(k);draw();return on.has(k)},last(){const n=RAW.c.length;return {date:RAW.d[n-1],price:RAW.c[n-1],chg:RAW.c[n-1]-RAW.c[n-2],pct:(RAW.c[n-1]/RAW.c[n-2]-1)*100}}};\n}\n\ndocument.querySelectorAll(\'.kxc\').forEach(function(root){\n const raw=JSON.parse(root.dataset.raw),q=s=>root.querySelector(s);let ch;\n const sh=h=>{const v=h||ch.last();q(\'.kd\').textContent=h?fmtDate(v.date):fmtDate(v.date)+\' 종가\';q(\'.kp\').textContent=won(v.price)+\'원\';const s=v.chg>=0;const c=q(\'.kc\');c.className=\'kc \'+(s?\'up\':\'dn\');c.textContent=(s?\'▲ \':\'▼ \')+won(Math.abs(v.chg))+\'원 (\'+(s?\'+\':\'\')+v.pct.toFixed(2)+\'%)\'};\n ch=chart({raw:raw,host:q(\'.kch\'),h:300,span:190,ma:[20,50,200],pad:{l:4,r:4,t:10,b:22},up:\'#ff5a5f\',down:\'#4c8dff\',grid:\'#1f242b\',dash:false,axis:false,axisc:\'#5f6670\',months:true,area:.22,lw:2.2,maw:1.4,mao:.9,cross:\'#5f6670\',ring:\'#14171c\',onHover:sh});\n MA_DEF.forEach(([k,c,l])=>{const b=document.createElement(\'button\');b.type=\'button\';b.className=\'chip\'+([20,50,200].includes(k)?\' on\':\'\');b.innerHTML=`<i style="background:${c}"></i>${l}선`;b.onclick=()=>b.classList.toggle(\'on\',ch.toggle(k));q(\'.chips\').appendChild(b)});\n root.querySelectorAll(\'.seg button\').forEach(b=>b.onclick=()=>{root.querySelectorAll(\'.seg button\').forEach(x=>x.classList.toggle(\'on\',x===b));ch.setSpan(+b.dataset.s)});\n});'

def krx_chart(tk):
    """한국 종목: 트레이딩뷰 위젯이 KRX를 막아 매일 받은 일봉 종가로 직접 그린다(시안 A, 마우스·터치로 거래일 종가 표시)."""
    e = CTA.get(tk, {}); px = e.get("px")
    if not px: return ""
    y = int(e["date"][:4]); pm = int(px["d"][-1][:2]); ds = []
    for md in reversed(px["d"]):
        m = int(md[:2])
        if m > pm: y -= 1
        pm = m; ds.append(f"{y}-{md[:2]}-{md[2:]}")
    raw = json.dumps({"d": list(reversed(ds)), "c": px["c"]}, separators=(",", ":"))
    return (f'<style>{KX_CSS}</style><div class="kxc" data-raw=\'{raw}\'><div class="tk">{KX_NAME.get(tk, tk)} · {tk} · KRX</div>'
            f'<div class="kd"></div><div class="kp"></div><div class="kc"></div><div class="kch"></div>'
            f'<div class="seg"><button type="button" data-s="21">1개월</button><button type="button" data-s="63">3개월</button><button type="button" data-s="126">6개월</button><button type="button" data-s="190" class="on">9개월</button></div>'
            f'<div class="chips"></div><div class="note">차트 위에 마우스를 올리거나 손가락으로 누른 채 움직이면 그날 종가가 위에 표시됩니다 · 일봉 종가 · 매일 자동 갱신</div></div>'
            f'<script>(function(){{{KX_JS}}})();</script>')

def tv_chart(tk, h=440, folder=""):
    if EXCH.get(tk) == "KRX":  # 한국 종목은 트레이딩뷰 위젯에서 라이선스상 표시되지 않음
        return krx_chart(tk)
    cfg = {"autosize": True, "symbol": tv_symbol(tk), "interval": "D", "timezone": "Asia/Seoul", "theme": "light", "style": "1",
           "locale": "kr", "allow_symbol_change": False, "hide_side_toolbar": True, "calendar": False, "support_host": "https://www.tradingview.com",
           "studies": [{"id": "MASimple@tv-basicstudies", "inputs": {"length": 20}}, {"id": "MASimple@tv-basicstudies", "inputs": {"length": 50}},
                       {"id": "MASimple@tv-basicstudies", "inputs": {"length": 200}}]}
    return (f'<div class="tvbox" style="height:{h}px"><div class="tradingview-widget-container tvw" style="height:100%;width:100%" '
            f'data-src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" data-cfg=\'{json.dumps(cfg)}\'></div></div>')

def cta_widget(tk, folder=""):
    if EXCH.get(tk) == "KRX":
        return tv_chart(tk, folder=folder)
    base = {"autosize": True, "symbol": tv_symbol(tk), "timezone": "Asia/Seoul", "theme": "light", "style": "1", "locale": "kr",
            "allow_symbol_change": False, "hide_side_toolbar": True, "calendar": False, "hide_top_toolbar": True, "support_host": "https://www.tradingview.com"}
    # 무료 임베드 위젯은 지표 색 지정을 무시한다. 선마다 다른 색은 MA 리본(STD;MA%Ribbon)의 고정 슬롯 색으로 낸다.
    # 리본 입력: MA마다 4개(표시 in_4k, 종류 in_4k+1, 소스 in_4k+2, 길이 in_4k+3). 슬롯 색: 1 노랑, 2 주황, 3 진주황, 4 빨강.
    def rib(slots):
        inp = {}
        for k in range(4):
            n = slots.get(k + 1)
            inp[f"in_{4*k}"] = bool(n); inp[f"in_{4*k+1}"] = "SMA"; inp[f"in_{4*k+3}"] = n or 10
        return {"id": "STD;MA%Ribbon", "inputs": inp}
    bb = {"id": "BB@tv-basicstudies", "inputs": {"length": 20, "stdDev": 2}}
    cd = dict(base, interval="D", studies=[rib({4: 5}), rib({1: 20, 2: 50, 3: 100}), {"id": "MASimple@tv-basicstudies", "inputs": {"length": 200}}, bb])
    cw = dict(base, interval="W", studies=[rib({4: 10}), rib({1: 20, 2: 40}), bb])
    j = lambda c: json.dumps(c).replace("'", "&#39;")
    return (f'<div class="ctaw"><div class="ivs"><button class="ivb on cvb" data-k="D">일봉 · SMA 5·20·50·100·200 + 볼린저</button>'
            f'<button class="ivb cvb" data-k="W">주봉 · 10·20·40주선 + 볼린저</button></div>'
            f'<div class="tvbox" style="height:460px"><div class="tradingview-widget-container tvw ctw" style="height:100%;width:100%" '
            f'data-src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" data-cfg=\'{j(cd)}\' data-cd=\'{j(cd)}\' data-cw=\'{j(cw)}\'></div></div>'
            f'<div class="cap">트레이딩뷰 실시간 차트 · 일봉: 5일 빨강·20일 노랑·50일 주황·100일 진주황·200일 파랑 · 주봉: 10주 빨강·20주 노랑·40주 주황 · 볼린저(20, 2) 기본색 · 범례의 눈 아이콘으로 지표를 껐다 켤 수 있습니다</div></div>')

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

try:
    _TG = json.load(open(os.path.join(ROOT, "data", "targets.json"), encoding="utf-8")).get("t", {})
except (OSError, ValueError):
    _TG = {}
_REC = {"strong_buy": "강력 매수", "buy": "매수", "hold": "중립", "underperform": "비중 축소", "sell": "매도"}
def target_box(tk):
    t = _TG.get(tk); e = CTA.get(tk, {})
    if not t or not e.get("close"): return ""
    cur = e.get("cur", "$"); F = lambda v: fmt(v, cur)
    up = (t["mean"] / e["close"] - 1) * 100
    cells = [("평균 목표가", F(t["mean"]), f'<span class="{"up" if up > 0 else "down"}">현재가 대비 {up:+.1f}%</span>')]
    for k, lb in (("high", "최고"), ("median", "중앙값"), ("low", "최저")):
        if t.get(k): cells.append((lb, F(t[k]), f'{(t[k] / e["close"] - 1) * 100:+.1f}%'))
    meta = " · ".join(x for x in ((f'애널리스트 {t["n"]}명' if t.get("n") else ""), (f'컨센서스 {_REC.get(t["rec"], t["rec"])}' if t.get("rec") else ""), f'{t.get("d", "")} 기준') if x)
    det = ""
    if t.get("recent"):
        _AC = {"raises": ("상향", "up"), "lowers": ("하향", "down"), "maintains": ("유지", ""), "announces": ("신규", ""), "initiates": ("신규", ""), "reiterates": ("유지", ""), "unchanged": ("유지", "")}
        rows = ""
        for x in t["recent"]:
            lb, cl = _AC.get((x.get("ac") or "").lower(), ("", ""))
            if not lb and x.get("pp"): lb, cl = (("상향", "up") if x["pt"] > x["pp"] else ("하향", "down") if x["pt"] < x["pp"] else ("유지", ""))
            pr = f'{F(x["pp"])} → <b>{F(x["pt"])}</b>' if x.get("pp") and x["pp"] != x["pt"] else f'<b>{F(x["pt"])}</b>'
            rt = f'{x["fr"]} → {x["to"]}' if x.get("fr") and x.get("to") and x["fr"] != x["to"] else (x.get("to") or "-")
            rows += f'<tr><td>{x["d"]}</td><td>{x["f"]}</td><td>{rt}</td><td>{pr}</td><td><span class="{cl}">{lb or "-"}</span></td><td>{(x["pt"] / e["close"] - 1) * 100:+.1f}%</td></tr>'
        det = ('<details class="tgd"><summary>세부정보 보기 · 최근 기관별 목표가</summary><div class="tw"><table><tr><th>날짜</th><th>기관</th><th>투자의견</th><th>목표가</th><th>변경</th><th>현재가 대비</th></tr>' + rows + '</table></div></details>')
    return ('<div class="tgbox"><div class="hd"><b>애널리스트 목표가</b><span>' + meta + '</span></div><div class="cs">'
            + "".join(f'<div><small>{a}</small><b>{b}</b><em>{c}</em></div>' for a, b, c in cells)
            + '</div>' + det + '<div class="nt">출처: Yahoo Finance 컨센서스 · 상승여력은 최근 종가 기준이며 매일 자동 갱신됩니다.</div></div>')
TG_CSS = """
.tgbox{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:12px 16px;margin:0 0 16px}
.tgbox .hd{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:baseline;margin-bottom:8px}.tgbox .hd b{font-size:14px}.tgbox .hd span{font-size:12px;color:var(--muted)}
.tgbox .cs{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.tgbox .cs div{display:flex;flex-direction:column;gap:2px}
.tgbox .cs small{font-size:11.5px;color:var(--muted)}.tgbox .cs b{font-size:18px;font-weight:800}.tgbox .cs em{font-style:normal;font-size:12px;color:var(--muted)}
.tgbox .cs em .up{color:var(--up);font-weight:700}.tgbox .cs em .down{color:var(--down);font-weight:700}
.tgd{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}.tgd summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--blue)}
.tgd .tw{overflow-x:auto;margin-top:8px}.tgd table{border-collapse:collapse;width:100%;font-size:12.5px;white-space:nowrap}.tgd th{text-align:left;color:var(--muted);font-weight:600;padding:4px 8px;border-bottom:1px solid var(--line)}.tgd td{padding:5px 8px;border-bottom:1px solid var(--line)}.tgd .up{color:var(--up);font-weight:700}.tgd .down{color:var(--down);font-weight:700}
.tgbox .nt{font-size:11.5px;color:var(--muted);margin-top:8px}
@media(max-width:640px){.tgbox .cs{grid-template-columns:repeat(2,1fr)}}
"""
CSS += TG_CSS

try:
    _INS = json.load(open(os.path.join(ROOT, "data", "insiders.json"), encoding="utf-8")).get("t", {})
except (OSError, ValueError):
    _INS = {}
try:
    _CG = json.load(open(os.path.join(ROOT, "data", "congress.json"), encoding="utf-8")).get("t", {})
except (OSError, ValueError):
    _CG = {}
try:
    _F13 = json.load(open(os.path.join(ROOT, "data", "funds13f.json"), encoding="utf-8")).get("f", {})
except (OSError, ValueError):
    _F13 = {}
_IK = {"buy": ("매수", "up"), "sell": ("매도", "down"), "grant": ("주식 보상", "mu"), "exercise": ("옵션 행사/전환", "mu"), "gift": ("증여", "mu"), "other": ("기타", "mu")}
def _usd(v):
    if v is None: return "-"
    a = abs(v); return ("$%.2fB" % (v / 1e9)) if a >= 1e9 else ("$%.1fM" % (v / 1e6)) if a >= 1e6 else ("$%.0fK" % (v / 1e3)) if a >= 1e3 else "$%.0f" % v
def _sh(n): return f"{n:,.0f}"
def smart_box(tk):
    import datetime as _d
    out = ""
    kr = tk.isdigit()
    def none(ic, title, why):
        return f'<div class="smd smn"><b>{ic} {title}</b> <span>{why}</span></div>'
    rows = _INS.get(tk) or []
    if rows:
        cut = (_d.date.today() - _d.timedelta(days=183)).isoformat()
        rec = [x for x in rows if x["d"] >= cut]
        nb = [x for x in rec if x["k"] == "buy"]; ns = [x for x in rec if x["k"] == "sell"]
        vb = sum(x["v"] or 0 for x in nb); vs = sum(x["v"] or 0 for x in ns)
        summ = f'최근 6개월 공개 시장 매수 {len(nb)}건 {_usd(vb)} · 매도 {len(ns)}건 {_usd(vs)}' if rec else "최근 6개월 신고 내역 없음"
        tr = ""
        for x in rows[:15]:
            lb, cl = _IK.get(x["k"], _IK["other"])
            who = x["n"] + (f' <small>{x["p"]}</small>' if x.get("p") else "")
            link = f'<a href="{x["u"]}" target="_blank" rel="noopener">원문</a>' if x.get("u", "").startswith("http") else ""
            tr += f'<tr><td>{x["d"]}</td><td>{who}</td><td><span class="{cl}">{lb}</span></td><td class="r">{_sh(x["sh"]) if x.get("sh") else "-"}</td><td class="r">{("$%.2f" % x["px"]) if x.get("px") else "-"}</td><td class="r">{_usd(x["v"]) if x.get("v") else "-"}</td><td>{link}</td></tr>'
        out += (f'<details class="smd"><summary>🧑‍💼 내부자 거래 (Form 4) <span>{summ}</span></summary><div class="tw"><table><tr><th>거래일</th><th>내부자</th><th>구분</th><th class="r">수량</th><th class="r">가격</th><th class="r">금액</th><th></th></tr>{tr}</table></div>'
                '<div class="nt">출처: Yahoo Finance(SEC Form 4). 주식 보상·옵션 행사는 시장 매매가 아니므로 매수/매도와 구분해 표시합니다. 가격은 신고 문구에서 추출해 일부는 비어 있을 수 있습니다.</div></details>')
    elif True:
        out += none("🧑‍💼", "내부자 거래 (Form 4)", "수집 대상 아님 (한국 상장 종목)" if kr else "거래 없음")
    fr = []
    for cik, f in _F13.items():
        c, p = f["rows"].get(tk), f["prows"].get(tk)
        if not c and not p: continue
        sh, psh = (c or {}).get("sh", 0), (p or {}).get("sh", 0)
        if psh == 0 and sh > 0: ac, cl = "신규 매수", "up"
        elif sh == 0: ac, cl = "전량 매도", "down"
        elif sh > psh: ac, cl = f"확대 +{(sh / psh - 1) * 100:.0f}%", "up"
        elif sh < psh: ac, cl = f"축소 {(sh / psh - 1) * 100:.0f}%", "down"
        else: ac, cl = "변동 없음", "mu"
        w = c["v"] / f["total"] * 100 if c and f.get("total") else None
        pw = p["v"] / f["ptotal"] * 100 if p and f.get("ptotal") else None
        est = (c or p).get("est") if sh != psh else None
        fr.append((c["v"] if c else 0, f'<tr><td>{f["name"]}</td><td>{f["period"][:4]} Q{(int(f["period"][5:7]) + 2) // 3}</td><td><span class="{cl}">{ac}</span></td><td class="r">{_sh(psh)} → <b>{_sh(sh)}</b></td><td class="r">{(f"{pw:.2f}% → " if pw is not None else "")}<b>{(f"{w:.2f}%" if w is not None else "0%")}</b></td><td class="r">{_usd(c["v"]) if c else "-"}</td><td class="r">{(("추정 $%.2f" % est) if est else "-")}</td></tr>'))
    if fr:
        fr.sort(key=lambda x: -x[0]); per = max(f["period"] for f in _F13.values())
        out += (f'<details class="smd"><summary>🏦 네임드 펀드 13F 매매 <span>{len(fr)}개 펀드 · 펀드별 가장 최근 공시 분기 기준</span></summary><div class="tw"><table><tr><th>펀드</th><th>기준</th><th>행동</th><th class="r">보유 주식</th><th class="r">포트폴리오 비중</th><th class="r">평가금액</th><th class="r">추정 평단(매도가)</th></tr>' + "".join(x[1] for x in fr) + '</table></div>'
                '<div class="nt">13F는 분기 말 기준 보유 내역이라 정확한 매매일·체결가는 알 수 없습니다. 비중은 해당 펀드의 13F 보고 포트폴리오(미국 상장 롱 포지션) 대비이며 전체 운용자산(시드)과는 다릅니다. 추정 평단은 변동이 생긴 분기의 거래량가중 평균가로, 실제 체결가와 다를 수 있는 추정치입니다. 공시는 분기 종료 후 최대 45일 뒤에 나옵니다.</div></details>')
    else:
        out += none("🏦", "네임드 펀드 13F 매매", "수집 대상 아님 (한국 상장 종목)" if kr else f"거래 없음 (네임드 {len(_F13)}개 펀드 보유 내역 없음)")
    cg = _CG.get(tk) or []
    if not cg:
        out += none("🏛", "의원 주식 거래 (STOCK Act)", "수집 대상 아님 (한국 상장 종목)" if kr else "거래 없음 (추적 중인 하원의원 기준)")
    if cg:
        _T = {"P": ("매수", "up"), "S": ("매도", "down"), "SP": ("일부 매도", "down"), "E": ("교환", "mu")}
        tr = ""
        for x in cg[:12]:
            lb, cl = _T.get(x["ty"], ("-", "mu"))
            tr += (f'<tr><td>{x["d"]}</td><td>{x["m"]}</td><td><span class="{cl}">{lb}</span></td><td>{x["o"]}</td><td class="r">{x["amt"]}</td><td>{x["n"]}</td>'
                   f'<td><a href="https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{x["yr"]}/{x["doc"]}.pdf" target="_blank" rel="noopener">원문</a></td></tr>')
        names = sorted({x["m"] for x in cg})
        out += (f'<details class="smd"><summary>🏛 의원 주식 거래 (STOCK Act) <span>{len(cg)}건 · {", ".join(names[:3])}{" 외" if len(names) > 3 else ""}</span></summary><div class="tw"><table><tr><th>거래일</th><th>의원</th><th>구분</th><th>명의</th><th class="r">금액 구간</th><th>공시 통지일</th><th></th></tr>{tr}</table></div>'
                '<div class="nt">출처: 미 하원 사무처(House Clerk) 정기 거래 보고서. 이름이 알려진 하원의원 일부만 추적하며 상원의원은 포함하지 않습니다. 정확한 금액이 아니라 신고 구간으로만 공개되고, 거래 후 최대 45일 뒤에 공시되므로 실시간 정보가 아닙니다. 명의는 본인·배우자·자녀·공동입니다.</div></details>')
    return '<div class="tgbox"><div class="hd"><b>스마트 머니 동향</b><span>내부자 · 네임드 펀드 · 의원 매수·매도 기록</span></div>' + out + '</div>'
SM_CSS = """
.smd{border-top:1px solid var(--line);padding-top:8px;margin-top:8px}.smd summary{cursor:pointer;font-size:13.5px;font-weight:700}.smd summary span{font-weight:500;font-size:12px;color:var(--muted);margin-left:8px}
.smd .tw{overflow-x:auto;margin-top:8px}.smd table{border-collapse:collapse;width:100%;font-size:12.5px;white-space:nowrap}.smd th{text-align:left;color:var(--muted);font-weight:600;padding:4px 8px;border-bottom:1px solid var(--line)}.smd td{padding:5px 8px;border-bottom:1px solid var(--line)}
.smn{font-size:13.5px}.smn span{font-size:12px;color:var(--muted);margin-left:8px}.smd .r{text-align:right}.smd small{color:var(--muted)}.smd .up{color:var(--up);font-weight:700}.smd .down{color:var(--down);font-weight:700}.smd .mu{color:var(--muted)}.smd .nt{font-size:11.5px;color:var(--muted);margin-top:8px;white-space:normal}
"""
CSS += SM_CSS

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

def _peg_data(r):  # 각 보고서 본문의 동종업계 비교표(트레이딩뷰 11/6 환산)에서 자기 종목 행을 읽는다 → 보고서를 올리면 자동 반영
    tk = r[4]
    for src in r[2]:
        try: h = open(src, encoding="utf-8").read()
        except OSError: continue
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
            c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            if len(c) >= 6 and c[0] == tk:
                o = 1 if len(c) >= 7 else 0  # 구 양식(시가총액 열 포함)은 한 칸 밀려 있음
                if not re.search(r"배|적자|–", c[2 + o]): continue
                m = re.match(r"([0-9]+\.[0-9]+)", c[3 + o])
                return c[2 + o].split(" (")[0].replace("약 ", ""), (c[5 + o].split(" ")[0] if re.match(r"[+-]", c[5 + o]) else "-"), float(m.group(1)) if m else None, ("의미 제한" in c[3 + o])
    return None

# 일회성 비용·비교 기저 왜곡으로 트레이딩뷰 PEG가 없거나 낮게 나온 종목의 조정 EPS 기준 값. 모두 해당 기업 보고서 PEG 심층 표의 수치.
#  main: 조정 EPS 기준 PEG를 PEG 칸에 넣는다 / side: PEG 칸은 그대로 두고 비고에 일회성 비용 제외 PEG를 적는다 / none: 조정해도 산출 불가
ADJ_PEG = {
    "ON": {"mode": "side", "note": "트레이딩뷰 PEG 0.35는 1Q25 GAAP 순손실(저기저) 효과. 조정 EPS 기준 PEG 약 2.5"},
    "ADI": {"mode": "side", "note": "조정 EPS 기준 PEG 약 0.63"},
    "MRK": {"mode": "none", "note": "GAAP·조정 EPS 모두 감소(취득 IPR&D 비용)해 산출 불가"},
    "MRNA": {"mode": "none", "note": "TTM 순손실이라 산출 불가"},
    "TGT": {"mode": "side", "note": "트레이딩뷰 PEG 1.35는 관세 환급 $1.65가 포함된 EPS 기준. 환급 제외 TTM EPS가 전년보다 낮아 환급 제외 PEG는 산출 불가"},
    "KO": {"mode": "side", "note": "조정 EPS 기준 PEG 약 2.5(GAAP 기준 2.34)"},
    "HUM": {"mode": "none", "note": "GAAP·조정 EPS 모두 감소해 산출 불가"},
    "UBER": {"mode": "side", "note": "GAAP EPS 성장 -78%(2025년 세금 혜택 기저)로 산출 불가. 비GAAP EPS 기준 PEG 약 0.64(성장률 +35% 가정, 추정)"},
    "INTU": {"mode": "side", "note": "트레이딩뷰 PEG 1.01은 GAAP 기준. FY26 비GAAP EPS 기준 PEG 약 0.70"},
    "LITE": {"mode": "main", "peg": 0.17, "per": "50.4배", "gr": "+299%", "note": "조정 EPS 기준(내 계산, 직전 4분기 저기저로 기저효과 큼). GAAP은 FQ4'26 일회성 비현금 비용으로 산출 불가"},
    "PANW": {"mode": "main", "peg": 5.7, "per": "84.1배", "gr": "+14.7%", "note": "조정 EPS 기준 PEG(내 계산). GAAP은 인수 비용으로 EPS가 감소해 산출 불가"},
    "NFLX": {"mode": "gain", "peg": 0.96, "per": "21.1배", "gr": "+22%", "why": "WBD 위약금 $28억 세후 약 $0.53 제외, 세율·주식수는 내 가정"},
    "ARM": {"mode": "side", "note": "GAAP 기준 PEG 18.99. 조정 EPS 기준 PEG 약 5.0"},
    "NKE": {"mode": "side", "note": "FY27 EPS 감소 가이던스(조정 $1.15~1.35)로 앞으로의 PEG는 산출 불가"},
    "ANET": {"mode": "side", "note": "조정 EPS 기준 PEG 약 1.24"},
    "ALAB": {"mode": "side", "note": "조정 EPS 기준 PEG 약 0.65(기저효과 큼)"},
    "APP": {"mode": "side", "note": "GAAP EPS 직접 계산 PEG 약 0.35"},
    "RACE": {"mode": "side", "note": "US$ 환산 EPS 직접 계산 PEG 약 4.1"},
    "PEP": {"mode": "side", "note": "트레이딩뷰 PEG 0.35는 2025년 일회성 비용(저기저) 효과. 조정 EPS 기준 PEG 약 2.4"},
    "GE": {"mode": "main", "peg": 1.68, "per": "43.1배", "gr": "+25.6%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표). 트레이딩뷰는 PEG 미제공"},
    "RTX": {"mode": "main", "peg": 1.37, "per": "26.5배", "gr": "+19.3%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표)"},
    "LMT": {"mode": "none", "note": "TTM EPS 변동(4Q24·2Q25 저점)으로 기저 효과가 커 산출 불가(보고서 PEG 심층 표 참고)"},
    "AXON": {"mode": "main", "peg": 5.0, "per": "42.9배", "gr": "+8.6%", "note": "조정 EPS 기준 PEG. GAAP EPS는 감소해 트레이딩뷰 PEG 산출 불가"},
    "BAC": {"mode": "side", "note": "일회성 비용 제외(조정 EPS) PEG 약 0.60. GAAP 기준 약 0.85"},
    "V": {"mode": "main", "peg": 2.03, "per": "32.1배", "gr": "+15.8%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표). 트레이딩뷰는 PEG 미제공"},
    "MA": {"mode": "main", "peg": 1.48, "per": "33.5배", "gr": "+22.6%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표). 트레이딩뷰는 PEG 미제공"},
    "AMAT": {"mode": "main", "peg": 0.78, "per": "28.7배", "gr": "+36.9%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표). GAAP 기준 0.65"},
    "KLAC": {"mode": "main", "peg": 2.09, "per": "37.2배", "gr": "+17.8%", "note": "조정 EPS 기준 PEG. GAAP 성장률은 FQ2'25 낮은 GAAP EPS 기저로 부풀려져(GAAP 기준 1.49)"},
    "NVO": {"mode": "none", "note": "트레이딩뷰 PEG 0.65는 2026년 상반기 340B 환급 일회성으로 EPS가 부풀려져 판정에서 제외"},
    "TER": {"mode": "none", "note": "AI 수요로 EPS가 한 번에 3배 가까이 뛴 기저 효과(계산상 0.13)여서 판정에서 제외"},
    "MRVL": {"mode": "main", "peg": 0.64, "per": "약 32배", "gr": "+50%(가정)", "note": "조정 EPS 기준: 비GAAP 선행 EPS(FY27Q3 가이던스×4) 추정, 성장률 +50% 가정. 트레이딩뷰 PEG는 $1.9B 매각 이익 때문에 산출 불가"},
    "SNDK": {"mode": "main", "peg": 0.02, "per": "3.7배", "gr": "+199%(추정)", "note": "조정 EPS 기준: 비GAAP 2Q 가이던스 연환산 추정. 트레이딩뷰 PEG는 1년 전 적자 기저로 산출 불가"},
    "META": {"mode": "side", "note": "조정 EPS: 소송 비용(일회성) 제외 영업이익 기준 PEG 약 1.7 (소송 비용 포함 시 이익 -3%로 산출 불가)"},
    "QCOM": {"mode": "none", "note": "조정 EPS(비GAAP) 기준으로도 순이익 -15%·선행 -36%라 PEG 산출 불가. 트레이딩뷰 0.08은 착시"},
    "INTC": {"mode": "none", "note": "조정 EPS(비GAAP)도 4Q 가이던스가 전 분기 대비 -52%라 PEG 산출 불가"},
    "CRWD": {"mode": "none", "note": "조정 EPS(비GAAP, FY27 가이던스 $1.255) 기준 PER 약 173배이나 전년 비교치를 확인하지 못해 산출 불가"},
    "CRM": {"mode": "gain", "peg": 2.3, "per": "약 23배", "gr": "+10%(가정)", "why": "투자이익 제외 기초 이익"},
    "WDC": {"mode": "gain", "peg": 0.31, "per": "15.6배", "gr": "+50%(가정)", "why": "비영업 이익 제외 비GAAP 연환산"},
    "GOOGL": {"mode": "gain", "peg": 1.0, "per": "약 26.6배", "gr": "+26.5%", "why": "지분 평가이익 제외 영업이익"},
    "AMZN": {"mode": "gain", "peg": 0.87, "per": "약 32.3배", "gr": "+37.1%", "why": "지분 평가이익 제외 영업이익"},
    "MSFT": {"mode": "gain", "peg": 1.46, "per": "약 29.2배", "gr": "+20%", "why": "오픈AI 손익 제외 영업이익"},
    "AAPL": {"mode": "gain", "peg": 2.2, "per": "38.9배", "gr": "+18%", "why": "관세 환급 제외"},
    "ORCL": {"mode": "gain", "peg": 0.62, "per": "14.3배", "gr": "+23%", "why": "암페어 이익 제외 선행 EPS"},
    "NVDA": {"mode": "gain", "peg": 0.26, "per": "약 27.6배", "gr": "+106%", "why": "지분 평가이익 제외 영업이익"},
    "IBM": {"mode": "main", "peg": 1.65, "per": "21.1배", "gr": "+12%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표)"},
    "JNJ": {"mode": "main", "peg": 10.3, "per": "26.8배", "gr": "+3%", "note": "조정 EPS 기준 PEG, 조정 EPS 성장이 낮아 크게 초과"},
    "ABBV": {"mode": "main", "peg": 0.64, "per": "23.0배", "gr": "+36%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표)"},
    "CEG": {"mode": "main", "peg": 0.68, "per": "22.2배", "gr": "+33%", "note": "조정 EPS 기준 PEG(보고서 PEG 심층 표)"},
    "ILMN": {"mode": "main", "peg": 2.19, "per": "39.4배", "gr": "+18%", "note": "조정 EPS 기준 PEG, 가이던스 성장 기준으로는 약 3.2"},
    "BE": {"mode": "main", "peg": 0.28, "per": "73.6배", "gr": "+268%(기저 효과)", "note": "조정 EPS 기준이나 직전 4분기 조정 EPS가 낮아 성장률이 부풀려진 기저 효과, 의미 제한적"},
    "VST": {"mode": "none", "note": "기저 효과로 EPS 성장률이 왜곡돼 산출 불가(보고서 PEG 심층 표 참고)"},
    "GEV": {"mode": "none", "note": "EPS 성장률이 왜곡돼 산출 불가(보고서 PEG 심층 표 참고)"},
    "COIN": {"mode": "none", "note": "TTM EPS 적자, 조정 EPS 미발표로 산출 불가"},
    "HOOD": {"mode": "none", "note": "TTM EPS가 감소해 산출 불가"},
    "CRCL": {"mode": "none", "note": "성장률 비교 기준이 왜곡돼 산출 불가(보고서 PEG 심층 표 참고)"},
    "BA": {"mode": "none", "note": "TTM EPS 변동이 커 산출 불가(보고서 PEG 심층 표 참고)"},
    "JOBY": {"mode": "none", "note": "적자라 산출 불가"},
    "ACHR": {"mode": "none", "note": "적자라 산출 불가"},
    "ONDS": {"mode": "none", "note": "TTM EPS가 1Q26 영업외 이익 때문에 흑자로 왜곡돼 산출 불가"},
    "UMAC": {"mode": "none", "note": "적자라 산출 불가"},
}

def peg_board():
    rows = []
    for r in REPORTS:
        tk = r[4]; d = _peg_data(r); px, ch, c = PRICE[tk]
        per, gr, peg, lim = d if d else ("-", "-", None, False)
        ad = ADJ_PEG.get(tk, {}); adj_note = ad.get("note", "")
        if ad.get("mode") == "gain":
            adj_note = f"조정 EPS 기준({ad['why']}, 보고서 추정). 일회성 이익 포함 PEG {peg:.2f}" if peg is not None else ""
            per, gr, peg, lim = ad["per"], ad["gr"], ad["peg"], False
        elif ad.get("mode") == "main": per, gr, peg, lim = ad["per"], ad["gr"], ad["peg"], False
        elif ad.get("mode") == "none": peg, lim = None, False
        if peg is None: v, tg = "산출 불가", '<span class="small">산출 불가</span>'
        elif peg <= 0.5: v, tg = f"{peg:.2f}", '<span class="tag g">적극 매수권</span>'
        elif peg <= 1.0: v, tg = f"{peg:.2f}", '<span class="tag y">투자 적격</span>'
        else: v, tg = f"{peg:.2f}", '<span class="tag b">기준 초과</span>'
        rem = "" if peg is None else ("성장률이 불황 바닥 기준이라 부풀려진 값, 의미 제한적" if lim or peg < 0.05 else "")
        if peg is None: rem = "적자 등으로 산출 불가" if d else "보고서에 PEG 정보 없음"
        if adj_note: rem = (adj_note + ". " + rem).rstrip(". ") if rem and peg is not None else (adj_note if peg is not None or ad.get("mode") != "none" else adj_note)
        star = ""
        live = f" data-q='{tk}'" if tk not in ("005930", "000660") else ""
        rows.append((peg if peg is not None else 1e9, f'<tr{live}><td class="rk"></td><td><a class="bn" href="{r[0]}"><span class="bl0">{ICON[tk]}</span><span><b>{r[3].replace(" 기업분석","")}</b><br><span class="small">{tk} · {r[6]}</span></span></a></td>'
                     f'<td class="r">{px}<br><span class="{c}">{ch}</span></td><td class="r xd">{per}</td><td class="r xd">{gr}</td><td class="r"><b>{v}</b></td><td>{tg}</td><td class="rm xd">{rem}</td></tr>'))
    rows.sort(key=lambda x: x[0])
    return ('<div class="panel cmp board" id="pegboard"><table><thead><tr><th class="rk">#</th><th>기업</th><th class="r">종가</th><th class="r xd">PER(TTM)</th><th class="r xd">EPS 성장(YoY)</th><th class="r">PEG</th><th>판정</th><th class="xd">비고</th></tr></thead><tbody>'
            + "".join(x[1] for x in rows) + '</tbody></table></div><div class="pager" id="pegpager"></div>')

def fg_label(v):
    return "극단적 공포" if v < 25 else ("공포" if v < 45 else ("중립" if v <= 55 else ("탐욕" if v < 75 else "극단적 탐욕")))

NEWS_CSS = """
.nwbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 14px}.nwbar input,.nwbar select{font:inherit;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 10px}.nwbar input{flex:1;min-width:140px}.nwbar .cnt{font-size:12px;color:var(--muted);margin-left:auto}
.nwl{list-style:none;margin:0;padding:0}.nwl li{border-bottom:1px solid var(--line);padding:13px 2px}.nwl a.t{font-size:15px;font-weight:600;color:var(--ink);text-decoration:none;line-height:1.45}.nwl a.t:hover{text-decoration:underline}
.nwl .s{font-size:13px;color:var(--muted);margin:4px 0 6px;line-height:1.5}.nwl .m{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}.nwl .tk{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:11.5px;color:var(--ink2);text-decoration:none;background:var(--card)}
.nwmore{display:block;margin:16px auto 0;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:8px 22px;font:inherit;font-size:13px;cursor:pointer}.nwempty{padding:30px 0;color:var(--muted);font-size:14px;text-align:center}.nwnote{font-size:12px;color:var(--muted);margin-top:14px;line-height:1.6}
"""
CSS += NEWS_CSS

BR_CSS = """
.brtab{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:4px 0 12px}.brtab .pill{padding:6px 16px}.brtab select{font:inherit;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 9px;margin-left:auto}
.brsum{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--navy);border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.65;margin-bottom:6px}.brsum .gn{display:block;font-size:12px;color:var(--muted);margin-top:4px}
.brl{list-style:none;margin:0;padding:0;counter-reset:br}.brl li{counter-increment:br;border-bottom:1px solid var(--line);padding:14px 2px 14px 34px;position:relative}.brl li:before{content:counter(br);position:absolute;left:2px;top:14px;width:22px;height:22px;border-radius:50%;background:var(--navy);color:var(--card);font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.brl .lb{display:inline-block;font-size:11px;font-weight:700;border-radius:3px;padding:1px 7px;margin-right:6px;background:var(--soft,#eee);color:var(--ink2);vertical-align:1px}.brl a.t{font-size:15.5px;font-weight:700;color:var(--ink);text-decoration:none;line-height:1.5}.brl a.t:hover{text-decoration:underline}
.brl .s{font-size:13.5px;color:var(--ink2);margin:5px 0;line-height:1.6}.brl .o{font-size:12px;color:var(--muted);margin:3px 0 6px;font-style:italic}.brl .m{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}.brl .tk{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:11.5px;color:var(--ink2);text-decoration:none;background:var(--card)}
"""
CSS += BR_CSS

CN_CSS = """
.cdk{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:0;scrollbar-width:none;max-width:460px;margin:8px auto 0;border-radius:18px;outline:none}.cdk::-webkit-scrollbar{display:none}
.cd{flex:0 0 100%;scroll-snap-align:center;aspect-ratio:3/4;box-sizing:border-box;padding:26px 24px;background:linear-gradient(160deg,#10172f,#0b1024 60%,#141a3d);color:#eef0ff;display:flex;flex-direction:column;position:relative;overflow:hidden}
.cd .ck{font-size:11px;letter-spacing:.18em;color:#8b93ff;font-weight:700;margin-bottom:12px}.cd .ct{font-size:26px;font-weight:800;line-height:1.25;margin-bottom:6px}.cd .cm{font-size:12.5px;color:#9aa3c7;margin-bottom:14px}.cd .cf{margin-top:auto;font-size:11.5px;color:#7c85ad;padding-top:10px}
.cd.cv{justify-content:center}.cv .cbig{font-size:44px;font-weight:900;line-height:1.15;margin:8px 0 14px}.cv .cdt{font-size:20px;color:#c7ccff;font-weight:700}.cv .cs{font-size:13px;color:#9aa3c7;margin-top:14px;line-height:1.6}.cv .cs2{font-size:15px;line-height:1.8;color:#c9cef0}.cv .cf{margin-top:28px}
.tg3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}.tl{background:rgba(255,255,255,.06);border-radius:12px;padding:12px 10px}.tl .tn{font-size:11px;color:#9aa3c7;margin-bottom:6px}.tl .tp{font-size:16px;font-weight:800}.tl .tc{font-size:13px;font-weight:700;margin-top:3px;color:#9aa3c7}.tl .tc.u{color:#ff6b6b}.tl .tc.d{color:#5aa2ff}
.gw{position:relative;margin:6px auto 0;width:100%;max-width:320px}.gg{width:100%;display:block}.gs2{text-align:center;font-size:52px;font-weight:900;margin-top:4px;line-height:1.1}.gr{text-align:center;font-size:18px;font-weight:800;margin-top:2px;color:#ffd27a}
.gh{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:26px}.gh div{background:rgba(255,255,255,.06);border-radius:12px;padding:10px 12px;display:flex;justify-content:space-between;font-size:13px}.gh span{color:#9aa3c7}.gh b{font-size:16px}
.cd.nw .cl{align-self:flex-start;font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:999px;background:rgba(129,140,248,.22);color:#c7ccff;margin-bottom:14px}.nh{font-size:23px;font-weight:800;line-height:1.4;margin-bottom:16px;word-break:keep-all}.nsum{font-size:14.5px;line-height:1.7;color:#d7dbf7;background:rgba(255,255,255,.06);border-radius:12px;padding:12px 14px;margin-bottom:12px}.nsum b{color:#ffd27a}
.no{font-size:12px;color:#8e97c0;font-style:italic;line-height:1.5;margin-bottom:12px}.ntg{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.ctk{font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px;background:rgba(255,255,255,.1);color:#eef0ff;text-decoration:none}.nm2{font-size:11.5px;color:#7c85ad}
.nb{margin-top:auto;align-self:stretch;text-align:center;background:#6366f1;color:#fff;font-weight:700;font-size:14px;padding:11px;border-radius:12px;text-decoration:none}
.es{font-size:12px;letter-spacing:.08em;color:#8b93ff;font-weight:700;margin:12px 0 8px}.eg{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}.eg>span{font-size:12px;color:#9aa3c7;min-width:62px}.em{font-size:13px;color:#7c85ad}.ei{display:flex;gap:10px;font-size:13.5px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.08)}.ei span{color:#ffd27a;font-weight:700;min-width:44px}.ei i{margin-left:auto;color:#f59e0b;font-style:normal;font-size:11px}
.cnav{display:flex;justify-content:center;align-items:center;gap:16px;margin:10px 0 4px}.cnav button{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:inherit;font-size:18px;cursor:pointer}#cct{font-size:13px;color:var(--muted);min-width:56px;text-align:center}
"""
CSS += CN_CSS

GS_CSS = """
.gl{display:grid;grid-template-columns:248px minmax(0,1fr);align-items:start}
.gl>.gm{min-width:0}.gl .readwrap{display:block;min-height:0;background:transparent}
.gs.side{top:53px;height:calc(100vh - 53px);padding:16px 12px 24px;display:flex;flex-direction:column;gap:2px}
.gs a.si,.gs summary{display:flex;align-items:center;gap:8px;font-size:14.5px;font-weight:600;padding:9px 10px;border-radius:8px;color:#222;text-decoration:none;cursor:pointer;list-style:none}
.gs summary::-webkit-details-marker{display:none}.gs summary:after{content:"›";margin-left:auto;font-size:18px;color:var(--muted);transition:transform .15s}.gs details[open]>summary:after{transform:rotate(90deg)}
.gs a.si.on,.gs a.si:hover,.gs summary:hover{background:#f2f2f3}.gs summary .n{font-size:11px;font-weight:500;color:var(--muted);background:var(--soft,#eee);border-radius:999px;padding:1px 7px}
.gs .sl{display:flex;flex-direction:column;margin:2px 0 6px 12px;padding-left:8px;border-left:1px solid var(--line);max-height:calc(100vh - 330px);overflow:auto}
.gs .sl a{font-size:13px;font-weight:400;padding:5px 8px;border-radius:6px;color:#4b5563;text-decoration:none;line-height:1.35}.gs .sl a.on,.gs .sl a:hover{background:#f2f2f3;color:#111}.gs .sl a.all{font-weight:600;color:#111}
html[data-theme=dark] .gs a.si,html[data-theme=dark] .gs summary,html[data-theme=dark] .gs .sl a.all{color:var(--ink)}html[data-theme=dark] .gs .sl a{color:var(--ink2)}
html[data-theme=dark] .gs a.si.on,html[data-theme=dark] .gs a.si:hover,html[data-theme=dark] .gs summary:hover,html[data-theme=dark] .gs .sl a.on,html[data-theme=dark] .gs .sl a:hover{background:var(--hover);color:var(--ink)}
@media(min-width:1001px){.top a.nv{display:none}.top .in{max-width:none;padding-left:18px}.top .thm{margin-left:auto}}
@media(max-width:1000px){.gl{display:block}.gs.side{display:none}}
@media(max-width:560px){.top a.nv{padding:5px 5px;font-size:12.5px}.top .thm{width:28px;margin-left:4px}}
"""
CSS += GS_CSS

GS_JS = """<script>(function(){var d=document.querySelector('.gs details'),L=document.querySelector('.gs .sl');if(!d)return;try{var v=localStorage.getItem('gsOpen');if(v==='1')d.open=true;else if(v==='0'&&!d.dataset.keep)d.open=false}catch(e){}
d.addEventListener('toggle',function(){try{localStorage.setItem('gsOpen',d.open?'1':'0')}catch(e){}});
var a=L&&L.querySelector('a.on');if(a&&d.open)L.scrollTop=Math.max(0,a.offsetTop-L.clientHeight/2);
var S=[['market','m'],['heatmap','h'],['reports','r']].map(function(x){return[document.getElementById(x[0]),document.querySelector('.gs a[data-k="'+x[1]+'"]')]}),H=document.querySelector('.gs a[data-k="home"]');
if(S[0][0]&&H){function sp(){var cur=H;S.forEach(function(x){if(x[0]&&x[1]&&x[0].getBoundingClientRect().top<=140)cur=x[1]});[H].concat(S.map(function(x){return x[1]})).forEach(function(l){if(l)l.classList.toggle('on',l===cur)})}addEventListener('scroll',sp,{passive:true});sp()}})();</script>"""

SR_CSS = """
.gsq{margin:0 2px 8px}.gsq input,.mq input{width:100%;box-sizing:border-box;font:inherit;font-size:13.5px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.gsq input:focus,.mq input:focus{outline:2px solid var(--navy);outline-offset:-1px}
.sres{display:none;flex-direction:column;gap:1px}.sres a{display:flex;justify-content:space-between;gap:8px;align-items:baseline;padding:8px 10px;border-radius:7px;text-decoration:none;color:var(--ink);font-size:13.5px}.sres a span{font-size:11.5px;color:var(--muted)}.sres a:hover,.sres a.hi{background:var(--hover)}.sres .none{padding:10px;font-size:13px;color:var(--muted)}
.gs.searching>:not(.gsq):not(.sres){display:none}.gs.searching>.sres{display:flex}
.tbtn{display:none;flex:none;width:34px;height:30px;margin-left:6px;border-radius:2px;border:1px solid rgba(230,216,191,.28);background:transparent;color:#E6D8BF;cursor:pointer;font-size:16px;line-height:1;align-items:center;justify-content:center}.tbtn:hover{background:rgba(255,255,255,.08)}
.mp{display:none;position:fixed;left:0;right:0;top:50px;z-index:40;background:var(--card);color:var(--ink);border-bottom:1px solid var(--line);box-shadow:0 10px 24px rgba(0,0,0,.18);padding:12px 14px 16px;max-height:calc(100vh - 50px);overflow:auto}.mp.open{display:block}
.mp a.mi{display:flex;align-items:center;gap:10px;padding:12px 8px;border-bottom:1px solid var(--line);text-decoration:none;color:var(--ink);font-size:15px;font-weight:600}.mp a.mi.on{color:var(--gold)}.mp a.mi:last-child{border-bottom:0}
.mp .sres{display:flex;margin-top:8px}.mq input{font-size:16px;padding:10px 12px}
@media(max-width:1000px){.tbtn{display:flex}.top .thm{margin-left:auto}.top a.nv{display:none}}
"""
CSS += SR_CSS

SR_JS = """<script>(function(){var D=__SD__;
function find(q){q=q.trim().toLowerCase();if(!q)return[];var o=[];D.forEach(function(x){var i=x[3].indexOf(q);if(i>=0)o.push([x,x[2].toLowerCase()===q?-3:x[1].toLowerCase().indexOf(q)===0?-2:(' '+x[3]).indexOf(' '+q)>=0?-1:0])});o.sort(function(a,b){return a[1]-b[1]});return o.slice(0,14).map(function(a){return a[0]})}
function show(ul,q){var r=find(q);ul.innerHTML=r.length?r.map(function(x,i){return'<a href="'+x[0]+'"'+(i?'':' class="hi"')+'><b>'+x[1]+'</b><span>'+x[2]+'</span></a>'}).join(''):(q.trim()?'<div class="none">검색 결과가 없습니다</div>':'');return r}
function wire(inp,ul,onq){if(!inp)return;inp.addEventListener('input',function(){show(ul,inp.value);onq&&onq(!!inp.value.trim())});inp.addEventListener('keydown',function(e){if(e.key==='Enter'){var a=ul.querySelector('a');if(a)location.href=a.getAttribute('href')}else if(e.key==='Escape'){inp.value='';show(ul,'');onq&&onq(false);inp.blur()}})}
var g=document.querySelector('.gs');wire(document.getElementById('sq'),document.getElementById('sr'),function(on){if(g)g.classList.toggle('searching',on)});
var mq=document.getElementById('mq');wire(mq,document.getElementById('mr'));
var sp=document.getElementById('spn'),mp=document.getElementById('mpn'),bs=document.getElementById('tsb'),bm=document.getElementById('tmb');
function tog(a,b,focus){if(!a)return;var o=!a.classList.contains('open');a.classList.toggle('open',o);if(b)b.classList.remove('open');if(o&&focus)setTimeout(function(){focus.focus()},30)}
if(bs)bs.addEventListener('click',function(e){e.stopPropagation();tog(sp,mp,mq)});if(bm)bm.addEventListener('click',function(e){e.stopPropagation();tog(mp,sp)});
document.addEventListener('click',function(e){[sp,mp].forEach(function(p){if(p&&p.classList.contains('open')&&!p.contains(e.target))p.classList.remove('open')})});
document.querySelectorAll('.mp a').forEach(function(a){a.addEventListener('click',function(){[sp,mp].forEach(function(p){p&&p.classList.remove('open')})})});})();</script>"""

CAL_CSS = """
.cltabs{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 12px}.cltabs .sp{margin-left:auto;font-size:12px;color:var(--muted)}
.cltb{width:100%;border-collapse:collapse;font-size:14px}.cltb th{text-align:left;padding:8px 9px;border-bottom:2px solid var(--navy);font-weight:600;white-space:nowrap;font-size:13px}.cltb td{padding:9px;border-bottom:1px solid var(--line);vertical-align:top}.cltb .r{text-align:right;white-space:nowrap}.cltb tr.dh td{background:var(--soft);font-weight:700;font-size:13px;padding:7px 9px;border-bottom:1px solid var(--line)}.cltb tr.dh.td td{background:var(--navy);color:var(--card)}
.cltb .en{display:block;font-size:11.5px;color:var(--muted);margin-top:1px}.cltb .st{color:#d97706;font-size:12px;letter-spacing:-1px}.cltb td.t{white-space:nowrap;color:var(--ink2);font-variant-numeric:tabular-nums}.cltb .pend{color:var(--muted);font-size:12px}
.cltb .bg{display:inline-block;font-size:11.5px;font-weight:700;border-radius:3px;padding:1px 7px;white-space:nowrap}.cltb .bg.up{background:rgba(34,197,94,.14);color:#15803d}.cltb .bg.dn{background:rgba(239,68,68,.14);color:#b91c1c}.cltb .bg.eq{background:var(--soft);color:var(--ink2)}
html[data-theme=dark] .cltb .bg.up{color:#4ade80}html[data-theme=dark] .cltb .bg.dn{color:#f87171}.cltb a.cn{text-decoration:none;color:var(--ink);font-weight:600}.cltb a.cn:hover{text-decoration:underline}
.clwrap{overflow-x:auto}.clempty{padding:28px 0;text-align:center;color:var(--muted);font-size:14px}
"""
CSS += CAL_CSS

CALD_CSS = """
.calw{max-width:1180px;margin:0 auto;padding:20px 22px 80px}
.cph{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:2px solid var(--navy);padding-bottom:10px;margin-bottom:12px}.cph .t{font-size:22px;font-weight:700}.cph .a{font-size:13px;color:var(--muted)}
.cdl{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}.cdl a{font-size:12.5px;text-decoration:none;color:var(--ink2);border:1px solid var(--line);border-radius:999px;padding:4px 12px;background:var(--card)}.cdl a.on{background:var(--navy);color:var(--card);border-color:var(--navy)}
.chd{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 12px}.chd .ttl{font-size:19px;font-weight:700;min-width:118px}.chd .sp{margin-left:auto}.chd .grp{display:flex;gap:6px}
.chd button,.cnb{font:inherit;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:5px 12px;cursor:pointer}.chd button.on{background:var(--navy);color:var(--card);border-color:var(--navy)}.chd button.sq{width:34px;padding:5px 0}
.cdh{font-size:12px;color:var(--muted);margin:0 0 8px}
.mg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border-top:1px solid var(--line);border-left:1px solid var(--line);background:var(--card);border-radius:10px;overflow:hidden}
.mg .wh{padding:7px 10px;font-size:12px;color:var(--muted);border-right:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--soft)}
.mg .dc{min-height:128px;padding:6px 6px 5px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);cursor:pointer;display:flex;flex-direction:column;gap:3px;min-width:0}.mg .dc:hover{background:var(--hover)}
.mg .dc.out{background:repeating-linear-gradient(135deg,transparent 0 6px,rgba(128,128,128,.09) 6px 7px);cursor:default}.mg .dc.we{background:var(--soft)}
.mg .dn{font-size:13px;font-weight:700;margin-bottom:1px;width:24px;height:24px;display:flex;align-items:center;justify-content:center}.mg .dc.td .dn{background:var(--navy);color:var(--card);border-radius:50%}
.cbar{flex:none;display:flex;gap:5px;align-items:baseline;border-left:3px solid var(--navy);padding:2px 5px;font-size:11.5px;line-height:1.35;background:rgba(128,128,128,.1);border-radius:0 3px 3px 0;overflow:hidden;white-space:nowrap}.cbar b{overflow:hidden;text-overflow:ellipsis;font-weight:600}.cbar.past{opacity:.5}
.cbar.i3{border-left-color:#dc2626}.cbar.i2{border-left-color:#d97706}.cbar.i1{border-left-color:#9ca3af}.cbar.e{border-left-color:var(--blue)}
.tm{color:var(--muted);font-variant-numeric:tabular-nums;flex:none}.tm.pre:after{content:"전";font-size:9.5px;margin-left:1px}.tm.post:after{content:"후";font-size:9.5px;margin-left:1px}
.more{font:inherit;font-size:11.5px;color:var(--muted);background:none;border:0;text-align:left;padding:1px 4px;cursor:pointer}.mg .cn{display:none}
.cdm{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:60;display:none;align-items:center;justify-content:center;padding:16px}.cdm.open{display:flex}
.cdb{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:14px;width:min(560px,100%);max-height:86vh;overflow:auto;padding:16px 16px 18px;box-shadow:0 20px 50px rgba(0,0,0,.3)}.cdb .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.cdb .hd b{font-size:17px}.cdb .x{font:inherit;font-size:20px;line-height:1;background:none;border:0;color:var(--muted);cursor:pointer}
.wc{margin:0 0 8px;padding:8px 10px;border:1px solid var(--line);border-left:3px solid var(--navy);border-radius:6px;font-size:12.5px;background:var(--paper);line-height:1.45}.wc.i3{border-left-color:#dc2626}.wc.i2{border-left-color:#d97706}.wc.i1{border-left-color:#9ca3af}.wc.e{border-left-color:var(--blue)}.wc.past{opacity:.78}
.wc .wt{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}.wc .wt .tm{font-size:15px;font-weight:700;color:var(--ink)}.wc .wt b{font-size:13.5px}.wc .wt a{color:var(--ink);text-decoration:none}.wc .wt a:hover{text-decoration:underline}.wc .st{color:#d97706;font-size:11px;letter-spacing:-1px}
.wc .en{font-size:11.5px;color:var(--muted)}.wc .vals{display:flex;gap:4px 10px;flex-wrap:wrap;margin-top:5px;font-size:12px;color:var(--ink2);align-items:center}.wc .vals b{color:var(--ink)}
.bg{display:inline-block;font-size:11px;font-weight:700;border-radius:3px;padding:1px 6px;white-space:nowrap}.bg.up{background:rgba(34,197,94,.15);color:#15803d}.bg.dn{background:rgba(239,68,68,.15);color:#b91c1c}.bg.eq{background:var(--soft);color:var(--ink2)}
html[data-theme=dark] .bg.up{color:#4ade80}html[data-theme=dark] .bg.dn{color:#f87171}
.wk{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;align-items:start}.wd{background:var(--card);border:1px solid var(--line);border-radius:10px;min-height:120px;overflow:hidden}.wd .wh2{padding:8px 10px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:baseline;font-size:13px;font-weight:700;background:var(--soft)}.wd .wh2 span{font-weight:500;font-size:11.5px;color:var(--muted)}
.wd.td .wh2{background:var(--navy);color:var(--card)}.wd.td .wh2 span{color:var(--card);opacity:.8}.wd .bd{padding:8px 7px 0}.wd .emp{font-size:12px;color:var(--muted);padding:6px 4px 10px;text-align:center}.wd.we{opacity:.9}
.wk .wc .vals{display:grid;grid-template-columns:1fr 1fr;gap:3px 8px}
@media(max-width:1000px){.wk{grid-template-columns:1fr}.wd{min-height:0}}
@media(max-width:700px){.mg .cbar,.mg .more{display:none}.mg .dc{min-height:62px;align-items:flex-start;padding:4px}.mg .cn{display:inline-flex;font-size:11px;font-weight:700;background:var(--navy);color:var(--card);border-radius:999px;min-width:20px;height:20px;align-items:center;justify-content:center;padding:0 5px}.mg .wh{padding:6px 2px;text-align:center}.calw{padding:14px 12px 70px}}
"""
CSS += CALD_CSS

def gside(on, cur):
    it = "".join(f'<a class="{"on" if r[0] == cur else ""}" href="{r[0]}">{r[3].replace(" 기업분석", "")}</a>' for r in REPORTS)
    c = lambda k: " on" if on == k else ""
    return ('<aside class="side gs">'
            '<div class="gsq"><input id="sq" type="search" placeholder="기업 검색 (이름·티커·한글)" autocomplete="off" aria-label="기업 검색"></div><div class="sres" id="sr"></div>'
            f'<a class="si{" on" if on == "home" else ""}" data-k="home" href="index.html">🏠 홈</a>'
            '<a class="si" data-k="m" href="index.html#market">📈 지수선물</a>'
            '<a class="si" data-k="h" href="index.html#heatmap">🔥 히트맵</a>'
            f'<a class="si{c("options")}" href="options.html">🎯 옵션</a>'
            f'<a class="si{c("f13")}" href="f13.html">🏛 13F</a>'
            f'<details{" open data-keep=1" if on == "reports" else ""}><summary>📚 기업분석 <span class="n">{len(REPORTS)}</span></summary><div class="sl"><a class="all" data-k="r" href="index.html#reports">전체 보기</a>{it}</div></details>'
            f'<a class="si{c("calendar")}" href="calendar.html">📅 일정</a>'
            f'<a class="si{c("news")}" href="news.html">📰 뉴스</a>'
            f'<a class="si{c("briefing")}" href="briefing.html">🗞 브리핑</a></aside>')

def _sd():
    return json.dumps([[r[0], r[3].replace(" 기업분석", ""), r[4], (r[4] + " " + r[3].replace(" 기업분석", "") + " " + r[5] + " " + r[6] + " " + KO_ALIAS.get(r[4], "")).lower()] for r in REPORTS], ensure_ascii=False).replace("</", "<\\/")
def mpanels(on):
    c = lambda k: " on" if on == k else ""
    return ('<div class="mp" id="spn"><div class="mq"><input id="mq" type="search" placeholder="기업 검색 (이름·티커·한글)" autocomplete="off" aria-label="기업 검색"></div><div class="sres" id="mr"></div></div>'
            '<div class="mp" id="mpn">'
            f'<a class="mi{c("home")}" href="index.html">🏠 홈</a><a class="mi" href="index.html#market">📈 지수선물</a><a class="mi" href="index.html#heatmap">🔥 히트맵</a>'
            f'<a class="mi{c("options")}" href="options.html">🎯 옵션</a>'
            f'<a class="mi{c("f13")}" href="f13.html">🏛 13F</a>'
            f'<a class="mi{c("reports")}" href="index.html#reports">📚 기업분석 전체 ({len(REPORTS)})</a><a class="mi{c("calendar")}" href="calendar.html">📅 일정</a><a class="mi{c("news")}" href="news.html">📰 뉴스</a><a class="mi{c("briefing")}" href="briefing.html">🗞 브리핑</a></div>')

def shell(title, inner, on="home", cur=None):
    nav = "".join(f'<a class="nv {"on" if on == k else ""}" href="{h}">{t}</a>' for k, h, t in
                  [("home", "index.html", "홈"), ("market", "index.html#market", "지수선물"), ("heatmap", "index.html#heatmap", "히트맵"), ("options", "options.html", "옵션"), ("f13", "f13.html", "13F"), ("reports", "index.html#reports", "기업분석"), ("calendar", "calendar.html", "일정"), ("news", "news.html", "뉴스"), ("briefing", "briefing.html", "브리핑")])
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>{FONT}{THEME_INIT}<style>{CSS}</style></head><body>
<div class="top"><div class="in"><a class="brand" href="index.html"><span class="mk">CA</span><span class="w">CORPORATE ANALYSIS</span></a>{nav}<button class="thm" type="button" aria-label="다크 모드 전환" title="다크 모드 전환"><span class="sun">☀</span><span class="moon">☾</span></button><button class="tbtn" id="tsb" type="button" aria-label="기업 검색">🔍</button><button class="tbtn" id="tmb" type="button" aria-label="메뉴">☰</button></div></div>
{mpanels(on)}
<div class="gl">{gside(on, cur)}<div class="gm">{inner}</div></div><div class="vis" id="vis" aria-live="off"></div>{GS_JS}{SR_JS.replace("__SD__", _sd())}<script>(function(){{var B='https://abacus.jasoncameron.dev/',N='ca-excellent3935/',d=new Date().toLocaleDateString('sv-SE',{{timeZone:'Asia/Seoul'}}).replace(/-/g,''),el=document.getElementById('vis'),seen=false;try{{seen=localStorage.getItem('visD')===d}}catch(e){{}}
function g(k,hit){{return fetch(B+(hit?'hit/':'get/')+N+k).then(function(r){{return r.ok?r.json():{{value:0}}}}).then(function(j){{return j.value||0}}).catch(function(){{return null}})}}
Promise.all([g('visits',!seen),g('d'+d,!seen)]).then(function(v){{if(v[0]==null)return;try{{localStorage.setItem('visD',d)}}catch(e){{}}el.textContent='방문 누적 '+v[0].toLocaleString('ko-KR')+' · 오늘 '+(v[1]||0).toLocaleString('ko-KR')}})}})();</script>{THEME_JS}</body></html>"""

_LBL = {"소프트웨어": "소프트웨어·클라우드", "양자": "양자컴퓨팅"}
PILLS = '<button class="pill on" data-f="all">전체</button>' + "".join(f'<button class="pill" data-f="{t}">{_LBL.get(t, t)}</button>' for t in dict.fromkeys(r[6] for r in sorted(REPORTS, key=lambda r: -sum(1 for x in REPORTS if x[6] == r[6]))))

KO_ALIAS = {"TGT": "타깃 타겟 target", "HUM": "휴매나 후마나 humana 메디케어", "UBER": "우버 uber 승차 배달", "INTU": "인튜이트 인투이트 intuit 터보택스 퀵북스", "ON": "온세미 온세미컨덕터 on semiconductor", "ADI": "아날로그 디바이시스 아날로그디바이스", "MRK": "머크 엠에스디 msd 키트루다", "MRNA": "모더나 엠알엔에이", "MU": "마이크론", "GOOGL": "구글 알파벳", "MSFT": "마이크로소프트 마소", "AMZN": "아마존", "NVDA": "엔비디아", "MRVL": "마벨", "TSM": "티에스엠씨 tsmc 대만반도체", "AVGO": "브로드컴", "AMD": "에이엠디", "INTC": "인텔",
    "QCOM": "퀄컴", "ORCL": "오라클", "PLTR": "팔란티어", "META": "메타 페이스북", "CRWV": "코어위브", "TSLA": "테슬라", "SPCX": "스페이스엑스", "DELL": "델", "SNDK": "샌디스크", "CRWD": "크라우드스트라이크",
    "NBIS": "네비우스", "AAPL": "애플", "LLY": "일라이릴리 릴리", "JPM": "제이피모건 jp모건", "TXN": "텍사스인스트루먼트", "ASTS": "에이에스티 스페이스모바일", "RKLB": "로켓랩", "NOW": "서비스나우", "CRM": "세일즈포스",
    "RDDT": "레딧", "SMCI": "슈퍼마이크로 슈마컴", "IREN": "아이렌", "WDC": "웨스턴디지털", "VRT": "버티브", "COHR": "코히런트", "MSTR": "스트래티지 마이크로스트래티지", "UNH": "유나이티드헬스", "KO": "코카콜라",
    "WMT": "월마트", "COST": "코스트코", "IONQ": "아이온큐", "IBM": "아이비엠", "UMAC": "언유주얼 머신스 드론", "JOBY": "조비 에어택시", "ACHR": "아처 에어택시", "ONDS": "온다스 드론", "GEV": "지이 버노바 ge", "CEG": "컨스텔레이션 에너지 원전", "BE": "블룸에너지 연료전지", "VST": "비스트라 전력", "COIN": "코인베이스", "CRCL": "서클 스테이블코인 usdc", "HOOD": "로빈후드", "JNJ": "존슨앤드존슨 존슨앤존슨", "ILMN": "일루미나", "ABBV": "애브비", "BA": "보잉", "GE": "지이 에어로스페이스 항공엔진 ge", "RTX": "레이시온 알티엑스 방산", "LMT": "록히드마틴 방산", "AXON": "액슨 테이저", "BAC": "뱅크오브아메리카 뱅오아 은행", "WFC": "웰스파고 은행", "V": "비자 카드 결제", "MA": "마스터카드 결제", "MP": "엠피 머티리얼즈 희토류", "LRCX": "램리서치 반도체장비", "AMAT": "어플라이드 머티어리얼즈 어플라이드머티리얼즈 반도체장비", "KLAC": "케이엘에이 kla 반도체장비", "TER": "테라다인 반도체 테스트", "HIMS": "힘스앤허스 힘스 원격의료", "TEM": "템퍼스 ai 정밀의료", "NVO": "노보 노디스크 위고비 비만", "CRSP": "크리스퍼 유전자가위", "QBTS": "디웨이브 양자", "RGTI": "리게티 양자", "DDOG": "데이터독 관측", "SNPS": "시높시스 eda 반도체설계", "VRSN": "베리사인 도메인", "CRDO": "크레도 aec 광연결", "PEP": "펩시코 펩시 음료 스낵", "LITE": "루멘텀 광통신 레이저 ocs", "ANET": "아리스타 네트웍스 이더넷 스위치", "PANW": "팔로알토 네트웍스 보안 방화벽", "NKE": "나이키 신발 스포츠웨어", "RACE": "페라리 슈퍼카", "APP": "앱러빈 광고 게임", "ARM": "암 홀딩스 cpu 설계", "NFLX": "넷플릭스 스트리밍", "CBRS": "세레브라스 웨이퍼 ai 추론", "ALAB": "아스테라 랩스 연결 반도체"}

def cover(r):  # 작은 정사각 타일
    f, d, src, title, tk, comp, tag, sub, bg, line, url = r
    px, ch, c = PRICE[tk]
    dq = f' data-q="{tk}"' if tk not in ("005930", "000660") else ""
    return (f'<a class="book tcard" data-tag="{tag}" data-s="{(tk+" "+title.replace(" 기업분석","")+" "+comp+" "+tag+" "+KO_ALIAS.get(tk,"")).lower()}"{dq} href="{f}" title="{sub}"><div class="tl-top"><span class="tl-tag">{tag}</span><span class="tl-tk">{tk}</span></div>'
            f'<div class="tl-logo">{ICON[tk]}</div><div class="tl-nm">{title.replace(" 기업분석","")}</div>'
            f'<div class="tl-px">{px} <span class="{c}">{ch}</span></div></a>')

# --------------- read pages ---------------
def side(active):
    return ""  # 사이드바는 shell()의 gside()가 모든 페이지에 공통으로 그린다

for i, r in enumerate(REPORTS):
    f, d, src, title, tk, comp, tag, sub, cols, line, url = r
    body = bullify(merged(src), d)
    body = re.sub(r'<img class="ch" src="%s/c_price\.png"[^>]*>' % re.escape(d), lambda m: cta_widget(tk, d), body)
    px, ch, c = PRICE[tk]
    prev = REPORTS[i - 1] if i > 0 else None; nxt = REPORTS[i + 1] if i < len(REPORTS) - 1 else None
    endnav = '<div class="endnav">' + (f'<a href="{prev[0]}">← {prev[3]}</a>' if prev else "<span></span>") + (f'<a href="{nxt[0]}">{nxt[3]} →</a>' if nxt else "<span></span>") + "</div>"
    inner = f"""<div class="readwrap">{side(f)}<div class="read">
<div class="rhead"><a href="index.html#reports">←</a><div><div class="t">{title}</div><div class="a">Corporate Analysis · 2026.11</div></div></div>
<div class="prembox"><div class="ic">{ICON[tk]}</div><div><div class="k">REPORT · {tag}</div>{sub} — 8개 분기 공시·컨퍼런스콜과 트레이딩뷰 데이터를 바탕으로 정리했습니다.</div></div>
<div class="stock"><div class="lg">{ICON[tk]}</div><div><div class="n">{comp} <small>({tk})</small></div><div class="s">{line}</div><div class="u">{url}</div></div><div class="p">{px}<small class="{c}">{ch}</small><small class="pbase">{_pbase(tk)}</small></div></div>
{target_box(tk)}{smart_box(tk)}{cta_box(tk)}{body}{endnav}</div></div>"""
    open(f"{OUT}/{f}", "w", encoding="utf-8").write(shell(title, inner, "reports", f))

# --------------- news page ---------------
try:
    _NEWS = json.load(open(os.path.join(ROOT, "data", "news.json"), encoding="utf-8"))
except (OSError, ValueError):
    _NEWS = {"asof": "", "items": {}}
_byl = {}
for _tk, _its in _NEWS.get("items", {}).items():
    for _x in _its:
        _e = _byl.setdefault(_x["l"].split("?")[0], dict(_x, k=[]))
        if _tk not in _e["k"]: _e["k"].append(_tk)
_NL = sorted(_byl.values(), key=lambda x: x["d"], reverse=True)
_nm = {r[4]: r[3].replace(" 기업분석", "") for r in REPORTS}
_lk = {r[4]: r[0] for r in REPORTS}
_nd = json.dumps({"n": [[x["t"], x["l"], x["d"], x["s"], x["src"], x["k"], x.get("tk", ""), x.get("sk", "")] for x in _NL], "nm": _nm, "lk": _lk, "asof": _NEWS.get("asof", "")}, ensure_ascii=False).replace("</", "<\\/")
_opts = "".join(f'<option value="{r[4]}">{r[3].replace(" 기업분석", "")} ({r[4]})</option>' for r in REPORTS)
NEWS_JS = """<script>(function(){var D=__DATA__,L=document.getElementById('nwl'),Q=document.getElementById('nwq'),S=document.getElementById('nws'),C=document.getElementById('nwc'),M=document.getElementById('nwm'),N=30,shown=N,cur=[];
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ago(iso){var m=Math.max(0,(Date.now()-new Date(iso).getTime())/60000);if(m<60)return Math.max(1,Math.round(m))+'분 전';if(m<1440)return Math.round(m/60)+'시간 전';if(m<10080)return Math.round(m/1440)+'일 전';return new Date(iso).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric'})}
function host(u){try{return new URL(u).hostname.replace(/^www\\./,'')}catch(e){return ''}}
function draw(){var q=(Q.value||'').trim().toLowerCase(),k=S.value;cur=D.n.filter(function(x){return(!k||x[5].indexOf(k)>=0)&&(!q||(x[0]+' '+x[6]+' '+x[3]+' '+x[7]+' '+x[5].map(function(t){return t+' '+(D.nm[t]||'')}).join(' ')).toLowerCase().indexOf(q)>=0)});
C.textContent=cur.length+'건';if(!cur.length){L.innerHTML='<div class="nwempty">표시할 뉴스가 없습니다.</div>';M.style.display='none';return}
L.innerHTML=cur.slice(0,shown).map(function(x){var tags=x[5].slice(0,6).map(function(t){return'<a class="tk" href="'+(D.lk[t]||'#')+'">'+esc(D.nm[t]||t)+'</a>'}).join('');
return'<li><a class="t" href="'+esc(x[1])+'" target="_blank" rel="noopener noreferrer">'+esc(x[6]||x[0])+'</a>'+((x[6]?x[7]:x[3])?'<div class="s">'+esc(x[6]?x[7]:x[3])+'</div>':'')+'<div class="m">'+tags+'<a class="tk" href="'+esc(x[1])+'" target="_blank" rel="noopener noreferrer">'+esc(host(x[1])||x[4])+' ↗</a><span>·</span><span title="'+esc(new Date(x[2]).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}))+'">'+ago(x[2])+'</span></div></li>'}).join('');
M.style.display=cur.length>shown?'':'none'}
Q.addEventListener('input',function(){shown=N;draw()});S.addEventListener('change',function(){shown=N;draw()});M.addEventListener('click',function(){shown+=N;draw()});draw();
var a=document.getElementById('nwa');if(a&&D.asof)a.textContent='마지막 수집 '+new Date(D.asof).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});})();</script>"""
news_inner = (f'<div class="readwrap">{side("news.html")}<div class="read"><div class="rhead"><a href="index.html">←</a><div><div class="t">뉴스</div><div class="a">등록된 {len(REPORTS)}개 기업 관련 최신 기사 · <span id="nwa"></span></div></div></div>'
    f'<div class="nwbar"><select id="nws"><option value="">전체 종목</option>{_opts}</select><input id="nwq" type="search" placeholder="종목·제목 검색"><span class="cnt" id="nwc"></span></div>'
    f'<ul class="nwl" id="nwl"></ul><button class="nwmore" id="nwm" type="button">더 보기</button>'
    f'<div class="nwnote">기사는 야후 파이낸스(삼성전자·SK하이닉스는 구글뉴스 포함)에서 자동 수집해 한국어로 번역한 제목·요약이며, 제목이나 출처 링크를 누르면 원문 사이트로 이동합니다. 번역은 기계 번역이라 정확한 내용은 원문을 확인하세요. 최근 30일 기사만 보관하고, 일부 기사는 종목과 직접 관련이 약할 수 있습니다.</div>'
    f'</div></div>' + NEWS_JS.replace("__DATA__", _nd))

# --------------- news detail drafts (in-site translated view + source reference) ---------------
NDD_CSS = """
.ndl{list-style:none;margin:0;padding:0}.ndl li{border-bottom:1px solid var(--line);padding:13px 2px;cursor:pointer}.ndl li:hover .t{text-decoration:underline}
.ndl .t{font-size:15px;font-weight:600;color:var(--ink);line-height:1.45}.ndl .s{font-size:13px;color:var(--muted);margin:4px 0 6px;line-height:1.5}
.ndl .m{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}.ndl .tk,.nda .tk{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:11.5px;color:var(--ink2);background:var(--card);text-decoration:none}
.ndsum{border:1px solid var(--line);border-left:4px solid var(--blue);background:var(--card);border-radius:10px;padding:13px 16px;margin:14px 0;font-size:15px;line-height:1.65}
.ndsum b.k{color:var(--blue);margin-right:4px}.ndsum mark{background:rgba(250,204,21,.28);color:inherit;padding:0 2px;border-radius:3px}
.ndbody{font-size:15px;line-height:1.8;color:var(--ink);margin:6px 0 4px}.ndbody small{display:block;color:var(--muted);font-size:12px;margin-top:6px}
.ndh{font-size:22px;font-weight:800;line-height:1.4;margin:6px 0 8px}.ndmeta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12.5px;color:var(--muted)}
.ndref{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:14px 16px;margin:18px 0 6px}.ndref .h{font-size:12px;color:var(--muted);margin-bottom:6px;font-weight:700}
.ndref .o{font-size:13.5px;color:var(--ink2);line-height:1.5;margin-bottom:10px}.ndref a.go{display:inline-block;background:var(--ink);color:var(--bg,#fff);border-radius:8px;padding:8px 16px;font-size:13.5px;font-weight:700;text-decoration:none}
.ndnote{font-size:11.5px;color:var(--muted);line-height:1.6;margin-top:10px}.ndback{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer;margin:4px 0 6px}
.ndmore{display:block;margin:16px auto 0;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:8px 22px;font:inherit;font-size:13px;cursor:pointer}
.ndbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 12px}.ndbar input,.ndbar select{font:inherit;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 10px}.ndbar input{flex:1;min-width:140px}
.ndhd{display:none}
.ndpanel{position:fixed;top:0;right:0;height:100%;width:min(520px,100%);background:var(--bg,#fff);border-left:1px solid var(--line);box-shadow:-8px 0 30px rgba(0,0,0,.18);z-index:60;transform:translateX(105%);transition:transform .22s;display:flex;flex-direction:column}
.ndpanel.on{transform:none}.ndpanel .ph{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--line)}.ndpanel .ph b{flex:1;font-size:13px;color:var(--muted)}
.ndpanel .pb{flex:1;overflow:auto;padding:4px 18px 18px}.ndpanel .pf{border-top:1px solid var(--line);padding:10px 14px;display:flex;gap:8px;align-items:center}.ndpanel .pf a.go{flex:1;text-align:center;background:var(--ink);color:var(--bg,#fff);border-radius:8px;padding:10px;font-weight:700;font-size:13.5px;text-decoration:none}
.ndpanel .pf button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:9px 12px;font:inherit;cursor:pointer}
.ndshade{position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:55;display:none}.ndshade.on{display:block}
@media(max-width:640px){.ndpanel{top:auto;bottom:0;height:86%;width:100%;border-left:0;border-top:1px solid var(--line);border-radius:16px 16px 0 0;transform:translateY(105%)}.ndh{font-size:19px}}
"""
CSS += NDD_CSS
NDD_JS = """<script>(function(){var D=__DATA__,MODE='__MODE__',L=document.getElementById('ndl'),Q=document.getElementById('ndq'),S=document.getElementById('nds'),C=document.getElementById('ndc'),M=document.getElementById('ndm'),LIST=document.getElementById('ndlist'),VIEW=document.getElementById('ndview'),N=30,shown=N,cur=[];
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ago(iso){var m=Math.max(0,(Date.now()-new Date(iso).getTime())/60000);if(m<60)return Math.max(1,Math.round(m))+'분 전';if(m<1440)return Math.round(m/60)+'시간 전';if(m<10080)return Math.round(m/1440)+'일 전';return new Date(iso).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric'})}
function host(u){try{return new URL(u).hostname.replace(/^www\\./,'')}catch(e){return ''}}
function hid(u){var h=5381,s=u.split('?')[0];for(var i=0;i<s.length;i++)h=((h<<5)+h+s.charCodeAt(i))>>>0;return h.toString(36)}
function hi(t){return esc(t).replace(/(\\$?[0-9][0-9,.]*\\s?(?:%|퍼센트|억|조|만|달러|원|배|명|분기)?)/g,function(m){return/[0-9]/.test(m)&&m.length>1?'<mark>'+m+'</mark>':m})}
function key(sk){var p=String(sk||'').split(/(?<=[.!?。])\\s+/).filter(Boolean);var s=p[0]||'';return s.length>130?s.slice(0,128)+'…':s}
function tags(x){return x[5].slice(0,6).map(function(t){return'<a class="tk" href="'+(D.lk[t]||'#')+'">'+esc(D.nm[t]||t)+'</a>'}).join('')}
function detail(x){var title=x[6]||x[0],body=x[6]?x[7]:x[3],k=key(body||title);
return'<div class="nda"><div class="ndmeta">'+tags(x)+'<span>·</span><span>'+esc(x[4])+'</span><span>·</span><span>'+new Date(x[2]).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})+' (KST)</span></div>'
+'<div class="ndh">'+esc(title)+'</div>'
+'<div class="ndsum"><b class="k">요약 :</b>'+hi(k)+'</div>'
+'<div class="ndbody">'+esc(body||'원문에서 제공된 본문 발췌가 없습니다.')+'<small>↑ 피드가 제공한 발췌문을 한국어로 번역한 내용입니다. 전체 기사는 아래 원문에서 확인하세요.</small></div>'
+'<div class="ndref"><div class="h">📎 원문 참조</div><div class="o">'+esc(x[0])+'<br><span style="color:var(--muted);font-size:12px">'+esc(x[4])+' · '+esc(host(x[1]))+'</span></div><a class="go" href="'+esc(x[1])+'" target="_blank" rel="noopener noreferrer">원문 사이트에서 읽기 ↗</a></div>'
+'<div class="ndnote">한국어 제목·요약은 기계 번역·자동 추출이며 오역이 있을 수 있습니다. 모든 저작권은 원문 발행처에 있습니다.</div></div>'}
function draw(){var q=(Q.value||'').trim().toLowerCase(),k=S.value;cur=D.n.filter(function(x){return(!k||x[5].indexOf(k)>=0)&&(!q||(x[0]+' '+x[6]+' '+x[3]+' '+x[7]+' '+x[5].map(function(t){return t+' '+(D.nm[t]||'')}).join(' ')).toLowerCase().indexOf(q)>=0)});
C.textContent=cur.length+'건';if(!cur.length){L.innerHTML='<div class="nwempty">표시할 뉴스가 없습니다.</div>';M.style.display='none';return}
L.innerHTML=cur.slice(0,shown).map(function(x,i){var b=x[6]?x[7]:x[3];return'<li data-h="'+hid(x[1])+'"><div class="t">'+esc(x[6]||x[0])+'</div>'+(b?'<div class="s">'+esc(b)+'</div>':'')+'<div class="m">'+tags(x)+'<span>'+esc(x[4])+'</span><span>·</span><span>'+ago(x[2])+'</span></div></li>'}).join('');M.style.display=cur.length>shown?'':'none'}
function find(h){for(var i=0;i<D.n.length;i++)if(hid(D.n[i][1])===h)return i;return -1}
var P=document.getElementById('ndpanel'),SH=document.getElementById('ndshade'),PB=P&&P.querySelector('.pb'),PG=P&&P.querySelector('a.go'),idx=-1;
function open(h,push){var i=find(h);if(i<0)return;idx=i;var x=D.n[i];
if(MODE==='a'){LIST.style.display='none';VIEW.style.display='';VIEW.innerHTML='<button class="ndback" type="button">← 목록으로</button>'+detail(x);window.scrollTo(0,0);VIEW.querySelector('.ndback').onclick=function(){history.back()}}
else{PB.innerHTML=detail(x);PG.href=x[1];P.classList.add('on');SH.classList.add('on');PB.scrollTop=0}
if(push)history.pushState({h:h},'','#'+h)}
function close(){if(MODE==='a'){VIEW.style.display='none';LIST.style.display='';VIEW.innerHTML=''}else{P.classList.remove('on');SH.classList.remove('on')}}
L.addEventListener('click',function(e){var li=e.target.closest('li');if(!li||e.target.closest('a'))return;open(li.getAttribute('data-h'),true)});
window.addEventListener('popstate',function(){var h=location.hash.slice(1);if(h)open(h,false);else close()});
if(MODE==='b'){SH.onclick=function(){history.back()};P.querySelector('.x').onclick=function(){history.back()};
P.querySelector('.pv').onclick=function(){if(idx>0)open(hid(D.n[idx-1][1]),false)};P.querySelector('.nx').onclick=function(){if(idx<D.n.length-1)open(hid(D.n[idx+1][1]),false)}}
Q.addEventListener('input',function(){shown=N;draw()});S.addEventListener('change',function(){shown=N;draw()});M.addEventListener('click',function(){shown+=N;draw()});draw();
if(location.hash.length>1)open(location.hash.slice(1),false);
var a=document.getElementById('nwa');if(a&&D.asof)a.textContent='마지막 수집 '+new Date(D.asof).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});})();</script>"""

def news_draft(kind):
    nm, ttl = "news.html", "뉴스"
    lk = ""
    panel = ('<div class="ndshade" id="ndshade"></div><div class="ndpanel" id="ndpanel"><div class="ph"><button class="ndback x" type="button">✕ 닫기</button><b>번역 뉴스</b><button class="ndback pv" type="button">↑ 이전</button><button class="ndback nx" type="button">↓ 다음</button></div>'
             '<div class="pb"></div><div class="pf"><a class="go" href="#" target="_blank" rel="noopener noreferrer">원문 사이트에서 읽기 ↗</a></div></div>') if kind == "b" else ""
    inner = (f'<div class="readwrap">{side(nm)}<div class="read"><div class="rhead"><a href="news.html">←</a><div><div class="t">뉴스</div><div class="a">등록된 {len(REPORTS)}개 기업 관련 최신 기사 · <span id="nwa"></span></div></div></div>{lk}'
             f'<div id="ndview" style="display:none"></div><div id="ndlist"><div class="ndbar"><select id="nds"><option value="">전체 종목</option>{_opts}</select><input id="ndq" type="search" placeholder="종목·제목 검색"><span class="cnt" id="ndc" style="margin-left:auto;font-size:12px;color:var(--muted)"></span></div>'
             f'<ul class="ndl" id="ndl"></ul><button class="ndmore" id="ndm" type="button">더 보기</button><div class="nwnote">기사는 야후 파이낸스(삼성전자·SK하이닉스는 구글뉴스 포함)에서 자동 수집해 한국어로 번역한 제목·요약입니다. 기사를 누르면 번역·요약을 보고, 하단의 원문 링크로 전체 기사를 읽을 수 있습니다. 번역은 기계 번역이라 정확한 내용은 원문을 확인하세요. 최근 30일 기사만 보관하고, 일부 기사는 종목과 직접 관련이 약할 수 있습니다.</div></div></div></div>{panel}'
             + NDD_JS.replace("__DATA__", _nd).replace("__MODE__", kind))
    open(f"{OUT}/{nm}", "w", encoding="utf-8").write(shell("뉴스 — " + ttl, inner, "news"))
news_draft("a")


# --------------- briefing page ---------------
try:
    _BR = json.load(open(os.path.join(ROOT, "data", "briefing.json"), encoding="utf-8")).get("b", [])
except (OSError, ValueError):
    _BR = []
_MK = {"label": M.get("label", ""), "asof": M.get("asof", ""), "snap": {k: SNAP[k] for k in ("NQ", "ES", "YM", "VIX", "DXY", "USDKRW", "US10Y", "CL", "GC") if k in SNAP},
       "fg": {k: FG.get(k) for k in ("score", "rating", "prev", "w", "m", "y")}}
try:
    _CB = json.load(open(os.path.join(ROOT, "data", "calendar.json"), encoding="utf-8"))
except (OSError, ValueError):
    _CB = {"econ": [], "earn": []}
_ECAL = {"earn": [{"day": e["day"], "tk": e["tk"], "time": e.get("time", "na"), "est": e.get("est", "")} for e in _CB.get("earn", []) if not e.get("eps")],
         "econ": [{"day": e["day"], "ts": e.get("ts", ""), "ko": e.get("ko") or e.get("name", ""), "imp": e.get("imp", 0), "allday": e.get("allday", False)} for e in _CB.get("econ", []) if e.get("imp", 0) >= 2]}
_bd = json.dumps({"b": _BR, "nm": _nm, "lk": _lk, "mk": _MK, "cal": _ECAL}, ensure_ascii=False).replace("</", "<\\/")
BR_JS = """<script>(function(){var D=__DATA__,K='pre',L=document.getElementById('brl'),SM=document.getElementById('brs'),SEL=document.getElementById('brd'),NX=document.getElementById('brn');
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function kst(iso){return new Date(iso).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})}
function host(u){try{return new URL(u).hostname.replace(/^www\\./,'')}catch(e){return ''}}
function etOff(d){var p=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',timeZoneName:'shortOffset'}).formatToParts(d).find(function(x){return x.type==='timeZoneName'}).value;var m=/GMT([+-]\\d+)/.exec(p);return m?+m[1]:-5}
function hh(m){m=((m%1440)+1440)%1440;return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')}
var o=etOff(new Date()),sh=(9-o)*60;NX.textContent='자동 생성 시각(현재 한국시간 기준): 장 시작 전 브리핑 '+hh(8*60+30+sh)+' (개장 1시간 전) · 장 마감 후 브리핑 '+hh(16*60+5+sh)+' (마감 직후). 서머타임 변경은 자동 반영됩니다.';
function list(){return D.b.filter(function(b){return b.kind===K})}
function fill(){var a=list();SEL.innerHTML=a.map(function(b,i){return'<option value="'+i+'">'+b.day+'</option>'}).join('');SEL.style.display=a.length>1?'':'none';draw()}
var CN=document.getElementById('brc');
function pc(v){return(v>=0?'+':'')+v.toFixed(2)+'%'}
function cc(v){return v>0?'u':(v<0?'d':'')}
function nextDay(day){var d=new Date(day+'T12:00:00Z');do{d=new Date(d.getTime()+86400000)}while(d.getUTCDay()===0||d.getUTCDay()===6);return d.toISOString().slice(0,10)}
function tm(ts){return new Date(ts).toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',hour12:false})}
function gauge(sc){var a=Math.PI*(1-sc/100),x=150+110*Math.cos(a),y=150-110*Math.sin(a),segs=[[0,25,'#ef4444'],[25,45,'#f59e0b'],[45,55,'#a3a3a3'],[55,75,'#84cc16'],[75,100,'#22c55e']],p='';
segs.forEach(function(g){var a0=Math.PI*(1-g[0]/100),a1=Math.PI*(1-g[1]/100);p+='<path d="M'+(150+120*Math.cos(a0))+','+(150-120*Math.sin(a0))+' A120,120 0 0 1 '+(150+120*Math.cos(a1))+','+(150-120*Math.sin(a1))+'" stroke="'+g[2]+'" stroke-width="16" fill="none" opacity=".9"/>'});
return'<svg viewBox="0 0 300 175" class="gg">'+p+'<line x1="150" y1="150" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'" stroke="#fff" stroke-width="4" stroke-linecap="round"/><circle cx="150" cy="150" r="8" fill="#fff"/></svg>'}
function deck(b){var M=D.mk,S=M.snap,C=[],n=b.items.length,nd=nextDay(b.day);
C.push('<div class="cd cv"><div class="ck">CORPORATE ANALYSIS</div><div class="cbig">장 마감 후<br>브리핑</div><div class="cdt">'+esc(b.day)+'</div><div class="cs">핵심 뉴스 '+n+'건 · 시장 요약 · 다음 거래일 일정</div><div class="cf">옆으로 넘겨 보세요 →</div></div>');
var T=[['NQ','나스닥100 선물'],['ES','S&P500 선물'],['YM','다우 선물'],['VIX','VIX 변동성'],['DXY','달러 인덱스'],['USDKRW','원/달러'],['US10Y','미 10년 금리'],['CL','WTI 유가'],['GC','금 선물']];
C.push('<div class="cd"><div class="ck">MARKET</div><div class="ct">지수·매크로 요약</div><div class="cm">미국장 마감 기준 · 갱신 '+kst(M.asof)+' (KST)</div><div class="tg3">'+T.filter(function(t){return S[t[0]]}).map(function(t){var v=S[t[0]];return'<div class="tl"><div class="tn">'+t[1]+'</div><div class="tp">'+v[0].toLocaleString('en-US',{maximumFractionDigits:2})+'</div><div class="tc '+cc(v[1])+'">'+pc(v[1])+'</div></div>'}).join('')+'</div><div class="cf">출처: Yahoo Finance · 선물·지수 기준 등락률</div></div>');
var F=M.fg;if(F&&F.score!=null)C.push('<div class="cd"><div class="ck">SENTIMENT</div><div class="ct">공포·탐욕 지수</div><div class="gw">'+gauge(F.score)+'<div class="gs2">'+Math.round(F.score)+'</div><div class="gr">'+esc(F.rating||'')+'</div></div><div class="gh"><div><span>전일</span><b>'+Math.round(F.prev)+'</b></div><div><span>1주 전</span><b>'+Math.round(F.w)+'</b></div><div><span>1개월 전</span><b>'+Math.round(F.m)+'</b></div><div><span>1년 전</span><b>'+Math.round(F.y)+'</b></div></div><div class="cf">출처: CNN Business Fear &amp; Greed</div></div>');
b.items.forEach(function(x,i){var tags=x.k.map(function(t){return'<a class="ctk" href="'+(D.lk[t]||'#')+'">'+esc(D.nm[t]||t)+'</a>'}).join('');
C.push('<div class="cd nw"><div class="ck">오늘의 소식 · '+(i+1)+'/'+n+'</div><span class="cl">'+esc(x.lab)+'</span><div class="nh">'+esc(x.ko)+'</div>'+(x.ks?'<div class="nsum"><b>요약 :</b> '+esc(x.ks)+'</div>':'')+(x.tr?'<div class="no">'+esc(x.t)+'</div>':'')+'<div class="ntg">'+tags+'</div><div class="nm2">'+esc(host(x.l))+' · '+kst(x.d)+'</div><a class="nb" href="'+esc(x.l)+'" target="_blank" rel="noopener noreferrer">원문 보기 ↗</a></div>')});
var er=D.cal.earn.filter(function(e){return e.day===nd}),ec=D.cal.econ.filter(function(e){return e.day===nd}).sort(function(a,b){return a.ts<b.ts?-1:1}).slice(0,8);
var gp=function(k,l){var a=er.filter(function(e){return e.time===k});return a.length?'<div class="eg"><span>'+l+'</span>'+a.map(function(e){return'<a class="ctk" href="'+(D.lk[e.tk]||'#')+'">'+esc(D.nm[e.tk]||e.tk)+'</a>'}).join('')+'</div>':''};
C.push('<div class="cd"><div class="ck">NEXT DAY</div><div class="ct">'+nd.slice(5,7)+'/'+nd.slice(8,10)+' 주요 일정</div><div class="cm">시간은 한국시간(KST)</div><div class="es">실적 발표(등록 기업)</div>'+(er.length?gp('pre','장 시작 전')+gp('post','장 마감 후')+gp('na','시각 미정'):'<div class="em">등록 기업 중 발표 예정 없음</div>')+'<div class="es">경제지표 ★★ 이상</div>'+(ec.length?ec.map(function(e){return'<div class="ei"><span>'+(e.allday?'종일':tm(e.ts))+'</span>'+esc(e.ko)+'<i>'+'★'.repeat(e.imp)+'</i></div>'}).join(''):'<div class="em">주요 지표 없음</div>')+'</div>');
C.push('<div class="cd cv"><div class="ck">NOTICE</div><div class="cs2">핵심 기사는 규칙으로 자동 선별했고, 한국어 제목·요약은 기계 번역입니다. 정확한 내용은 원문을 확인하세요.<br><br>투자 권유가 아니며 투자 판단과 책임은 본인에게 있습니다.</div><div class="cf">CORPORATE ANALYSIS</div></div>');
CN.innerHTML='<div class="cdk" id="cdk">'+C.join('')+'</div><div class="cnav"><button type="button" id="cpv" aria-label="이전">←</button><span id="cct"></span><button type="button" id="cnx" aria-label="다음">→</button></div>';
var K2=document.getElementById('cdk'),ct=document.getElementById('cct'),cards=K2.children;
function upd(){var w=K2.clientWidth||1,i=Math.round(K2.scrollLeft/w);ct.textContent=(i+1)+' / '+cards.length}
K2.addEventListener('scroll',function(){requestAnimationFrame(upd)});
document.getElementById('cpv').onclick=function(){K2.scrollBy({left:-K2.clientWidth,behavior:'smooth'})};document.getElementById('cnx').onclick=function(){K2.scrollBy({left:K2.clientWidth,behavior:'smooth'})};
K2.tabIndex=0;K2.addEventListener('keydown',function(e){if(e.key==='ArrowRight')document.getElementById('cnx').click();if(e.key==='ArrowLeft')document.getElementById('cpv').click()});upd()}
function draw(){var a=list(),b=a[+SEL.value||0];document.querySelectorAll('.brtab .pill').forEach(function(p){p.classList.toggle('on',p.dataset.k===K)});
if(!b){SM.style.display='';L.style.display='';CN.style.display='none';SM.innerHTML='아직 생성된 '+(K==='pre'?'장 시작 전':'장 마감 후')+' 브리핑이 없습니다. 위 시각에 자동으로 만들어집니다.';L.innerHTML='';return}
if(K==='post'){SM.style.display='none';L.style.display='none';CN.style.display='';deck(b);return}SM.style.display='';L.style.display='';CN.style.display='none';CN.innerHTML='';
SM.innerHTML=esc(b.summary)+'<span class="gn">'+esc(b.day)+' · '+kst(b.gen)+' 생성 · 영어 기사의 제목·요약은 기계 번역입니다</span>';
L.innerHTML=b.items.map(function(x){var tags=x.k.map(function(t){return'<a class="tk" href="'+(D.lk[t]||'#')+'">'+esc(D.nm[t]||t)+'</a>'}).join('');
return'<li><div><span class="lb">'+esc(x.lab)+'</span><a class="t" href="'+esc(x.l)+'" target="_blank" rel="noopener noreferrer">'+esc(x.ko)+'</a></div>'+(x.ks?'<div class="s">'+esc(x.ks)+'</div>':'')+(x.tr?'<div class="o">'+esc(x.t)+'</div>':'')+'<div class="m">'+tags+'<span>'+esc(host(x.l))+'</span><span>·</span><span>'+kst(x.d)+'</span></div></li>'}).join('')}
document.querySelectorAll('.brtab .pill').forEach(function(p){p.addEventListener('click',function(){K=p.dataset.k;fill()})});SEL.addEventListener('change',draw);
var l=D.b[0];if(l)K=l.kind;fill();})();</script>"""
br_inner = (f'<div class="readwrap">{side("briefing.html")}<div class="read"><div class="rhead"><a href="index.html">←</a><div><div class="t">뉴스 브리핑</div><div class="a">장 시작 1시간 전 · 장 마감 후 핵심 뉴스 {len(REPORTS)}개 기업 대상</div></div></div>'
    '<div class="brtab"><button class="pill on" data-k="pre" type="button">장 시작 전</button><button class="pill" data-k="post" type="button">장 마감 후</button><select id="brd" aria-label="날짜"></select></div>'
    '<div class="brsum" id="brs"></div><ol class="brl" id="brl"></ol><div id="brc" style="display:none"></div>'
    '<div class="nwnote" id="brn"></div><div class="nwnote">핵심 기사는 사람이 고르지 않고 규칙으로 자동 선별합니다. 종목 시가총액, 실적·인수합병·규제·경영진·애널리스트·급등락 같은 키워드, 출처 신뢰도, 여러 종목에 걸친 기사 여부로 점수를 매기고, 투자 권유성 기사와 중복 기사는 낮추거나 제외합니다. 한국어 문장은 번역이므로 정확한 내용은 원문을 확인하세요. 투자 조언이 아닙니다.</div>'
    '</div></div>' + BR_JS.replace("__DATA__", _bd))
open(f"{OUT}/briefing.html", "w", encoding="utf-8").write(shell("뉴스 브리핑 — Corporate Analysis", br_inner, "briefing"))

# --------------- calendar page ---------------
try:
    _CAL = json.load(open(os.path.join(ROOT, "data", "calendar.json"), encoding="utf-8"))
except (OSError, ValueError):
    _CAL = {"asof": "", "econ": [], "earn": []}
_cd = json.dumps({"econ": _CAL.get("econ", []), "earn": _CAL.get("earn", []), "asof": _CAL.get("asof", ""), "nm": _nm, "lk": _lk}, ensure_ascii=False).replace("</", "<\\/")
# --------------- calendar drafts (달력형 초안 A·B) ---------------
CALX_JS = """var D=__DATA__,S={tab:'earn',I:2},NOW=Date.now();
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
var KD=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}),KT=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}),ET=new Intl.DateTimeFormat('en-GB',{timeZone:'America/New_York',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}),WD=['일','월','화','수','목','금','토'];
function etOff(d){var p=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',timeZoneName:'shortOffset'}).formatToParts(d).find(function(x){return x.type==='timeZoneName'}).value,m=/GMT([+-]\\d+)/.exec(p);return m?+m[1]:-5}
function etMs(day,h,m){var p=day.split('-'),g=Date.UTC(+p[0],+p[1]-1,+p[2],h+5,m),o=etOff(new Date(g));return Date.UTC(+p[0],+p[1]-1,+p[2],h-o,m)}
function num(v){if(v==null)return NaN;var s=String(v).replace(/[,$%\\s()]/g,''),m=1,x=/([KMBT])$/i.exec(s);if(x){m={K:1e3,M:1e6,B:1e9,T:1e12}[x[1].toUpperCase()];s=s.slice(0,-1)}var n=parseFloat(s);return isNaN(n)?NaN:n*m}
function cmp(a,c){var x=num(a),y=num(c);if(isNaN(x)||isNaN(y))return'';var d=x-y;return Math.abs(d)<1e-9?'<span class="bg eq">예상 부합</span>':d>0?'<span class="bg up">예상 상회</span>':'<span class="bg dn">예상 하회</span>'}
var EV=[];D.econ.forEach(function(e){var ts=new Date(e.ts).getTime();EV.push({k:'econ',ts:ts,day:KD.format(ts),t:e.allday?'종일':KT.format(ts),et:e.allday?'':ET.format(ts),title:e.ko||e.name,en:e.name,imp:e.imp,a:e.a,c:e.c,p:e.p,done:e.a!==''})});
D.earn.forEach(function(e){var ts=e.time==='post'?etMs(e.day,16,0):etMs(e.day,9,30);var neg=/^\\(/.test(e.est||'');EV.push({k:'earn',ts:ts,day:KD.format(ts),t:e.time==='na'?'미정':KT.format(ts),pp:e.time,tk:e.tk,title:D.nm[e.tk]||e.tk,when:e.time==='pre'?'미국 장 시작 전 발표 (개장 '+KT.format(etMs(e.day,9,30))+' KST 이전)':e.time==='post'?'미국 장 마감 후 발표 ('+KT.format(etMs(e.day,16,0))+' KST 이후)':'발표 시간 미정',us:e.day,fq:e.fq,est:e.est,ly:e.ly,n:e.n,eps:e.eps,sur:e.sur,done:e.eps!==''})});
function cp(e){return e.tk?(D.cap[e.tk]||0):0}
EV.sort(function(a,b){return a.ts-b.ts||(b.imp||0)-(a.imp||0)||cp(b)-cp(a)});
var BYD={};EV.forEach(function(e){(BYD[e.day]=BYD[e.day]||[]).push(e)});
var TODAY=KD.format(new Date()),MINK=EV.length?EV[0].day:TODAY,MAXK=EV.length?EV[EV.length-1].day:TODAY;
function evs(day){return(BYD[day]||[]).filter(function(e){return e.k===S.tab&&(S.tab!=='econ'||e.imp>=S.I)})}
function card(e){var past=e.ts<NOW?' past':'';if(e.k==='econ'){return'<div class="wc i'+e.imp+past+'"><div class="wt"><span class="tm">'+esc(e.t)+'</span><span class="st">'+'★'.repeat(e.imp)+'</span><b>'+esc(e.title)+'</b></div><div class="en">'+esc(e.en)+(e.et?' · 미국 '+e.et+' ET':'')+'</div><div class="vals"><span>예상 <b>'+esc(e.c||'-')+'</b></span><span>이전 <b>'+esc(e.p||'-')+'</b></span><span>실제 <b>'+(e.done?esc(e.a):(e.ts<NOW?'집계 대기':'-'))+'</b></span>'+(e.done?cmp(e.a,e.c):'')+'</div></div>'}
var sr=e.sur!==''&&!isNaN(parseFloat(e.sur))?parseFloat(e.sur):null,res=e.done?(sr==null?cmp(e.eps,e.est):(sr>0?'<span class="bg up">상회 +'+sr.toFixed(1)+'%</span>':sr<0?'<span class="bg dn">하회 '+sr.toFixed(1)+'%</span>':'<span class="bg eq">부합</span>')):'';
return'<div class="wc e'+past+'"><div class="wt"><span class="tm '+(e.pp==='pre'?'pre':e.pp==='post'?'post':'na')+'">'+esc(e.t)+'</span><a href="'+esc(D.lk[e.tk]||'#')+'"><b>'+esc(e.title)+'</b></a><span class="en">'+esc(e.tk)+'</span></div><div class="en">'+esc(e.when)+' · 미국 현지 '+(+e.us.slice(5,7))+'/'+(+e.us.slice(8))+(e.fq?' · '+esc(e.fq)+' 분기':'')+'</div><div class="vals"><span>예상 EPS <b>'+esc(e.est||'-')+'</b></span><span>전년 <b>'+esc(e.ly||'-')+'</b></span><span>애널리스트 <b>'+esc(e.n||'-')+'</b></span>'+(e.done?'<span>실제 <b>'+esc(e.eps)+'</b></span>'+res:'')+'</div></div>'}
function lab(k){var p=k.split('-'),w=new Date(k+'T12:00:00+09:00').getDay();return +p[1]+'월 '+ +p[2]+'일 ('+WD[w]+')'}
function ctl(){return'<button class="'+(S.tab==='earn'?'on':'')+'" data-tab="earn">실적</button><button class="'+(S.tab==='econ'?'on':'')+'" data-tab="econ">경제지표</button>'}
function ictl(){return S.tab==='econ'?'<span class="grp"><button class="'+(S.I===3?'on':'')+'" data-imp="3">핵심 ★★★</button><button class="'+(S.I===2?'on':'')+'" data-imp="2">주요 ★★+</button><button class="'+(S.I===1?'on':'')+'" data-imp="1">전체</button></span>':''}
function wire(root,redraw){root.querySelectorAll('[data-tab]').forEach(function(b){b.onclick=function(){S.tab=b.dataset.tab;redraw()}});root.querySelectorAll('[data-imp]').forEach(function(b){b.onclick=function(){S.I=+b.dataset.imp;redraw()}})}
function range(){return'수집 범위 '+lab(MINK)+' ~ '+lab(MAXK)+' · 시간은 모두 한국시간(KST)입니다'}
"""
CALA_JS = """var C=document.getElementById('chd'),B=document.getElementById('cbody'),M=document.getElementById('cdm'),MB=document.getElementById('cdb'),t0=TODAY.split('-'),Y=+t0[0],Mo=+t0[1]-1;
function openDay(k){var l=evs(k);MB.innerHTML='<div class="hd"><b>'+lab(k)+'</b><button class="x" id="cdx" aria-label="닫기">×</button></div>'+(l.length?l.map(card).join(''):'<div class="en">이 날은 표시할 일정이 없습니다.</div>');M.classList.add('open');document.getElementById('cdx').onclick=function(){M.classList.remove('open')}}
M.addEventListener('click',function(e){if(e.target===M)M.classList.remove('open')});document.addEventListener('keydown',function(e){if(e.key==='Escape')M.classList.remove('open')});
function draw(){C.innerHTML='<button class="sq" id="pv" aria-label="이전 달">‹</button><span class="ttl">'+Y+'년 '+(Mo+1)+'월</span><button class="sq" id="nx" aria-label="다음 달">›</button><button id="tdy">오늘</button><span class="grp">'+ctl()+'</span><span class="sp"></span>'+ictl();
document.getElementById('pv').onclick=function(){Mo--;if(Mo<0){Mo=11;Y--}draw()};document.getElementById('nx').onclick=function(){Mo++;if(Mo>11){Mo=0;Y++}draw()};document.getElementById('tdy').onclick=function(){Y=+t0[0];Mo=+t0[1]-1;draw()};wire(C,draw);
var first=new Date(Date.UTC(Y,Mo,1)),dim=new Date(Date.UTC(Y,Mo+1,0)).getUTCDate(),off=(first.getUTCDay()+6)%7,rows=Math.ceil((off+dim)/7),h='',N=4;
['월','화','수','목','금','토','일'].forEach(function(w){h+='<div class="wh">'+w+'</div>'});
for(var i=0;i<rows*7;i++){var d=i-off+1;if(d<1||d>dim){h+='<div class="dc out"></div>';continue}var k=Y+'-'+String(Mo+1).padStart(2,'0')+'-'+String(d).padStart(2,'0'),l=evs(k);
h+='<div class="dc'+(i%7>4?' we':'')+(k===TODAY?' td':'')+'" data-k="'+k+'"><div class="dn">'+d+'</div>';
l.slice(0,N).forEach(function(e){if(e.k==='econ')h+='<div class="cbar i'+e.imp+(e.ts<NOW?' past':'')+'"><span class="tm">'+esc(e.t)+'</span><b>'+esc(e.title)+'</b></div>';else h+='<div class="cbar e'+(e.ts<NOW?' past':'')+'"><span class="tm '+(e.pp==='pre'?'pre':e.pp==='post'?'post':'na')+'">'+esc(e.t)+'</span><b>'+esc(e.tk)+'</b></div>'});
if(l.length>N)h+='<button class="more" type="button">+'+(l.length-N)+'개</button>';if(l.length)h+='<span class="cn">'+l.length+'</span>';h+='</div>'}
B.innerHTML='<div class="cdh">'+range()+' · 날짜를 누르면 상세가 열립니다</div><div class="mg">'+h+'</div>';B.querySelectorAll('.dc[data-k]').forEach(function(c){c.onclick=function(){openDay(c.dataset.k)}})}
draw();"""
def cal_page():
    nm, js, ttl = "calendar.html", CALA_JS, "일정"
    data = json.dumps({"econ": _CAL.get("econ", []), "earn": _CAL.get("earn", []), "nm": _nm, "lk": _lk, "cap": _CAP}, ensure_ascii=False).replace("</", "<\\/")
    inner = (f'<div class="calw"><div class="cph"><span class="t">{ttl}</span><span class="a">미국 경제지표와 등록 기업 실적 · 시간은 한국시간(KST)</span></div><div class="chd" id="chd"></div><div id="cbody"></div>'
             '<div class="nwnote">실적 시각 표기: 미국 장 시작 전 발표는 개장 시각(KST) 기준 "전", 장 마감 후 발표는 마감 시각(KST) 기준 "후"로 표시하며 실제 발표 시각과 다를 수 있습니다(시간 미정은 "미정"). 경제지표는 발표 시각을 한국시간으로 환산했습니다. 데이터 출처: Nasdaq. 실적은 이 사이트에 등록된 미국 상장 기업만 보여줍니다.</div></div>'
             '<div class="cdm" id="cdm"><div class="cdb" id="cdb"></div></div>'
             '<script>(function(){' + CALX_JS.replace("__DATA__", data) + js + '})();</script>')
    open(f"{OUT}/{nm}", "w", encoding="utf-8").write(shell("일정 — " + ttl, inner, "calendar"))
cal_page()

# --------------- 옵션 탭 ---------------
OPT_CSS = """
.opw{max-width:1100px}.oph{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:6px}.oph .t{font-size:22px;font-weight:800}.oph .a{font-size:12.5px;color:var(--muted)}
.opseg{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.opseg button{border:1px solid var(--line);background:var(--card,transparent);color:var(--text,inherit);padding:7px 12px;border-radius:999px;font-size:13px;font-weight:700;cursor:pointer}.opseg button.on{background:var(--brand,#2563eb);border-color:var(--brand,#2563eb);color:#fff}
.opleg{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:12.5px;line-height:1.65;color:var(--muted);margin-bottom:10px}.opleg b{color:var(--text,inherit)}
.opv{display:none}.opv.on{display:block}.optw{overflow-x:auto}.opt{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}.opt th{text-align:right;color:var(--muted);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line);position:sticky;top:0}.opt th:first-child,.opt td:first-child{text-align:left}
.opt td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--line)}.opt td a{color:inherit;font-weight:700;text-decoration:none}.opt .s{display:block;font-size:11px;color:var(--muted);font-weight:500}
.opt a.bn{display:flex;align-items:center;gap:10px;text-align:left}.opt .bl0{width:28px;height:28px;border-radius:50%;overflow:hidden;flex:none;background:var(--soft);display:flex;align-items:center;justify-content:center}.opt .bl0 .mono{font-size:9px}.opt .bl0 img{width:100%;height:100%;object-fit:cover}.opq{width:100%;max-width:320px;padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card,transparent);color:inherit;font-size:14px;margin:0 0 10px}.opx{display:none;color:var(--muted);font-size:13px;padding:10px 2px}
.opt .up{color:var(--up);font-weight:700}.opt .down{color:var(--down);font-weight:700}.opt .mu{color:var(--muted)}
.rb{position:relative;display:inline-block;width:120px;height:8px;border-radius:4px;background:var(--line);vertical-align:middle}.rb i{position:absolute;top:0;bottom:0;background:#93c5fd;border-radius:4px}.rb u{position:absolute;top:-3px;width:2px;height:14px;background:var(--text,#111);text-decoration:none}
.tg{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:700}.tg.p{background:rgba(22,163,74,.14);color:#16a34a}.tg.n{background:rgba(220,38,38,.14);color:#dc2626}
.opn{font-size:11.5px;color:var(--muted);line-height:1.6;margin-top:10px}
"""
def options_page():
    try:
        O = json.load(open(os.path.join(ROOT, "data", "options.json"), encoding="utf-8"))
    except (OSError, ValueError):
        O = {"asof": "", "t": {}}
    T = O.get("t", {})
    def nm(r):
        sx = (r[4] + " " + r[3].replace(" 기업분석", "") + " " + r[5] + " " + KO_ALIAS.get(r[4], "")).lower().replace('"', "")
        return f'<a class="bn" href="{r[0]}"><span class="bl0">{ICON[r[4]]}</span><span><b>{r[3].replace(" 기업분석", "")}</b><span class="s">{r[4]}</span></span></a><span class="hs" hidden>{sx}</span>'
    def pct(a, b): return (a / b - 1) * 100
    r1, r2, r3 = [], [], []
    for r in REPORTS:
        tk = r[4]; o = T.get(tk)
        if not o: continue
        px = o["px"]
        if "lo" in o:
            span = (o["hi"] - o["lo"]) * 2 or 1; l0 = o["lo"] - (o["hi"] - o["lo"]) / 2
            bar = f'<span class="rb"><i style="left:25%;width:50%"></i><u style="left:50%"></u></span>'
            src = "옵션 IV" if o.get("src") == "iv" else "과거 변동성"
            r1.append(f'<tr><td>{nm(r)}</td><td>${px:,.2f}</td><td class="down">${o["lo"]:,.2f}</td><td class="up">${o["hi"]:,.2f}</td><td><b>±{o["sgp"]:.2f}%</b><span class="s">±${o["sg"]:,.2f}</span></td><td>{bar}</td><td>{o["iv5"] * 100:.1f}%<span class="s">{src}</span></td><td>{(o.get("hv20") or 0) * 100:.1f}%</td></tr>' if o.get("hv20") else
                      f'<tr><td>{nm(r)}</td><td>${px:,.2f}</td><td class="down">${o["lo"]:,.2f}</td><td class="up">${o["hi"]:,.2f}</td><td><b>±{o["sgp"]:.2f}%</b><span class="s">±${o["sg"]:,.2f}</span></td><td>{bar}</td><td>{o["iv5"] * 100:.1f}%<span class="s">{src}</span></td><td class="mu">-</td></tr>')
        e = o.get("er")
        if e and e.get("mvp") is not None:
            prem = f'{e["iv"] / e["ivb"]:.2f}배' if e.get("iv") and e.get("ivb") else "-"
            tm = {"pre": "장 시작 전", "post": "장 마감 후", "bmo": "장 시작 전", "amc": "장 마감 후"}.get(e.get("t"), "시각 미정")
            r2.append((e["d"], f'<tr><td>{nm(r)}</td><td>{e["d"][5:7]}/{e["d"][8:10]}<span class="s">{tm}</span></td><td><b>±{e["mvp"]:.1f}%</b><span class="s">±${e["mv"]:,.2f}</span></td><td>${px * (1 - e["mvp"] / 100):,.2f} ~ ${px * (1 + e["mvp"] / 100):,.2f}</td><td>{(f"{e[chr(105)+chr(118)] * 100:.1f}%" if e.get("iv") else "-")}<span class="s">만기 {e["e"][5:]}</span></td><td>{(f"{e[chr(105)+chr(118)+chr(98)] * 100:.1f}%" if e.get("ivb") else "-")}</td><td>{prem}</td></tr>'))
        if "pw" in o or "cw" in o or o.get("gf"):
            def lv(k):
                return f'${k:,.2f}<span class="s">{pct(k, px):+.1f}%</span>' if k else "-"
            gf = o.get("gf"); reg = o.get("gr", 0)
            tag = '<span class="tg p">양(+) 감마 · 변동성 억제</span>' if reg > 0 else ('<span class="tg n">음(-) 감마 · 변동성 확대</span>' if reg < 0 else "-")
            r3.append(f'<tr><td>{nm(r)}</td><td>${px:,.2f}</td><td class="down">{lv(o.get("pw"))}</td><td class="up">{lv(o.get("cw"))}</td><td>{lv(gf) if gf else "<span class=mu>구간 내 없음</span>"}</td><td>{tag}</td><td>{o.get("pcr", "-")}</td></tr>')
    r2.sort(key=lambda x: x[0]); r2 = [x[1] for x in r2]
    def tbl(h, rows, empty):
        return (f'<div class="optw"><table class="opt"><tr>{h}</tr>' + "".join(rows) + '</table></div>') if rows else f'<div class="opleg">{empty}</div>'
    v1 = tbl("<th>기업</th><th>현재가</th><th>하단(-1σ)</th><th>상단(+1σ)</th><th>변동폭</th><th>범위</th><th>사용 변동성(연)</th><th>HV20</th>", r1, "옵션 데이터가 아직 수집되지 않았습니다. 다음 아침 갱신 후 표시됩니다.")
    v2 = tbl("<th>기업</th><th>실적일</th><th>옵션 기대 변동폭</th><th>기대 가격대</th><th>실적 만기 IV</th><th>평상시 IV</th><th>IV 배율</th>", r2, "발표 예정일이 잡힌 종목의 옵션 데이터가 아직 없습니다.")
    v3 = tbl("<th>기업</th><th>현재가</th><th>풋월(지지)</th><th>콜월(저항)</th><th>감마 플립</th><th>현재 감마 구간</th><th>풋/콜 비율</th>", r3, "미결제약정 데이터가 아직 수집되지 않았습니다.")
    legs = [
        "<b>5거래일 1σ</b> — 앞으로 5거래일 뒤 주가가 이 범위 안에 있을 확률이 약 68%라는 뜻입니다. 현재가 × 옵션 IV(만기가 5일 이상 남은 첫 만기의 ATM 내재변동성) × √(5/252)로 계산하고, 옵션이 없으면 과거 20일 변동성(HV20)을 씁니다.",
        "<b>실적발표 내재변동성</b> — 다음 실적 발표를 지나는 첫 만기의 ATM 스트래들(콜+풋) 가격 ÷ 현재가가 시장이 예상하는 발표 후 변동폭입니다. IV 배율은 그 만기 IV ÷ 실적 이후 평상시 IV로, 클수록 발표 이벤트 프리미엄이 큽니다.",
        "<b>풋월·콜월·감마 플립</b> — 45일 이내 만기의 미결제약정(OI)이 가장 많이 쌓인 행사가입니다. 풋월은 현재가 아래(지지로 작용하기 쉬움), 콜월은 위(저항)에서 찾고, 감마 플립은 딜러 순감마가 0이 되는 가격입니다. 현재가가 플립 위면 양 감마(헤지가 변동성을 눌러 줌), 아래면 음 감마(변동성 확대)로 봅니다.",
    ]
    names = ["5거래일 1σ", "실적발표 내재변동성", "풋월 · 콜월 · 감마 플립"]
    seg = "".join(f'<button type="button" class="{"on" if i == 0 else ""}" data-v="{i}">{n}</button>' for i, n in enumerate(names))
    body = "".join(f'<div class="opv{" on" if i == 0 else ""}" data-v="{i}"><div class="opleg">{legs[i]}</div>{v}</div>' for i, v in enumerate((v1, v2, v3)))
    note = ('<div class="opn">데이터: Yahoo Finance 옵션 체인(지연 시세), 매일 아침 갱신. 미결제약정은 전일 기준이며, 감마 플립은 "콜은 딜러가 팔고 풋은 산다"는 통상 가정으로 추정한 값이라 실제 딜러 포지션과 다를 수 있습니다. 옵션이 없는 종목·한국 종목은 표시되지 않습니다. 투자 권유가 아닙니다.</div>')
    js = ("<script>(function(){var b=document.querySelectorAll('.opseg button'),v=document.querySelectorAll('.opv');b.forEach(function(x){x.onclick=function(){b.forEach(function(y){y.classList.toggle('on',y===x)});v.forEach(function(y){y.classList.toggle('on',y.dataset.v===x.dataset.v)})}});var q=document.getElementById('opq'),nx=document.getElementById('opx');q.addEventListener('input',function(){var t=q.value.trim().toLowerCase(),shown=0;document.querySelectorAll('.opt tr').forEach(function(r,i){var h=r.querySelector('.hs');if(!h)return;var ok=!t||h.textContent.indexOf(t)>-1;r.style.display=ok?'':'none';if(ok&&r.closest('.opv.on'))shown++});nx.style.display=(t&&!shown)?'block':'none'});b.forEach(function(x){x.addEventListener('click',function(){q.dispatchEvent(new Event('input'))})})})();</script>")
    inner = (f'<style>{OPT_CSS}</style><div class="opw"><div class="oph"><span class="t">옵션</span><span class="a">등록 기업 옵션 지표 · 갱신 {O.get("asof") or "수집 전"} (KST)</span></div><div class="opseg">{seg}</div><input class="opq" id="opq" type="search" placeholder="기업 검색 (이름·티커·한글)" autocomplete="off" aria-label="옵션 기업 검색"><div class="opx" id="opx">검색 결과가 없습니다.</div>{body}{note}</div>{js}')
    open(f"{OUT}/options.html", "w", encoding="utf-8").write(shell("옵션 — 5거래일 1σ · 실적 내재변동성 · 풋월/콜월/감마 플립", inner, "options"))
options_page()

# --------------- 13F 탭: 등록 기업이 제출한 13F(타사 주식 보유 현황) ---------------
F13_CSS = """
.fw{max-width:1100px}.fh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:6px}.fh .t{font-size:22px;font-weight:800}.fh .a{font-size:12.5px;color:var(--muted)}
.fq{width:100%;max-width:420px;box-sizing:border-box;margin:10px 0;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card,transparent);color:inherit;font-size:14px}
.fl{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:12.5px;line-height:1.65;color:var(--muted);margin-bottom:10px}.fl b{color:var(--text,inherit)}
.fc{border:1px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden}.fc>summary{display:flex;align-items:center;gap:12px;padding:12px 14px;cursor:pointer;list-style:none}.fc>summary::-webkit-details-marker{display:none}
.fc .lg{width:34px;height:34px;border-radius:50%;overflow:hidden;flex:none;background:var(--soft);display:flex;align-items:center;justify-content:center}.fc .lg .mono{font-size:10px}
.fc .nm{font-weight:800;font-size:15px}.fc .sb{font-size:12px;color:var(--muted);font-weight:500}.fc .tt{margin-left:auto;text-align:right;font-weight:800}.fc .tt span{display:block;font-size:11.5px;color:var(--muted);font-weight:500}
.fb{padding:0 14px 12px}.ft{overflow-x:auto}.ftb{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}.ftb th{text-align:right;color:var(--muted);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line)}.ftb td{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line)}.ftb th:first-child,.ftb td:first-child{text-align:left}
.ftb td a{color:inherit;font-weight:700}.ftb .s{display:block;font-size:11px;color:var(--muted);font-weight:500}.ftb .up{color:var(--up);font-weight:700}.ftb .down{color:var(--down);font-weight:700}.ftb .new{color:#2563eb;font-weight:700}.ftb .mu{color:var(--muted)}
.fs{font-size:12.5px;color:var(--muted);margin-top:10px;line-height:1.7}.fs b{color:var(--text,inherit)}
"""
CSS += F13_CSS
def f13_page():
    try:
        O = json.load(open(os.path.join(ROOT, "data", "corp13f.json"), encoding="utf-8"))
    except (OSError, ValueError):
        O = {"asof": "", "c": {}}
    C = O.get("c", {})
    byk = {r[4]: r for r in REPORTS}
    def money(v):
        return f"${v / 1e9:,.2f}B" if v >= 1e9 else f"${v / 1e6:,.1f}M"
    def nmcell(x):
        lab = x["nm"].title() if x["nm"].isupper() else x["nm"]
        if x.get("tk") and x["tk"] in byk:
            return f'<a href="{byk[x["tk"]][0]}">{lab}</a><span class="s">{x["tk"]}</span>'
        return f'{lab}<span class="s">{x.get("cls", "")}</span>'
    cards = []
    _lim = (dt.date.today() - dt.timedelta(days=400)).isoformat()  # 마지막 13F가 1년 넘게 지난(제출 중단) 회사는 제외
    order = [r[4] for r in REPORTS if r[4] in C and C[r[4]]["period"] >= _lim]
    for tk in order:
        c = C[tk]; r = byk[tk]
        rows = ""
        for x in c["rows"]:
            if x["ch"] == "new": chs = '<span class="new">신규</span>'
            elif x["ch"] == "same": chs = '<span class="mu">변동 없음</span>'
            else:
                chs = f'<span class="{"up" if x["ch"] == "up" else "down"}">{"확대" if x["ch"] == "up" else "축소"} {x["chp"]:+.0f}%</span>' if x.get("chp") is not None else "-"
            rows += f'<tr><td>{nmcell(x)}</td><td>{x["sh"]:,}</td><td>{money(x["v"])}</td><td>{x["w"]:.2f}%</td><td>{chs}</td></tr>'
        sold = ""
        if c.get("sold"):
            sold = '<div class="fs"><b>직전 분기 대비 전량 매도</b>: ' + ", ".join(f'{(x["nm"].title() if x["nm"].isupper() else x["nm"])}({money(x["v"])})' for x in c["sold"]) + "</div>"
        hs = " ".join([tk, r[3], r[5], KO_ALIAS.get(tk, ""), c["name"]] + [x["nm"] for x in c["rows"]]).lower().replace('"', "")
        nm = r[3].replace(" 기업분석", "")
        cards.append(f'<details class="fc" data-s="{hs}"><summary><span class="lg">{ICON[tk]}</span><span><div class="nm"><a href="{r[0]}" style="color:inherit;text-decoration:none">{nm}</a> <span class="sb">{tk}</span></div><div class="sb">{c["period"]} 기준 · 접수 {c["filed"]} · 보유 {c["n"]:,}종목</div></span><span class="tt">{money(c["total"])}<span>13F 보고 총액</span></span></summary>'
                     f'<div class="fb"><div class="ft"><table class="ftb"><tr><th>보유 종목 (상위 {len(c["rows"])})</th><th>보유 주식 수</th><th>평가금액</th><th>포트폴리오 비중</th><th>직전 분기 대비</th></tr>{rows}</table></div>{sold}</div></details>')
    body = "".join(cards) or '<div class="fl">13F를 제출하는 등록 기업 데이터가 아직 수집되지 않았습니다. 수집 후 표시됩니다.</div>'
    leg = ('<div class="fl"><b>13F 보유 현황</b> — 등록 기업 중 SEC에 13F-HR(기관투자자 주식 보유 보고서)을 제출하는 회사가 분기 말에 보유한 <b>타사 주식</b>입니다. 평가금액 기준 상위 30종목을 보여 주고, 직전 분기와 주식 수를 비교해 신규·확대·축소·전량 매도를 표시합니다. '
           '13F는 미국 상장 주식 롱 포지션만 담고(옵션·채권·공매도·해외 주식 제외), 분기 종료 후 45일 안에 공시돼 시차가 있습니다. 비중은 13F에 보고된 포트폴리오 대비입니다.</div>')
    inner = (f'<div class="fw"><div class="fh"><span class="t">13F</span><span class="a">등록 기업의 타사 주식 보유 현황 · {len(cards)}개 기업 · 갱신 {O.get("asof") or "수집 전"} (KST)</span></div>{leg}'
             '<input class="fq" id="fq" type="search" placeholder="회사·보유 종목 검색 (예: 엔비디아, CoreWeave)" autocomplete="off">' + body +
             "</div><script>(function(){var q=document.getElementById('fq');if(!q)return;q.addEventListener('input',function(){var v=q.value.trim().toLowerCase();document.querySelectorAll('.fc').forEach(function(d){d.style.display=(!v||d.dataset.s.indexOf(v)>=0)?'':'none'})})})();</script>")
    open(f"{OUT}/f13.html", "w", encoding="utf-8").write(shell("13F — 등록 기업의 타사 주식 보유 현황", inner, "f13"))
f13_page()

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
    return (f'<div class="panel fut live" data-k="{k}"><div class="fhd"><div class="nm">{name} · 실시간 <span class="lv">LIVE</span></div><div class="ivs">{pills}</div></div>'
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
            '<label>기간 <select id="hmp"><option value="1d">1일</option><option value="1w">1주</option><option value="1m">1개월</option><option value="3m">3개월</option><option value="6m">6개월</option><option value="ytd">연초 대비</option><option value="1y">1년</option></select></label>'
            '<label>크기 <select id="hmz"><option value="cap">시가총액</option><option value="eq">동일</option></select></label>'
            '<label class="hmck"><input type="checkbox" id="hmlogo"> 로고</label>'
            '<span class="hmvw"><button class="pill on" data-v="map" type="button">히트맵</button><button class="pill" data-v="list" type="button">목록</button></span></div>'
            '<div id="hmbox" class="hmbox"></div><div id="hmlist" class="hmlist" hidden></div>'
            '<div class="hmfoot"><span id="hmnote">색은 오늘의 등락률(%)입니다.</span><span class="hmlg" id="hmlg"></span></div>'
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
<div class="sech"><h2>미국 지수 선물</h2></div>
<div class="grid3">{fut("NQ","나스닥100 선물","NQ1!")}{fut("ES","S&P500 선물","ES1!")}{fut("YM","다우존스 선물","YM1!")}</div>

<div class="sech" id="heatmap"><h2>S&amp;P500 히트맵</h2></div>
{heatmap()}

<div class="sech"><h2>CNN 공포·탐욕 지수</h2></div>
<div class="panel fgwrap">
<div><div class="cnst" id="cnst">CNBC 시세 · 확인 중</div>{gauge(FG["score"])}<div class="fgnum" id="fgnum"><b style="color:{bcol(FG["score"])}">{FG["score"]:.0f}</b><div style="color:{bcol(FG["score"])}">{FG["rating"]}</div></div>
<div style="margin-top:10px" id="fgspk">{spark(FG["hist"], 260, 46, bcol(FG["score"]))}</div><div class="note" style="text-align:center;margin-top:2px">최근 약 3.5개월 추이</div></div>
<table class="hist" id="fghist" style="width:100%;border-collapse:collapse"><tr><td colspan="3" style="font-weight:700;color:var(--ink)">시점별 비교</td></tr>{hist_rows}</table>
<table class="comp" id="fgcomp" style="width:100%;border-collapse:collapse"><tr><td colspan="3" style="font-weight:700;color:var(--ink)">7개 구성 지표</td></tr>{comp_rows}</table>
</div>

<div class="sech"><h2>변동성 · 달러 · 환율 · 원자재</h2></div>
<div class="tiles">{"".join(tile_any(n, y) for n, y in MACRO_LIVE)}</div>
<div class="note oneline"><b>한 줄 해석</b> · {ONE_LINE} <span style="opacity:.7">(전일 종가 기준)</span></div>

<div class="sech"><h2>국채 금리</h2></div>
<div class="tiles">{"".join(tile_any(n, y) for n, y in RATE_LIVE)}</div>

<div class="note">데이터: Yahoo Finance(선물·지수·환율·원자재), 미국 재무부·일본 재무성(국채 금리), CNN Business(공포·탐욕 지수). 매일 미국장 마감 후(06:30 KST)와 한국장 마감 후(16:00 KST) 자동 갱신됩니다. 선물·히트맵·변동성·환율·원자재·국채 금리 칸과 기업별 차트는 트레이딩뷰 위젯으로 장중에 실시간(일부 지연) 반영됩니다.</div>
</section>

<section id="cta">
<div class="sech"><h2 id="sch2">CTA 스코어보드</h2><span class="sm" id="schs"></span></div>
<div class="stabs"><button class="stab on" data-t="cta" type="button">CTA 스코어보드</button><button class="stab" data-t="peg" type="button">PEG 스코어보드</button></div>
<div id="pane-cta">
{cta_board()}
<div class="note">점수 +1은 8개 신호가 모두 매수, -1은 모두 매도입니다. 추세추종(CTA) 자금의 움직임을 흉내 낸 자체 계산 모델이며, 실제 증권사 CTA 포지션 데이터가 아닙니다.</div>
</div>
<div id="pane-peg" hidden>
{peg_board()}
<div class="note">PEG = PER ÷ EPS 성장률. 낮은 순서로 정렬했고, 값은 각 기업 보고서의 동종업계 비교표(트레이딩뷰 TTM, 11/6 종가 환산)에서 가져옵니다. 판정: 0.5 이하 적극 매수권, 1.0 이하 투자 적격, 초과는 기준 초과. 적자 등으로 PEG가 없는 종목은 맨 아래에 둡니다. 비고란에 "의미 제한적"이라고 적힌 종목은 성장률 기저 착시 등으로 PEG 숫자만 보고 판단하기 어렵습니다. 종가는 1분마다 갱신됩니다(미국 종목).</div>
</div>
</section>

<section id="reports">
<div class="sech"><h2>기업분석</h2></div>
<div class="bsw"><input id="bsq" type="search" placeholder="기업명·티커 검색 (예: 엔비디아, NVDA)" autocomplete="off"><span id="bsn"></span></div><div class="pills">{PILLS}</div>
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
(function(){{const B=document.getElementById('pegboard'),P=document.getElementById('pegpager');if(!B)return;const rows=[...B.querySelectorAll('tbody tr')],N=10,pages=Math.ceil(rows.length/N);rows.forEach((r,k)=>r.firstChild.textContent=k+1);
function show(i){{rows.forEach((r,k)=>r.style.display=(k>=i*N&&k<(i+1)*N)?'':'none');if(pages<2){{P.innerHTML='';return;}}
let h='<button data-p="'+(i-1)+'"'+(i===0?' disabled':'')+'>‹</button>';for(let k=0;k<pages;k++)h+='<button data-p="'+k+'" class="'+(k===i?'on':'')+'">'+(k+1)+'</button>';
h+='<button data-p="'+(i+1)+'"'+(i===pages-1?' disabled':'')+'>›</button><span class="pi">'+(i*N+1)+'–'+Math.min((i+1)*N,rows.length)+' / '+rows.length+'개</span>';P.innerHTML=h;}}
P.addEventListener('click',e=>{{const b=e.target.closest('button');if(b&&!b.disabled)show(+b.dataset.p);}});show(0);
const R=rows.filter(r=>r.dataset.q),U='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols='+R.map(r=>encodeURIComponent(r.dataset.q)).join('|');
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,'')),fmt=v=>v<1000?'$'+v.toFixed(2):'$'+Math.round(v).toLocaleString('en-US');
async function upd(){{try{{const j=await (await fetch(U,{{cache:'no-store'}})).json();const Q={{}};[].concat(j.FormattedQuoteResult.FormattedQuote||[]).forEach(q=>Q[q.symbol]=q);
R.forEach(r=>{{const q=Q[r.dataset.q];if(!q||q.last==null)return;let L=num(q.last),C=num(q.change_pct);const e=q.ExtendedMktQuote;if(q.curmktstatus!=='REG_MKT'&&e&&e.last&&!/PREV/.test(e.type||'')){{L=num(e.last);C=num(e.change_pct);}}
if(isNaN(L))return;if(isNaN(C)){{const pv=num(q.previous_day_closing);C=pv?(L-pv)/pv*100:0;}}r.children[2].innerHTML=fmt(L)+'<br><span class="'+(C>0?'up':C<0?'down':'')+'">'+(C>=0?'+':'')+C.toFixed(2)+'%</span>';}});}}catch(e){{}}}}
upd();setInterval(()=>{{if(!document.hidden)upd();}},60000);}})();
(function(){{const tb=document.querySelectorAll('.stab'),H=document.getElementById('sch2'),S=document.getElementById('schs'),pc=document.getElementById('pane-cta'),pp=document.getElementById('pane-peg');
const T={{cta:['CTA 스코어보드',S.textContent],peg:['PEG 스코어보드','']}};
function set(t){{tb.forEach(b=>b.classList.toggle('on',b.dataset.t===t));pc.hidden=t!=='cta';pp.hidden=t!=='peg';H.textContent=T[t][0];S.textContent=T[t][1];try{{localStorage.setItem('scTab',t)}}catch(e){{}}}}
tb.forEach(b=>b.addEventListener('click',()=>set(b.dataset.t)));let t0='cta';try{{t0=localStorage.getItem('scTab')||'cta'}}catch(e){{}}if(location.hash==='#peg')t0='peg';set(t0);}})();
var BF='all';function bfil(){{var q=(document.getElementById('bsq').value||'').trim().toLowerCase(),n=0;document.querySelectorAll('.book').forEach(function(b){{var ok=(BF==='all'||b.dataset.tag===BF)&&(!q||(b.dataset.s||'').indexOf(q)>=0);b.style.display=ok?'':'none';if(ok)n++;}});var e=document.getElementById('bsn');if(e)e.textContent=(q||BF!=='all')?n+'개':'';}}
document.querySelectorAll('.pill[data-f]').forEach(p=>p.addEventListener('click',()=>{{document.querySelectorAll('.pill[data-f]').forEach(x=>x.classList.toggle('on',x===p));BF=p.dataset.f;bfil();}}));
document.getElementById('bsq').addEventListener('input',bfil);</script>"""
open(f"{OUT}/index.html", "w", encoding="utf-8").write(shell("Corporate Analysis — 지수선물 · 기업분석", home, "home"))
print("ok", sorted(os.listdir(OUT)))
