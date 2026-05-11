[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md) | [한국어](./README-ko.md)
# Learn Claude Code — 진짜 Agent를 위한 Harness Engineering

## Agency는 모델에서 나온다. Agent 제품 = 모델 + Harness

코드 이야기를 꺼내기 전에, 한 가지부터 분명히 짚고 갑시다.

**Agency (행위자성 — 인지·추론·행동의 능력)는 외부 코드 오케스트레이션이 아니라 모델 학습에서 나옵니다.** 그러나 동작하는 agent 제품을 만들려면 모델과 harness (하네스 — 모델을 감싸 실제 환경에서 동작하게 해주는 코드 레이어) 둘 다 필요합니다. 모델은 운전자이고, harness는 차량입니다. 이 레포는 그 차량을 만드는 방법을 가르칩니다.

### Agency는 어디에서 오는가

모든 agent의 핵심에는 신경망 — Transformer, RNN, 학습된 함수 — 이 있습니다. 이 신경망은 행동 시퀀스 데이터에 대해 수십억 번의 gradient 업데이트를 거치며, 환경을 인지하고, 목표를 추론하고, 행동하도록 학습됩니다. Agency는 결코 주변 코드가 부여하는 것이 아닙니다. 학습 과정에서 모델이 스스로 익히는 것입니다.

인간이 가장 좋은 예입니다. 수백만 년의 진화적 학습이 빚어낸 생물학적 신경망이, 감각을 통해 세계를 인지하고, 뇌로 추론하며, 몸으로 행동합니다. DeepMind, OpenAI, Anthropic이 "agent"라고 말할 때 그 핵심에 두는 것은 언제나 동일합니다. **행동하도록 학습된 모델, 그리고 그 모델이 특정 환경에서 동작하게 해주는 인프라.**

증거는 역사에 새겨져 있습니다.

