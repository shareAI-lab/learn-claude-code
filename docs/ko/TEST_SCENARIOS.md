# 한국어(ko) 로컬라이제이션 테스트 시나리오

이 문서는 한국어 로컬라이제이션이 제대로 작동하는지 확인하기 위한 수동 테스트 가이드입니다.
PR 머지 전에 아래 시나리오들을 순서대로 실행해 보세요.

---

## 1. 사전 준비

```sh
# 저장소 루트에서
cd /Users/daehyun/ai-labs/learn-claude-code

# 브랜치 확인
git status
git branch --show-current   # feat/korean-localization 이어야 함

# 웹 의존성 설치 (이미 되어 있으면 건너뛰어도 됨)
cd web
npm install
```

---

## 2. 문서 테스트 (정적 마크다운)

### 2.1 파일 존재 확인

```sh
# 루트 README
ls -la /Users/daehyun/ai-labs/learn-claude-code/README-ko.md

# 12개 세션 문서
ls /Users/daehyun/ai-labs/learn-claude-code/docs/ko/
# 기대 결과:
#   s01-the-agent-loop.md, s02-tool-use.md, s03-todo-write.md,
#   s04-subagent.md, s05-skill-loading.md, s06-context-compact.md,
#   s07-task-system.md, s08-background-tasks.md, s09-agent-teams.md,
#   s10-team-protocols.md, s11-autonomous-agents.md, s12-worktree-task-isolation.md,
#   TEST_SCENARIOS.md  <- 이 파일

# 비어 있던 docs/kr/ 디렉터리는 제거되어야 함
ls /Users/daehyun/ai-labs/learn-claude-code/docs/kr 2>&1 | head -1
# 기대 결과: "No such file or directory"
```

### 2.2 라인 수 패리티(parity) 확인

각 한국어 문서가 영어 원본과 라인 수가 거의 같아야 합니다(±5%).

```sh
cd /Users/daehyun/ai-labs/learn-claude-code
for f in en/s01-the-agent-loop.md en/s02-tool-use.md en/s03-todo-write.md \
         en/s04-subagent.md en/s05-skill-loading.md en/s06-context-compact.md \
         en/s07-task-system.md en/s08-background-tasks.md en/s09-agent-teams.md \
         en/s10-team-protocols.md en/s11-autonomous-agents.md en/s12-worktree-task-isolation.md; do
  ko="docs/${f/en\//ko/}"
  en="docs/$f"
  printf "%-45s  en=%4d  ko=%4d\n" "${f##*/}" "$(wc -l < $en)" "$(wc -l < $ko)"
done
```

### 2.3 크로스 링크 헤더 확인

루트의 4개 README가 모두 동일한 4개 언어 링크를 가져야 합니다.

```sh
head -1 /Users/daehyun/ai-labs/learn-claude-code/README.md
# 다른 README들은 헤더가 다른 라인에 있을 수 있음
grep -n "한국어" /Users/daehyun/ai-labs/learn-claude-code/README.md \
                  /Users/daehyun/ai-labs/learn-claude-code/README-zh.md \
                  /Users/daehyun/ai-labs/learn-claude-code/README-ja.md \
                  /Users/daehyun/ai-labs/learn-claude-code/README-ko.md
```

**기대 결과**: 4개 README 모두에 `[한국어](./README-ko.md)` 링크가 존재.

### 2.4 README-ko.md 시각 확인 (수동)

GitHub 마크다운 미리보기에서 다음 항목을 확인하세요:

- [ ] 상단 4-언어 링크가 한 줄에 모두 보이는가
- [ ] `## Agency는 어디에서 오는가` 같은 한글 제목이 자연스러운가
- [ ] DeepMind / OpenAI / Anthropic / Atari 같은 고유명사가 그대로 유지되는가
- [ ] `agent_loop()` 파이썬 코드 블록이 그대로 보존되어 있는가
- [ ] 12개 세션 모토 블록(s01–s12)의 한글 번역이 어색하지 않은가
- [ ] 마지막 두 줄의 닫는 슬로건이 영어 원문의 임팩트를 살리는가

### 2.5 docs/ko/sXX 문서 시각 확인 (수동)

각 문서에서 무작위로 3~5개를 골라 다음을 확인:

