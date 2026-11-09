"""CTA 신호 계산 (사이트 생성과 데이터 수집에서 같이 사용).

8개 신호를 각각 +1(매수) / -1(매도)로 매기고 평균을 점수로 쓴다.
  1. 장기 추세 필터   종가 vs 200일선
  2. 중장기 교차      50일선 vs 200일선
  3. 단기 교차        20일선 vs 50일선
  4. 돈키언 채널      종가 vs 55일 고가·저가 중간값
  5~8. 모멘텀         종가 vs 21/63/126/252거래일 전 종가
"""

KEYS = ["s200", "s50", "s20", "dh55", "dl55", "m1", "m3", "m6", "m12"]


def fmt(v, cur):
    if cur == "원":
        return f"{v:,.0f}원"
    return f"${v:,.2f}" if v < 1000 else f"${v:,.0f}"


def signals(e):
    """e: close, s20, s50, s200, dh55, dl55, m1, m3, m6, m12, cur → (list, score).
    상장 기간이 짧아 200일선·6·12개월 기준가가 없으면 그 신호는 빼고 나머지로 평균한다.
    최소 조건(20·50일선, 55일 고저, 1개월 기준가)이 없으면 (None, None)."""
    if not all(e.get(k) for k in ("close", "s20", "s50", "dh55", "dl55", "m1")):
        return None, None
    c, cur = e["close"], e.get("cur", "$")
    F = lambda v: fmt(v, cur)
    mid = (e["dh55"] + e["dl55"]) / 2
    out = []
    if e.get("s200"):
        out.append(("장기 추세 필터", "종가 vs 200일선", f"{F(c)} {'>' if c > e['s200'] else '<'} {F(e['s200'])}", 1 if c > e["s200"] else -1))
        out.append(("중장기 교차", "50일선 vs 200일선", f"{F(e['s50'])} {'>' if e['s50'] > e['s200'] else '<'} {F(e['s200'])}", 1 if e["s50"] > e["s200"] else -1))
    out.append(("단기 교차", "20일선 vs 50일선", f"{F(e['s20'])} {'>' if e['s20'] > e['s50'] else '<'} {F(e['s50'])}", 1 if e["s20"] > e["s50"] else -1))
    out.append(("돈키언 채널", "55일 고가·저가 중간값", f"중간값 {F(mid)} {'위' if c > mid else '아래'}", 1 if c > mid else -1))
    for lab, k, n in [("1개월 모멘텀", "m1", 21), ("3개월 모멘텀", "m3", 63), ("6개월 모멘텀", "m6", 126), ("12개월 모멘텀", "m12", 252)]:
        if not e.get(k):
            continue
        r = (c / e[k] - 1) * 100
        out.append((lab, f"{n}거래일 수익률", f"{r:+.1f}% (기준 {F(e[k])})", 1 if c > e[k] else -1))
    return out, sum(x[3] for x in out) / len(out)