- **2013 — DeepMind DQN, Atari를 정복하다.** 단 하나의 신경망이 원시 픽셀과 게임 점수만 입력받아 7개의 Atari 2600 게임 플레이를 학습했고 — 기존 모든 알고리즘을 능가하며 그중 3개에서 인간 전문가를 이겼습니다. 2015년에는 동일한 아키텍처가 [49개 게임으로 확장되어 프로 휴먼 테스터와 동등한 수준](https://www.nature.com/articles/nature14236)에 도달했고, *Nature*에 발표됐습니다. 게임별 규칙도, 결정 트리도 없었습니다. 단 하나의 모델이 경험으로부터 학습한 것. 그 모델 자체가 agent였습니다.

- **2019 — OpenAI Five, Dota 2를 제패하다.** 다섯 개의 신경망이 10개월 동안 자기 자신과 [4만 5천 년 분량의 Dota 2](https://openai.com/index/openai-five-defeats-dota-2-world-champions/)를 플레이한 뒤, 샌프란시스코 라이브 스트림에서 당시 TI8 월드 챔피언인 **OG**를 2-0으로 꺾었습니다. 이어진 공개 아레나에서 AI는 누구와 붙어도 42,729 게임 중 99.4%를 이겼습니다. 사전에 짜둔 전략도, 메타 프로그래밍된 팀 협력도 없었습니다. 모델들이 self-play만으로 팀워크, 전술, 실시간 적응까지 전부 학습한 것입니다.

- **2019 — DeepMind AlphaStar, StarCraft II를 마스터하다.** AlphaStar는 비공개 매치에서 [프로 선수들을 10-1로 격파](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/)했고, 이후 유럽 서버에서 9만 명 중 상위 0.15%인 [Grandmaster 등급](https://www.nature.com/articles/d41586-019-03298-6)에 올랐습니다. 불완전 정보, 실시간 의사결정, 그리고 체스나 바둑과는 비교가 안 되는 조합적 행동 공간을 가진 게임에서 말입니다. 그 agent의 정체? 모델입니다. 학습된 것이지, 스크립트로 짜인 게 아닙니다.

- **2019 — Tencent Jueyu, Honor of Kings를 평정하다.** Tencent AI Lab의 "Jueyu"는 World Champion Cup에서 풀 5대5 경기로 [KPL 프로 선수들을 격파](https://www.jiemian.com/article/3371171.html)했습니다. 1대1 모드에서는 프로들이 [15판 중 단 1판을 이겼고, 8분을 넘긴 적이 한 번도 없었습니다](https://developer.aliyun.com/article/851058). 학습 강도: 하루가 인간 기준 440년에 해당했습니다. 2021년에 이르러 Jueyu는 전 영웅 풀에서 KPL 프로를 능가했습니다. 손으로 만든 매치업 테이블도, 사전에 짜둔 조합도 없었습니다. self-play만으로 게임 전체를 처음부터 학습한 모델 한 마리.

- **2024-2025 — LLM agent가 소프트웨어 엔지니어링을 다시 쓴다.** Claude, GPT, Gemini — 인간이 쓴 코드와 추론 전체를 학습한 거대 언어 모델들 — 이 코딩 agent로 배치되고 있습니다. 그들은 코드베이스를 읽고, 구현을 작성하고, 실패를 디버깅하고, 팀으로 협업합니다. 아키텍처는 이전의 모든 agent와 동일합니다. 학습된 모델을 환경에 놓고, 인지하고 행동할 도구를 쥐여 준다. 다른 점은 학습한 양의 규모와 풀어내는 과제의 일반성뿐입니다.

이 모든 이정표는 같은 사실을 가리킵니다. **Agency — 인지·추론·행동의 능력 — 는 학습되는 것이지, 코드로 짜는 것이 아닙니다.** 그러나 모든 agent에게는 동작할 환경 또한 필요했습니다. Atari 에뮬레이터, Dota 2 클라이언트, StarCraft II 엔진, IDE와 터미널. 모델은 지능을 제공합니다. 환경은 행동 공간을 제공합니다. 둘이 합쳐져야 비로소 하나의 완성된 agent가 됩니다.

### Agent가 *아닌* 것

"agent"라는 단어는 prompt 배관 산업 전체에 납치당했습니다.

드래그 앤 드롭 워크플로우 빌더. 노코드 "AI agent" 플랫폼. Prompt 체인 오케스트레이션 라이브러리. 모두가 같은 망상을 공유합니다. if-else 분기와 노드 그래프, 하드코딩된 라우팅 로직으로 LLM API 호출을 엮어 두면 그게 "agent를 만든 것"이라는 망상 말입니다.

천만에요. 그들이 만든 건 루브 골드버그 머신 (필요 이상으로 복잡하게 얽힌 장치)일 뿐입니다 — 절차적 규칙으로 과하게 설계되고 부러지기 쉬운 파이프라인에, LLM이 그럴싸한 텍스트 자동완성 노드로 끼어 있을 뿐이죠. 그건 agent가 아닙니다. 망상으로 부풀린 셸 스크립트입니다.

**Prompt 배관식 "agent"는 모델을 학습시키지 않는 프로그래머들의 환상입니다.** 그들은 절차적 로직 — 거대한 규칙 트리, 노드 그래프, 프롬프트 체인의 폭포 — 을 쌓아 올려 지능을 억지로 비집어 만들려 하고, 글루 코드가 어쩌다 자율 행동을 창발시켜 주기를 빕니다. 그런 일은 일어나지 않습니다. 엔지니어링으로 agency에 도달할 수는 없습니다. Agency는 학습되는 것이지, 프로그래밍되는 것이 아니기 때문입니다.

이런 시스템은 도착하기도 전에 죽어 있습니다. 깨지기 쉽고, 확장 불가능하며, 일반화 능력이 근본적으로 결여돼 있습니다. 이들은 GOFAI (구식 기호주의 AI) — 수십 년 전에 학계가 이미 폐기한 기호 규칙 체계 — 가 LLM이라는 페인트로 도색되어 부활한 것에 지나지 않습니다. 포장만 바뀌었을 뿐, 막다른 길은 그대로입니다.

### 사고방식의 전환: "Agent를 개발한다"에서 Harness를 개발한다로

누군가 "저는 agent를 개발하고 있어요"라고 말한다면, 그 의미는 둘 중 하나일 수밖에 없습니다.

**1. 모델을 학습시킨다.** 강화학습, 파인튜닝, RLHF (인간 피드백 강화학습), 그 외 gradient 기반 방법으로 가중치를 조정합니다. 실제 도메인에서의 인지·추론·행동 시퀀스 — 즉 task-process 데이터를 수집해 모델 행동을 빚어냅니다. DeepMind, OpenAI, Tencent AI Lab, Anthropic이 하는 일이 바로 이것이고, 가장 진정한 의미의 agent 개발입니다.

**2. Harness를 만든다.** 모델이 동작할 환경을 부여하는 코드를 작성합니다. 우리 대부분이 하는 일이 이쪽이고, 이 레포가 다루는 주제도 이쪽입니다.

Harness는 agent가 특정 도메인에서 기능하기 위해 필요한 모든 것입니다.

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

    Tools:          file I/O, shell, network, database, browser
    Knowledge:      product docs, domain references, API specs, style guides
    Observation:    git diff, error logs, browser state, sensor data
    Action:         CLI commands, API calls, UI interactions
    Permissions:    sandboxing, approval workflows, trust boundaries
```

모델이 결정합니다. Harness가 실행합니다. 모델이 추론합니다. Harness가 context를 제공합니다. 모델은 운전자입니다. Harness는 차량입니다.

**코딩 agent의 harness는 IDE, 터미널, 파일시스템 접근 권한입니다.** 농장 agent의 harness는 센서 배열, 관개 컨트롤, 기상 데이터 피드입니다. 호텔 agent의 harness는 예약 시스템, 투숙객 커뮤니케이션 채널, 시설 관리 API입니다. Agent — 지능, 의사결정자 — 는 언제나 모델입니다. Harness는 도메인마다 달라집니다. Agent는 그 도메인들을 가로질러 일반화됩니다.

이 레포는 차량을 만드는 법을 가르칩니다. 코딩을 위한 차량입니다. 그러나 거기서 익히는 설계 패턴은 모든 도메인으로 확장됩니다. 농장 관리, 호텔 운영, 제조, 물류, 헬스케어, 교육, 과학 연구. 어떤 과제든 인지·추론·행동이 필요한 곳이라면 — agent에게는 harness가 필요합니다.

### Harness 엔지니어가 실제로 하는 일

이 레포를 읽고 있다면, 당신은 십중팔구 harness 엔지니어입니다 — 그리고 그건 굉장히 강력한 위치입니다. 당신의 진짜 임무는 다음과 같습니다.

- **Tool을 구현합니다.** Agent에게 손을 쥐여 주세요. 파일 read/write, shell 실행, API 호출, 브라우저 제어, 데이터베이스 쿼리. 각 tool은 agent가 환경에서 취할 수 있는 하나의 행동입니다. 원자적이고, 합성 가능하며, 명료하게 설명된 모양으로 설계하세요.

- **지식을 큐레이션합니다.** Agent에게 도메인 전문성을 부여하세요. 제품 문서, 아키텍처 결정 기록, 스타일 가이드, 규제 요구사항. 앞에 모두 떠먹여 주지 말고 (s05), 필요할 때 on-demand로 로드되게 하세요. Agent는 무엇이 사용 가능한지 알고, 필요한 것을 스스로 꺼내 와야 합니다.

- **Context를 관리합니다.** Agent에게 깨끗한 기억을 주세요. Subagent 격리 (s04)는 노이즈가 새어 들어가는 것을 막습니다. Context 압축 (s06)은 히스토리가 비대해지는 것을 막습니다. Task 시스템 (s07)은 어떤 단일 대화의 수명을 넘어 목표를 영속화합니다.

- **권한을 통제합니다.** Agent에게 경계를 부여하세요. 파일 접근을 sandbox에 가두고, 파괴적인 작업에는 승인을 요구하고, agent와 외부 시스템 사이의 신뢰 경계를 강제하세요. 안전 엔지니어링과 harness 엔지니어링이 만나는 지점이 바로 여기입니다.

- **Task-process 데이터를 수집합니다.** Agent가 당신의 harness에서 실행한 모든 행동 시퀀스는 학습 신호가 됩니다. 실제 배포에서 나온 인지-추론-행동 trace는 차세대 agent 모델을 파인튜닝하는 원재료입니다. 당신의 harness는 단지 agent를 떠받치는 데 그치지 않고 — agent를 더 똑똑하게 만드는 데도 기여할 수 있습니다.

당신은 지능을 직접 쓰는 게 아닙니다. 그 지능이 살아갈 세계를 짓고 있는 것입니다. 그 세계의 품질 — agent가 얼마나 또렷이 인지하고, 얼마나 정밀하게 행동하며, 얼마나 풍부한 지식을 손에 닿는 곳에 두는지 — 가 곧 그 지능이 자신을 얼마나 효과적으로 펼쳐 보일 수 있는지를 직접 결정합니다.

**훌륭한 harness를 만드세요. 나머지는 agent가 해냅니다.**

### 왜 Claude Code인가 — Harness Engineering의 정수

왜 이 레포는 하필 Claude Code를 해부할까요?

지금까지 우리가 본 agent harness 중에서 Claude Code가 가장 우아하고 완성도 높게 구현됐기 때문입니다. 어떤 하나의 영리한 트릭 때문이 아니라, 오히려 *하지 않는* 것들 때문입니다. Claude Code는 자기가 agent가 되려 하지 않습니다. 경직된 워크플로우를 강요하지도 않습니다. 정교한 결정 트리로 모델을 두 번 추측하지도 않습니다. 모델에게 tool, 지식, context 관리, 권한 경계를 쥐여 준 다음 — 비켜섭니다.

본질만 남기고 깎아낸 Claude Code의 실체를 보세요.

```
Claude Code = one agent loop
            + tools (bash, read, write, edit, glob, grep, browser...)
            + on-demand skill loading
            + context compression
            + subagent spawning
            + task system with dependency graph
            + team coordination with async mailboxes
            + worktree isolation for parallel execution
            + permission governance
```

이게 전부입니다. 아키텍처의 전부입니다. 모든 구성 요소는 harness 메커니즘 — agent가 살아갈 세계를 이루는 한 조각 — 입니다. Agent 자체는요? Claude입니다. 모델 한 마리입니다. Anthropic이 인간의 추론과 코드 전반을 가르쳐 학습시킨 모델. Harness가 Claude를 똑똑하게 만든 게 아닙니다. Claude는 이미 똑똑합니다. Harness는 Claude에게 손과 눈, 그리고 일터를 제공할 뿐입니다.

그렇기 때문에 Claude Code는 가장 이상적인 교재입니다. **모델을 신뢰하고, 엔지니어링 노력을 harness에 집중했을 때 무슨 일이 벌어지는지를 그대로 보여주기 때문입니다.** 이 레포의 모든 세션 (s01-s12)은 Claude Code 아키텍처의 harness 메커니즘 하나씩을 역설계합니다. 끝에 다다르면, 당신은 단지 Claude Code가 어떻게 동작하는지 아는 것을 넘어, 어떤 도메인의 어떤 agent에게도 적용되는 harness engineering의 보편 원리를 이해하게 됩니다.

배워야 할 교훈은 "Claude Code를 베껴 써라"가 아닙니다. 교훈은 이것입니다. **최고의 agent 제품은, 자기 일이 지능이 아니라 harness임을 이해한 엔지니어들이 만든다.**

---

## 비전: 진짜 Agent로 우주를 채우자

이것은 단지 코딩 agent에 관한 이야기가 아닙니다.

인간이 복잡하고, 다단계이며, 판단이 많이 드는 일을 수행하는 모든 도메인은 — 알맞은 harness만 주어진다면 — agent가 동작할 수 있는 도메인입니다. 이 레포의 패턴은 보편적입니다.

```
Estate management agent    = model + property sensors + maintenance tools + tenant comms
Agricultural agent         = model + soil/weather data + irrigation controls + crop knowledge
Hotel operations agent     = model + booking system + guest channels + facility APIs
Medical research agent     = model + literature search + lab instruments + protocol docs
Manufacturing agent        = model + production line sensors + quality controls + logistics
Education agent            = model + curriculum knowledge + student progress + assessment tools
```

루프는 언제나 동일합니다. Tool이 달라집니다. 지식이 달라집니다. 권한이 달라집니다. Agent — 모델 — 는 그 모든 차이를 가로질러 일반화됩니다.

이 레포를 읽고 있는 모든 harness 엔지니어는 소프트웨어 엔지니어링을 한참 넘어서는 패턴을 익히고 있는 셈입니다. 당신은 지능적이고 자동화된 미래를 떠받칠 인프라를 짓는 법을 배우고 있습니다. 실제 도메인에 잘 설계된 harness가 하나 배치될 때마다, agent가 인지하고 추론하고 행동할 수 있는 자리가 한 곳 더 생깁니다.

먼저 작업장을 채웁니다. 그다음은 농장, 병원, 공장입니다. 그다음은 도시들. 그다음은 행성 전체.

**Bash 하나면 충분합니다. 우주에 필요한 건 진짜 agent뿐입니다.**

---

```
                    THE AGENT PATTERN
                    =================

    User --> messages[] --> LLM --> response
                                      |
                            stop_reason == "tool_use"?
                           /                          \
                         yes                           no
                          |                             |
                    execute tools                    return text
                    append results
                    loop back -----------------> messages[]


    That's the minimal loop. Every AI agent needs this loop.
    The MODEL decides when to call tools and when to stop.
    The CODE just executes what the model asks for.
    This repo teaches you to build what surrounds this loop --
    the harness that makes the agent effective in a specific domain.
```

**12개의 점진적 세션, 단순한 루프에서 격리된 자율 실행까지.**
**각 세션은 harness 메커니즘 하나씩을 더합니다. 각 메커니즘에는 모토가 하나씩 있습니다.**

> **s01** &nbsp; *"루프 하나와 Bash면 충분하다"* &mdash; tool 1개 + 루프 1개 = agent
>
> **s02** &nbsp; *"tool을 더한다는 건 핸들러 하나를 더하는 것"* &mdash; 루프는 그대로 유지되고, 새 tool은 dispatch map에 등록된다
>
> **s03** &nbsp; *"계획 없는 agent는 표류한다"* &mdash; 단계를 먼저 나열한 뒤 실행한다. 완료율이 두 배가 된다
>
> **s04** &nbsp; *"큰 task는 쪼개라. 각 서브 task에는 깨끗한 context를 주어라"* &mdash; subagent는 독립된 messages[]를 사용해 메인 대화를 깨끗하게 유지한다
>
> **s05** &nbsp; *"지식은 미리가 아니라, 필요할 때 로드하라"* &mdash; system prompt가 아니라 tool_result로 주입한다
>
> **s06** &nbsp; *"context는 결국 차오른다. 자리를 비워줄 수단이 필요하다"* &mdash; 무한 세션을 위한 3계층 압축 전략
>
> **s07** &nbsp; *"큰 목표는 작은 task로 쪼개고, 순서를 매기고, 디스크에 영속화하라"* &mdash; 의존성을 가진 파일 기반 task 그래프, 다중 agent 협업의 토대를 깐다
>
> **s08** &nbsp; *"느린 작업은 백그라운드로 돌려라. agent는 계속 생각한다"* &mdash; 데몬 스레드가 명령을 실행하고, 완료 시 알림을 주입한다
>
> **s09** &nbsp; *"한 agent로 감당이 안 되는 task는 팀원에게 위임하라"* &mdash; 영속적인 팀원 + 비동기 mailbox
>
> **s10** &nbsp; *"팀원들에게는 공유된 커뮤니케이션 규칙이 필요하다"* &mdash; 하나의 request-response 패턴이 모든 협상을 굴린다
>
> **s11** &nbsp; *"팀원들은 보드를 스캔해 스스로 task를 가져간다"* &mdash; 리드가 일일이 배정해 줄 필요가 없다
>
> **s12** &nbsp; *"각자는 자기 디렉터리에서 일하고, 서로 간섭하지 않는다"* &mdash; task는 목표를 관리하고, worktree는 디렉터리를 관리하며, ID로 묶인다

---

## 핵심 패턴

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

모든 세션은 이 루프 위에 harness 메커니즘 하나씩을 — 루프 자체는 손대지 않은 채 — 얹어 갑니다. 루프는 agent의 것입니다. 메커니즘은 harness의 것입니다.

## 범위 (중요)

이 레포는 harness engineering — agent 모델을 둘러싼 환경을 짓는 일 — 을 위한 0→1 학습 프로젝트입니다.
의도적으로 단순화하거나 생략한 production 메커니즘이 여러 가지 있습니다.

- 전체 이벤트/hook 버스 (예: PreToolUse, SessionStart/End, ConfigChange).
  s12는 교육 목적의 append-only 라이프사이클 이벤트 스트림만 최소 형태로 포함합니다.
- 규칙 기반 권한 거버넌스와 신뢰 워크플로우
- 세션 라이프사이클 제어 (resume/fork) 및 고급 worktree 라이프사이클 제어
- MCP 런타임 전반의 세부 사항 (transport/OAuth/리소스 subscribe/polling)

이 레포의 팀 JSONL mailbox 프로토콜은 어디까지나 교육용 구현이며, 특정 production 내부 구조에 대한 주장이 아닙니다.

## 빠른 시작

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env   # Edit .env with your ANTHROPIC_API_KEY

python agents/s01_agent_loop.py       # Start here
python agents/s12_worktree_task_isolation.py  # Full progression endpoint
python agents/s_full.py               # Capstone: all mechanisms combined
```

### 웹 플랫폼

인터랙티브 시각화, 단계별 다이어그램, 소스 뷰어, 그리고 문서를 한 곳에서 볼 수 있습니다.

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## 학습 경로

```
Phase 1: THE LOOP                    Phase 2: PLANNING & KNOWLEDGE
==================                   ==============================
s01  The Agent Loop          [1]     s03  TodoWrite               [5]
     while + stop_reason                  TodoManager + nag reminder
     |                                    |
     +-> s02  Tool Use            [4]     s04  Subagents            [5]
              dispatch map: name->handler     fresh messages[] per child
                                              |
                                         s05  Skills               [5]
                                              SKILL.md via tool_result
                                              |
                                         s06  Context Compact      [5]
                                              3-layer compression

Phase 3: PERSISTENCE                 Phase 4: TEAMS
==================                   =====================
s07  Tasks                   [8]     s09  Agent Teams             [9]
     file-based CRUD + deps graph         teammates + JSONL mailboxes
     |                                    |
s08  Background Tasks        [6]     s10  Team Protocols          [12]
     daemon threads + notify queue        shutdown + plan approval FSM
                                          |
                                     s11  Autonomous Agents       [14]
                                          idle cycle + auto-claim
                                     |
                                     s12  Worktree Isolation      [16]
                                          task coordination + optional isolated execution lanes

                                     [N] = number of tools
```

## 아키텍처

```
learn-claude-code/
|
|-- agents/                        # Python reference implementations (s01-s12 + s_full capstone)
|-- docs/{en,zh,ja,ko}/            # Mental-model-first documentation (4 languages)
|-- web/                           # Interactive learning platform (Next.js)
|-- skills/                        # Skill files for s05
+-- .github/workflows/ci.yml      # CI: typecheck + build
```

## 문서

멘탈 모델 우선: 문제, 해결책, ASCII 다이어그램, 그리고 최소한의 코드.
지원 언어: [English](./docs/en/) | [中文](./docs/zh/) | [日本語](./docs/ja/) | [한국어](./docs/ko/).

| 세션 | 주제 | 모토 |
|---------|-------|-------|
| [s01](./docs/en/s01-the-agent-loop.md) | The Agent Loop | *루프 하나와 Bash면 충분하다* |
| [s02](./docs/en/s02-tool-use.md) | Tool Use | *tool을 더한다는 건 핸들러 하나를 더하는 것* |
| [s03](./docs/en/s03-todo-write.md) | TodoWrite | *계획 없는 agent는 표류한다* |
| [s04](./docs/en/s04-subagent.md) | Subagents | *큰 task는 쪼개라. 각 서브 task에는 깨끗한 context를 주어라* |
| [s05](./docs/en/s05-skill-loading.md) | Skills | *지식은 미리가 아니라, 필요할 때 로드하라* |
| [s06](./docs/en/s06-context-compact.md) | Context Compact | *context는 결국 차오른다. 자리를 비워줄 수단이 필요하다* |
| [s07](./docs/en/s07-task-system.md) | Tasks | *큰 목표는 작은 task로 쪼개고, 순서를 매기고, 디스크에 영속화하라* |
| [s08](./docs/en/s08-background-tasks.md) | Background Tasks | *느린 작업은 백그라운드로 돌려라. agent는 계속 생각한다* |
| [s09](./docs/en/s09-agent-teams.md) | Agent Teams | *한 agent로 감당이 안 되는 task는 팀원에게 위임하라* |
| [s10](./docs/en/s10-team-protocols.md) | Team Protocols | *팀원들에게는 공유된 커뮤니케이션 규칙이 필요하다* |
| [s11](./docs/en/s11-autonomous-agents.md) | Autonomous Agents | *팀원들은 보드를 스캔해 스스로 task를 가져간다* |
| [s12](./docs/en/s12-worktree-task-isolation.md) | Worktree + Task Isolation | *각자는 자기 디렉터리에서 일하고, 서로 간섭하지 않는다* |

## 다음 단계 — 이해에서 출시까지

12개 세션을 마치면 harness engineering이 안팎으로 어떻게 동작하는지 알게 됩니다. 그 지식을 실제로 굴리는 두 가지 길이 있습니다.

### Kode Agent CLI — 오픈소스 코딩 Agent CLI

> `npm i -g @shareai-lab/kode`

Skill과 LSP를 지원하고, Windows에서 바로 동작하며, GLM / MiniMax / DeepSeek 등 오픈 모델과 플러그형으로 붙입니다. 설치하면 끝.

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK — 당신의 앱에 Agent 기능을 임베드

공식 Claude Code Agent SDK는 내부적으로 풀 CLI 프로세스와 통신합니다 — 동시 사용자 한 명마다 별도의 터미널 프로세스가 뜬다는 뜻입니다. Kode SDK는 사용자당 프로세스 오버헤드가 없는 독립 라이브러리로, 백엔드, 브라우저 확장, 임베디드 기기, 그 어떤 런타임에도 끼워 넣을 수 있습니다.

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## 자매 레포: *필요할 때만 켜는 세션*에서 *항상 켜져 있는 비서*로

이 레포가 가르치는 harness는 **쓰고 버리는** 방식입니다 — 터미널을 열어 agent에게 task를 주고, 끝나면 닫고, 다음 세션은 빈 상태에서 다시 시작합니다. 그게 Claude Code 모델입니다.

[OpenClaw](https://github.com/openclaw/openclaw)는 또 다른 가능성을 증명했습니다. 같은 agent 코어 위에 단 두 개의 harness 메커니즘을 더하면, agent는 "쿡 찔러야 움직이는 존재"에서 "30초마다 깨어나 할 일이 있나 살피는 존재"로 바뀝니다.

- **Heartbeat** — 30초마다 harness가 agent에게 메시지를 보내 할 일이 있는지 묻습니다. 없으면? 다시 잡니다. 있으면? 즉시 행동합니다.
- **Cron** — agent가 자기 자신의 미래 task를 스케줄해 두면, 시간이 되었을 때 자동으로 실행됩니다.

여기에 멀티채널 IM 라우팅 (WhatsApp / Telegram / Slack / Discord 등 13개 이상의 플랫폼), 영속적인 context 메모리, 그리고 Soul 성격 시스템을 더하면, agent는 일회용 도구에서 항상 켜져 있는 개인 AI 비서로 진화합니다.

**[claw0](https://github.com/shareAI-lab/claw0)** 는 이러한 harness 메커니즘을 밑바닥부터 해체해 보여주는 우리의 동반 교육용 레포입니다.

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(agent harness core:                (proactive always-on harness:
 loop, tools, planning,              heartbeat, cron, IM channels,
 teams, worktree isolation)          memory, soul personality)
```

## 소개
<img width="260" src="https://github.com/user-attachments/assets/fe8b852b-97da-4061-a467-9694906b5edf" /><br>

WeChat으로 스캔해 팔로우하거나,
X에서 팔로우하세요: [shareAI-Lab](https://x.com/baicai003)

## 라이선스

MIT

---

**Agency는 모델에서 나옵니다. Harness는 그 agency를 현실로 만듭니다. 훌륭한 harness를 만드세요. 나머지는 모델이 해냅니다.**

**Bash 하나면 충분합니다. 우주에 필요한 건 진짜 agent뿐입니다.**