- [ ] 코드 블록(```python …``` 등)이 그대로 영어로 남아 있는가
- [ ] ASCII 다이어그램(박스 그리기 문자)이 깨지지 않았는가
- [ ] 인라인 코드(`stop_reason`, `messages[]` 등)가 그대로 유지되는가
- [ ] 첫 등장 시 헷갈릴 만한 용어(harness, FSM, JSONL 등)에 한글 보조 설명이 괄호로 붙어 있는가
- [ ] 섹션 구조(`## 문제`, `## 해결책`, `## 동작 원리`, `## 핵심 통찰` 등)가 영어 원본과 일치하는가

---

## 3. 웹 빌드 테스트 (자동)

### 3.1 콘텐츠 추출

```sh
cd /Users/daehyun/ai-labs/learn-claude-code/web
npm run extract
```

**기대 결과**:
- `Found 48 doc files across 4 locales` 메시지 (12 × 4 = 48)
- `12 versions`, `11 diffs`, `48 docs`로 마무리
- 에러나 경고 없음

### 3.2 TypeScript 타입 체크

```sh
cd /Users/daehyun/ai-labs/learn-claude-code/web
npx tsc --noEmit
```

**기대 결과**: 출력 없음(0개 에러).

### 3.3 정적 빌드

```sh
cd /Users/daehyun/ai-labs/learn-claude-code/web
npm run build
```

**기대 결과**:
- 빌드 성공 (`✓ Compiled successfully` 또는 동등)
- 생성된 정적 경로 목록에 `/ko/`, `/ko/timeline/`, `/ko/compare/`, `/ko/layers/`,
  `/ko/s01/` … `/ko/s12/` 가 포함되어 있어야 함

확인:
```sh
ls /Users/daehyun/ai-labs/learn-claude-code/web/out/ko/ 2>&1 | head -30
```

---

## 4. 웹 런타임 테스트 (수동, 브라우저)

### 4.1 개발 서버 띄우기

```sh
cd /Users/daehyun/ai-labs/learn-claude-code/web
npm run dev
# http://localhost:3000 으로 접속
```

### 4.2 데스크톱 — 로케일 스위처

1. `http://localhost:3000/en` 접속
2. 헤더 우측 로케일 스위처에 `EN | 中文 | 日本語 | 한국어` 4개 버튼이 보이는지 확인
3. `한국어` 버튼 클릭 → URL이 `/ko`로 바뀌고 다음 텍스트가 한글로 표시되어야 함:
   - [ ] 헤더 네비게이션: `홈 / 학습 경로 / 버전 비교 / 아키텍처 레이어`
   - [ ] 메인 hero 제목 아래의 subtitle: "nano Claude Code 스타일의 에이전트를 0에서 1까지…"
   - [ ] "학습 시작" 버튼
   - [ ] "핵심 패턴", "메시지 증가 흐름", "학습 경로", "아키텍처 레이어" 섹션 헤더
4. 다른 언어로도 전환해 보고 한국어로 되돌아왔을 때 상태가 자연스러운지 확인

### 4.3 모바일 — 햄버거 메뉴

1. 브라우저 창을 모바일 폭(<768px)으로 줄이거나 DevTools의 모바일 에뮬레이션 사용
2. 햄버거 메뉴 클릭 → 메뉴가 열림
3. `EN / 中文 / 日本語 / 한국어` 네 버튼이 모두 노출되는지 확인
4. `한국어` 탭 → 페이지 새로고침 후 `/ko/` 경로에서 한글 UI가 보이는지 확인

### 4.4 학습 경로(Timeline) 페이지

`http://localhost:3000/ko/timeline` 접속:

- [ ] 페이지 제목 "학습 경로"
- [ ] s01–s12 카드의 부제목이 한글 (예: `s01: 에이전트 루프 (Agent Loop)`, `s06: 컨텍스트 압축 (Compact)`)
- [ ] "자세히 보기" 링크 표시
- [ ] LOC 증가 추이 차트 정상 렌더

### 4.5 버전 비교(Compare) 페이지

`http://localhost:3000/ko/compare` 접속:

- [ ] 페이지 제목 "버전 비교"
- [ ] "버전 A", "버전 B" 라벨이 한글
- [ ] "위에서 두 개의 버전을 선택하면 비교가 시작됩니다." 빈 상태 힌트가 한글
- [ ] 두 버전 선택 → "LOC 변화량", "B에 새로 추가된 도구" 등 한글 라벨이 보임

