# Corporate Analysis 자동 갱신 사이트

GitHub에 올려 두기만 하면 매일 자동으로 갱신되는 기업분석·시장 지표 사이트입니다. 갱신에 Claude 토큰은 쓰이지 않습니다.

| 항목 | 갱신 방식 | 시점 |
|---|---|---|
| CTA 점수 (16개 종목, 8개 신호) | GitHub Actions가 일봉을 받아 계산 | 매일 06:30 KST(미국장 마감 후), 16:00 KST(한국장 마감 후) |
| CNN 공포·탐욕 지수 | 위와 동일 | 위와 동일 |
| 선물·VIX·달러·환율·유가·금·미국 국채 금리 | 위와 동일 | 위와 동일 |
| 시세 띠, 기업별 차트 | 트레이딩뷰 공식 위젯 (방문자 브라우저에서 직접 로드) | 장중 실시간(거래소별로 일부 지연) |
| 기업분석 본문 | `content/` 폴더의 HTML | 직접 수정하거나 Claude에게 요청 |

## 처음 설정 (한 번만, 약 10분)

1. **GitHub 가입**: https://github.com 에서 계정을 만듭니다.
2. **저장소 만들기**: 오른쪽 위 `+` → `New repository`.
   - Repository name: 예) `corporate-analysis`
   - **Public** 선택 (무료 계정에서 Pages를 쓰려면 공개 저장소여야 합니다)
   - `Create repository`
3. **파일 올리기**: 새 저장소 화면에서 `uploading an existing file` 링크 클릭 → 압축을 푼 폴더 안의 **모든 파일과 폴더**를 끌어다 놓기 → `Commit changes`.
   - 웹 업로드는 한 번에 100개 파일까지라 **두 번에 나눠** 올립니다: ① `content` 폴더만 먼저 → `Commit`, ② `Add file → Upload files`로 나머지(`data`, `scripts`, `.github`, `README.md`, `requirements.txt`, `.gitignore`) → `Commit`.
   - `.github` 폴더처럼 점(.)으로 시작하는 폴더는 숨겨져 있을 수 있습니다. 윈도우 탐색기 `보기 → 숨긴 항목`을 켜고 함께 올려야 자동 갱신이 작동합니다.
   - 끌어다 놓기로 `.github` 폴더가 안 올라가면: `Add file → Create new file` → 파일 이름에 `.github/workflows/update.yml` 입력 → 내용 붙여넣기 → `Commit`.
4. **Actions 쓰기 권한 켜기**: `Settings → Actions → General → Workflow permissions` → **Read and write permissions** 선택 → `Save`.
5. **Pages 켜기**: `Settings → Pages → Build and deployment → Source`를 **GitHub Actions**로 선택.
6. **첫 실행**: `Actions` 탭 → 왼쪽 `매일 데이터 갱신 + 사이트 배포` → `Run workflow` → 초록 버튼.
   - 2~3분 뒤 초록 체크가 뜨면 `Settings → Pages` 맨 위에 사이트 주소가 나옵니다: `https://아이디.github.io/corporate-analysis/`

## 이후 할 일

- 없습니다. 평일마다 하루 두 번 자동으로 갱신됩니다.
- 수동 갱신이 필요하면 `Actions → Run workflow`.
- 실패하면 GitHub가 이메일로 알려 줍니다. `Actions` 탭에서 빨간 X를 눌러 로그를 볼 수 있습니다.

## 폴더 구조

```
content/            기업별 리포트 본문(HTML)과 차트 이미지 — 분기 실적 업데이트 때만 수정
data/market.json    시장 지표·공포탐욕 지수 (자동 갱신)
data/cta.json       16개 종목 CTA 데이터 (자동 갱신)
scripts/update_data.py   데이터 수집 (Yahoo Finance, FRED, CNN)
scripts/build_site.py    사이트 생성 → _site/
scripts/ctalib.py        CTA 8개 신호 계산 규칙
.github/workflows/update.yml   자동 실행 스케줄
```

## 알아둘 점

- **CTA 모델**: 200일선 필터, 50/200·20/50 이동평균 교차, 55일 돈키언 채널, 1·3·6·12개월 모멘텀 8개 신호의 평균입니다. 자체 계산 모델이며 증권사 CTA 포지션 데이터가 아닙니다.
- **데이터 출처**: Yahoo Finance(yfinance)와 CNN 공포·탐욕 지수는 공식 API가 아닙니다. 출처가 막히면 그 항목만 이전 값이 유지되고 나머지는 계속 갱신됩니다.
- **일본 국채 금리**: 무료 일간 데이터가 없어 미국 3개월물·5년물로 대체했습니다.
- **한국 종목 위젯**: 삼성전자·SK하이닉스는 트레이딩뷰 위젯에서 라이선스상 차트가 표시되지 않을 수 있습니다(CTA 계산은 정상).
- **휴면 방지**: 공개 저장소는 60일간 활동이 없으면 예약 실행이 멈출 수 있습니다. 매일 데이터 커밋이 쌓이므로 보통 문제없지만, 멈추면 `Actions` 탭에서 다시 켜면 됩니다.
- 개인 학습용 분석이며 투자 권유가 아닙니다.
