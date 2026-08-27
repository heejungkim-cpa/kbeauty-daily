# K-BEAUTY DAILY

K-뷰티 산업 뉴스를 매일 아침 8시에 자동으로 모으고, 분류하고, 요약해서 한 페이지로 보여줍니다.

내 컴퓨터가 꺼져 있어도 GitHub 서버에서 알아서 돌아갑니다. 결과는 웹 주소로 올라가니 휴대폰에서도 열립니다.

```
매일 08:00 KST
  → 구글 뉴스 RSS 수집       (API 키 불필요)
  → 중복 제거 · 광고성 기사 제외
  → 키워드로 7개 분류        (규칙 기반, 실패 없음)
  → AI가 '오늘의 흐름' 작성  (선택, 하루 1회 호출)
  → docs/index.html 갱신
```

---

## 먼저 내 컴퓨터에서 확인해보기

네트워크나 계정 설정 없이 화면부터 보고 싶다면:

```bash
pip install -r requirements.txt
python collect.py --demo
python render.py
```

`docs/index.html` 을 브라우저로 열면 샘플 데이터가 채워진 대시보드가 보입니다.
마음에 들면 아래 자동화 설정으로 넘어가세요.

실제로 한 번 수집해보려면 `--demo` 없이 실행하면 됩니다.

```bash
python collect.py
python render.py
```

---

## 자동화 설정 (한 번만 하면 됩니다)

### 1단계 — GitHub에 올리기

GitHub에서 새 저장소를 만들고(예: `kbeauty-daily`), 이 폴더를 통째로 올립니다.

```bash
git init
git add .
git commit -m "첫 커밋"
git branch -M main
git remote add origin https://github.com/사용자명/kbeauty-daily.git
git push -u origin main
```

> 저장소는 **Public** 으로 만드세요. Private 저장소는 GitHub Pages가 유료 플랜에서만 됩니다.

### 2단계 — 자동 실행 권한 켜기

저장소 → **Settings** → **Actions** → **General** → 맨 아래 **Workflow permissions**
→ `Read and write permissions` 선택 → Save.

이걸 안 하면 수집은 되는데 결과를 저장하지 못하고 실패합니다. 가장 흔한 오류입니다.

### 3단계 — 웹페이지 켜기

저장소 → **Settings** → **Pages**
→ Source: `Deploy from a branch`
→ Branch: `main` / 폴더: `/docs` → Save.

1~2분 뒤 `https://사용자명.github.io/kbeauty-daily/` 로 접속됩니다.

### 4단계 — 첫 실행 확인

저장소 → **Actions** 탭 → 왼쪽에서 `매일 뉴스 수집` 선택 → **Run workflow** 버튼.

초록색 체크가 뜨면 성공입니다. 이제부터는 매일 아침 8시에 알아서 돌아갑니다.

---

## AI 요약 붙이기 (선택)

키를 넣지 않아도 대시보드는 정상 작동합니다. 요약 영역만 안 나옵니다.

붙이려면 [console.anthropic.com](https://console.anthropic.com) 에서 API 키를 발급받고,
저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Secret: 발급받은 키

하루에 딱 한 번, 그날 헤드라인 전체를 넘겨서 3~4줄 브리핑을 받는 구조입니다.
기사 본문을 크롤링하지 않으므로 비용도 작고 깨질 일도 적습니다.

---

## 수집 범위 바꾸기

`config.py` 하나만 고치면 됩니다. 다른 파일은 건드릴 필요 없습니다.

| 고칠 항목 | 위치 |
|---|---|
| 검색어 추가·삭제 | `SEARCH_QUERIES` |
| 분류 기준 · 색상 | `CATEGORIES` |
| 기업 태그 | `COMPANY_TAGS` |
| 걸러낼 기사 | `EXCLUDE_KEYWORDS` |
| 하루 기사 수 상한 | `MAX_ARTICLES_PER_DAY` |

특정 매체만 보고 싶으면 검색어에 `site:도메인` 을 넣으세요.
RSS를 제공하지 않는 매체도 이 방법으로 가져올 수 있습니다.

```python
SEARCH_QUERIES = [
    "site:cosinkorea.com",
    "site:beautynury.com",
]
```

수집 시각을 바꾸려면 `.github/workflows/daily.yml` 의 cron을 고칩니다.
**UTC 기준**이라 한국시간에서 9시간을 빼야 합니다.

| 원하는 한국시간 | cron |
|---|---|
| 07:00 | `0 22 * * *` |
| 08:00 | `0 23 * * *` |
| 09:00 | `0 0 * * *` |
| 평일 08:00만 | `0 23 * * 0-4` |

---

## 파일 구조

```
config.py                  설정 — 여기만 고치면 됩니다
collect.py                 수집 · 중복 제거 · 분류 · AI 요약
render.py                  JSON → HTML 대시보드
requirements.txt           라이브러리 2개
.github/workflows/daily.yml  매일 아침 자동 실행
data/YYYY-MM-DD.json       날짜별 원본 (90일 보관)
docs/index.html            대시보드 (GitHub Pages가 이 폴더를 씁니다)
```

수집한 원본을 날짜별로 남기기 때문에, 나중에 "지난 3개월 동안 ODM 이슈가 몇 건이었나"
같은 시계열 분석을 `data/` 폴더만 읽어서 바로 할 수 있습니다.

---

## 잘 안 될 때

**Actions가 빨간불** — 대부분 2단계 권한 설정을 빠뜨린 경우입니다.
Actions 탭에서 실패한 실행을 눌러 로그를 보면 어느 줄에서 멈췄는지 나옵니다.

**페이지가 404** — Pages 설정에서 폴더가 `/docs` 인지 확인하세요.
`docs/index.html` 이 저장소에 실제로 올라가 있어야 합니다.

**기사가 너무 적다** — `when:1d` 로 하루치만 받고 있어서 그렇습니다.
`collect.py` 의 `when:1d` 를 `when:2d` 로 바꾸면 범위가 넓어집니다.

**엉뚱한 기사가 섞인다** — `EXCLUDE_KEYWORDS` 에 단어를 추가하거나,
검색어를 더 구체적으로 바꾸세요. 관련도 점수가 0인 기사는 `기타` 로 밀려 맨 뒤에 나옵니다.

**일부 검색어만 실패** — 정상입니다. 실패한 검색어는 건너뛰고 나머지로 페이지를 만듭니다.
대시보드 맨 아래에 어떤 검색어가 실패했는지 표시됩니다.