### 4.6 레이어(Layers) 페이지

`http://localhost:3000/ko/layers` 접속:

- [ ] 제목 "아키텍처 레이어"
- [ ] 5개 레이어 라벨이 한글: 도구 & 실행 / 계획 & 조정 / 메모리 관리 / 동시성 / 협업
- [ ] 각 레이어 설명 한글 (예: "에이전트가 무엇을 할 수 있는가…")

### 4.7 세션 상세 페이지 (s01–s12 각각)

`http://localhost:3000/ko/s01` 부터 `s12` 까지 둘러보세요. 각 페이지에서:

- [ ] 헤더의 세션 제목이 한글 (예: `s06: 컨텍스트 압축 (Compact)`)
- [ ] 레이어 배지 라벨이 한글 (예: "메모리 관리")
- [ ] 탭 이름: `학습 / 시뮬레이션 / 소스 / 심층 분석`
- [ ] **학습 탭**: docs/ko/sXX-*.md 의 내용이 마크다운 렌더링으로 보임
  - 코드 블록은 영어 그대로
  - 본문은 한글
- [ ] **시뮬레이션 탭**: 에이전트 루프 시뮬레이터 버튼 라벨이 한글 (재생/일시정지/한 단계/초기화)
- [ ] **소스 탭**: 파이썬 코드 표시, "소스 보기" 버튼 한글
- [ ] **심층 분석 탭**: 정상 동작 + 한글 라벨
- [ ] 이전/다음 버튼: "이전 / 다음" + 다음 세션 한글 제목
- [ ] "변경점 보기", "설계 결정", "새로 추가된 것" 등의 부제목 한글

### 4.8 다크 모드 토글

- 헤더의 달/태양 아이콘 클릭 → 라이트/다크 모드 전환이 한국어 페이지에서도 정상 동작
- 새로고침 후에도 모드가 유지됨

### 4.9 폴백(fallback) 동작 확인

만약 ko.json에 빠진 키가 있다면 영어로 폴백되어야 합니다.
간단히 키 하나를 일부러 누락시켜 보고 다시 추가하는 방식으로 확인 가능
(테스트 후 반드시 원복).

---

## 5. 회귀(regression) 체크

기존 언어(en, zh, ja)가 깨지지 않았는지 확인:

- [ ] `/en` 경로에서 영어 UI 정상
- [ ] `/zh` 경로에서 중국어 UI 정상
- [ ] `/ja` 경로에서 일본어 UI 정상
- [ ] 각 언어에서 `/sXX` 페이지의 docs 본문이 해당 언어로 표시됨
- [ ] 로케일 스위처 4개 모두 정상 동작

---

## 6. 알려진 비-목적 (out of scope)

다음 항목은 이 PR의 범위에 포함되지 않습니다:

- `agents/sXX_*.py` 파이썬 파일 내부의 영어 주석/문자열은 번역하지 않습니다(코드 정체성 유지).
- `skills/*/SKILL.md` (Anthropic Agent SDK 스타일 스킬 정의)는 다국어를 지원하지 않으므로 번역 대상이 아닙니다.
- `.env`, `requirements.txt`, `package.json` 등 설정 파일은 번역하지 않습니다.

---

## 7. 문제 발생 시

- 빌드 실패: `cd web && npm run extract && npx tsc --noEmit` 순서로 디버깅
- 한글이 깨져 보임: 파일 인코딩이 UTF-8 인지 확인 (`file docs/ko/s01-the-agent-loop.md`)
- 로케일 스위처 클릭해도 페이지가 안 바뀜: 브라우저 콘솔 에러 확인, `web/src/components/layout/header.tsx`의 LOCALES 배열 검토
- 한국어 본문이 표시되지 않음: `web/src/data/generated/docs.json`에 `"locale": "ko"` 항목이 12개 있는지 확인 (`grep -c '"locale": "ko"' web/src/data/generated/docs.json`)

---

## 통과 기준

위 모든 체크박스가 통과되어야 PR을 머지할 준비가 된 것입니다.
번역의 어색함이나 용어 보완이 필요하면 별도 이슈로 트래킹해도 좋습니다.
