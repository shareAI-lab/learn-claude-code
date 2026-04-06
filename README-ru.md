[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md) | [Русский](./README-ru.md)
# Learn Claude Code -- Harness Engineering для настоящих агентов

## Model -- это и есть Agent

Прежде чем говорить о коде, давайте раз и навсегда расставим всё по своим местам.

**Agent -- это model. Не фреймворк. Не цепочка промптов. Не drag-and-drop рабочий процесс.**

### Что такое Agent

Agent -- это нейронная сеть: Transformer, RNN, обученная функция, которая через миллиарды шагов градиентного спуска на данных о последовательностях действий научилась воспринимать окружающую среду, рассуждать о целях и совершать действия для их достижения. Слово «agent» в сфере ИИ всегда означало именно это. Всегда.

Человек -- это agent. Биологическая нейронная сеть, сформированная миллионами лет эволюционного обучения, воспринимающая мир через органы чувств, рассуждающая с помощью мозга, действующая посредством тела. Когда DeepMind, OpenAI или Anthropic говорят «agent», они имеют в виду то же самое, что это слово означало с самого начала существования области: **model, которая научилась действовать.**

Доказательство написано историей:

- **2013 -- DeepMind DQN играет в Atari.** Одна нейронная сеть, получая только сырые пиксели и игровые счета, научилась играть в 7 игр для Atari 2600 -- превзойдя все предыдущие алгоритмы и победив экспертов-людей в 3 из них. К 2015 году та же архитектура масштабировалась до [49 игр и сравнялась с профессиональными тестировщиками](https://www.nature.com/articles/nature14236), публикация в *Nature*. Никаких игровых правил, никаких деревьев решений. Одна model, обучающаяся на опыте. Эта model и была agent.

- **2019 -- OpenAI Five покоряет Dota 2.** Пять нейронных сетей, сыгравших [45 000 лет Dota 2](https://openai.com/index/openai-five-defeats-dota-2-world-champions/) против самих себя за 10 месяцев, победили **OG** -- действующих чемпионов мира TI8 -- со счётом 2:0 в прямом эфире из Сан-Франциско. В последующем публичном турнире ИИ выиграл 99,4% из 42 729 партий против всех желающих. Никаких заскриптованных стратегий. Никакой заранее запрограммированной командной координации. Model сами научились командной работе, тактике и адаптации в реальном времени исключительно через самоигру.

- **2019 -- DeepMind AlphaStar осваивает StarCraft II.** AlphaStar [победил профессиональных игроков со счётом 10:1](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/) в закрытом матче, а позднее достиг [статуса Grandmaster](https://www.nature.com/articles/d41586-019-03298-6) на европейских серверах -- войдя в топ 0,15% из 90 000 игроков. Игра с неполной информацией, решениями в реальном времени и комбинаторным пространством действий, многократно превосходящим шахматы и го. Agent? Model. Обученная. Не заскриптованная.

- **2019 -- Tencent Jueyu доминирует в Honor of Kings.** «Jueyu» от Tencent AI Lab [победила профессиональных игроков KPL](https://www.jiemian.com/article/3371171.html) в полноценном матче 5v5 на World Champion Cup. В режиме 1v1 профессионалы выиграли лишь [1 из 15 игр и ни разу не пережили 8 минут](https://developer.aliyun.com/article/851058). Интенсивность обучения: один день равнялся 440 человеческим годам. К 2021 году Jueyu превзошла профессионалов KPL по всему пулу героев. Никаких ручных таблиц матчапов. Никаких заскриптованных составов. Model, выучившая всю игру с нуля через самоигру.

- **2024-2025 -- LLM agents меняют облик разработки ПО.** Claude, GPT, Gemini -- большие языковые model, обученные на всём массиве человеческого кода и рассуждений, -- разворачиваются как coding agents. Они читают кодовые базы, пишут реализации, отлаживают ошибки, координируют работу в командах. Архитектура идентична всем предыдущим agents: обученная model, помещённая в среду и снабжённая tools для восприятия и действия. Единственное отличие -- масштаб усвоенного и универсальность решаемых задач.

Каждое из этих достижений подтверждает одно: **«agent» -- это никогда не окружающий код. Agent -- это всегда model.**

### Чем Agent не является

Слово «agent» было присвоено целой индустрией по прокладке промптов.

Drag-and-drop конструкторы рабочих процессов. No-code платформы «AI agents». Библиотеки оркестрации цепочек промптов. Все они разделяют одно заблуждение: что соединение вызовов LLM API через ветки if-else, графы узлов и жёстко прошитую логику маршрутизации -- это «создание agent».

Это не так. То, что они строят, -- машина Рубе Голдберга: чрезмерно сложный, хрупкий конвейер из процедурных правил, куда LLM вставлен как раздутая нода завершения текста. Это не agent. Это shell-скрипт с манией величия.

**«Agents» из промпт-водопроводов -- это фантазия программистов, которые не обучают model.** Они пытаются брутфорсом получить интеллект, нагромождая процедурную логику -- огромные деревья правил, графы узлов, каскады цепочек промптов -- и молясь, что достаточное количество связующего кода каким-то образом породит автономное поведение. Не породит. Нельзя сконструировать агентность. Агентность -- это результат обучения, а не программирования.

Такие системы мертворождённые: хрупкие, немасштабируемые, принципиально неспособные к обобщению. Это современное воскрешение GOFAI (Good Old-Fashioned AI) -- символических систем правил, от которых область отказалась десятилетия назад, теперь покрашенных в цвет LLM. Другая упаковка, тот же тупик.

### Смена мышления: от «разработки agents» к разработке Harness

Когда кто-то говорит «я разрабатываю agent», это может означать лишь одно из двух:

**1. Обучение model.** Корректировка весов через reinforcement learning, дообучение, RLHF или другие методы на основе градиентного спуска. Сбор данных о процессе выполнения задач -- реальных последовательностей восприятия, рассуждения и действия в реальных областях -- и использование их для формирования поведения model. Именно этим занимаются DeepMind, OpenAI, Tencent AI Lab и Anthropic. Это разработка agent в истинном смысле слова.

**2. Создание harness.** Написание кода, дающего model среду для работы. Это то, чем занимаемся большинство из нас, и это -- тема данного репозитория.

Harness -- это всё, что нужно agent для функционирования в конкретной области:

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

    Tools:          file I/O, shell, network, database, browser
    Knowledge:      product docs, domain references, API specs, style guides
    Observation:    git diff, error logs, browser state, sensor data
    Action:         CLI commands, API calls, UI interactions
    Permissions:    sandboxing, approval workflows, trust boundaries
```

Model принимает решения. Harness их исполняет. Model рассуждает. Harness предоставляет context. Model -- водитель. Harness -- транспортное средство.

**Harness coding agent -- это его IDE, терминал и доступ к файловой системе.** Harness фермерского agent -- это массив датчиков, управление орошением и потоки погодных данных. Harness гостиничного agent -- это система бронирования, каналы общения с гостями и API управления объектом. Agent -- интеллект, принимающий решения -- всегда model. Harness меняется в зависимости от области. Agent обобщается на все области.

Этот репозиторий учит создавать транспортные средства. Транспортные средства для написания кода. Но паттерны проектирования применимы к любой области: управление фермой, гостиничный бизнес, производство, логистика, здравоохранение, образование, научные исследования. Везде, где задачу нужно воспринять, осмыслить и выполнить -- agent нужен harness.

### Что на самом деле делают Harness Engineers

Если вы читаете этот репозиторий, скорее всего, вы harness engineer -- и это очень сильная позиция. Вот ваша настоящая работа:

- **Реализуйте tools.** Дайте agent руки. Чтение/запись файлов, выполнение shell-команд, вызовы API, управление браузером, запросы к базам данных. Каждый tool -- это действие, которое agent может совершить в своей среде. Проектируйте их атомарными, компонуемыми и хорошо описанными.

- **Курируйте knowledge.** Дайте agent экспертизу в области. Документация продукта, записи об архитектурных решениях, руководства по стилю, нормативные требования. Загружайте по требованию (s05), а не заранее. Agent должен знать, что доступно, и брать то, что нужно.

- **Управляйте context.** Дайте agent чистую память. Изоляция subagent (s04) предотвращает утечку шума. Сжатие context (s06) предотвращает переполнение историей. Системы задач (s07) сохраняют цели за пределами одного разговора.

- **Контролируйте permissions.** Задайте agent границы. Ограничьте доступ к файлам через sandbox. Требуйте подтверждения для деструктивных операций. Соблюдайте границы доверия между agent и внешними системами. Здесь безопасность встречается с harness engineering.

- **Собирайте данные о процессе выполнения задач.** Каждая последовательность действий, которую agent выполняет в вашем harness, -- это обучающий сигнал. Трассировки восприятия-рассуждения-действия из реальных развёртываний -- это сырой материал для дообучения следующего поколения model agents. Ваш harness не просто обслуживает agent -- он может помочь его улучшить.

Вы пишете не интеллект. Вы строите мир, в котором этот интеллект живёт. Качество этого мира -- насколько чётко agent воспринимает, насколько точно действует, насколько богаты его доступные знания -- напрямую определяет, насколько эффективно интеллект может себя проявить.

**Стройте отличные harnesses. Agent сделает остальное.**

### Почему Claude Code -- мастер-класс по Harness Engineering

Почему этот репозиторий препарирует именно Claude Code?

Потому что Claude Code -- это самый элегантный и полноценно реализованный harness для agent, который нам доводилось видеть. Не из-за какого-то одного умного трюка, а из-за того, чего он *не делает*: он не пытается быть agent. Он не навязывает жёстких рабочих процессов. Он не перепроверяет model сложными деревьями решений. Он снабжает model tools, knowledge, управлением context и границами permissions -- а затем уходит с дороги.

Посмотрите, что такое Claude Code в своей сути:

```
Claude Code = один agent loop
            + tools (bash, read, write, edit, glob, grep, browser...)
            + on-demand skill loading
            + context compression
            + subagent spawning
            + task system with dependency graph
            + team coordination with async mailboxes
            + worktree isolation for parallel execution
            + permission governance
```

Вот и всё. Вся архитектура целиком. Каждый компонент -- это механизм harness: кусочек мира, построенный для agent. Сам agent? Это Claude. Model. Обученная Anthropic на всём массиве человеческого мышления и кода. Harness не делает Claude умным. Claude уже умён. Harness даёт Claude руки, глаза и рабочее пространство.

Вот почему Claude Code -- идеальный предмет для изучения: **он демонстрирует, что происходит, когда вы доверяете model и сосредотачиваете свои инженерные усилия на harness.** Каждая сессия в этом репозитории (s01-s12) реконструирует один механизм harness из архитектуры Claude Code. По завершении вы понимаете не только то, как работает Claude Code, но и универсальные принципы harness engineering, применимые к любому agent в любой области.

Урок не в том, чтобы «скопировать Claude Code». Урок таков: **лучшие продукты на основе agents создают инженеры, понимающие, что их работа -- это harness, а не интеллект.**

---

## Видение: наполнить вселенную настоящими Agents

Это не только про coding agents.

В каждой области, где люди выполняют сложную, многоэтапную работу, требующую суждений, могут работать agents -- при наличии правильного harness. Паттерны этого репозитория универсальны:

```
Estate management agent    = model + property sensors + maintenance tools + tenant comms
Agricultural agent         = model + soil/weather data + irrigation controls + crop knowledge
Hotel operations agent     = model + booking system + guest channels + facility APIs
Medical research agent     = model + literature search + lab instruments + protocol docs
Manufacturing agent        = model + production line sensors + quality controls + logistics
Education agent            = model + curriculum knowledge + student progress + assessment tools
```

Loop всегда один и тот же. Tools меняются. Knowledge меняется. Permissions меняются. Agent -- model -- обобщается на всё.

Каждый harness engineer, читающий этот репозиторий, осваивает паттерны, применимые далеко за пределами разработки ПО. Вы учитесь строить инфраструктуру для интеллектуального автоматизированного будущего. Каждый хорошо спроектированный harness, развёрнутый в реальной области, -- это ещё одно место, где agent может воспринимать, рассуждать и действовать.

Сначала мы заполняем мастерские. Затем фермы, больницы, заводы. Потом города. Потом планету.

**Bash is all you need. Real agents are all the universe needs.**

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

**12 последовательных сессий: от простого loop до изолированного автономного выполнения.**
**Каждая сессия добавляет один механизм harness. У каждого механизма -- своё motto.**

> **s01** &nbsp; *"Один loop и Bash -- это всё, что нужно"* &mdash; один tool + один loop = agent
>
> **s02** &nbsp; *"Добавить tool -- значит добавить один обработчик"* &mdash; loop остаётся прежним; новые tools регистрируются в таблице диспетчеризации
>
> **s03** &nbsp; *"Agent без плана блуждает"* &mdash; сначала составь список шагов, потом выполняй; завершаемость удваивается
>
> **s04** &nbsp; *"Дели большие задачи; каждая подзадача получает чистый context"* &mdash; subagents используют независимые messages[], сохраняя главный разговор чистым
>
> **s05** &nbsp; *"Загружай knowledge тогда, когда это нужно, а не заранее"* &mdash; передавай через tool_result, а не через system prompt
>
> **s06** &nbsp; *"Context заполняется; нужен способ освободить место"* &mdash; трёхуровневая стратегия сжатия для бесконечных сессий
>
> **s07** &nbsp; *"Дели большие цели на малые задачи, упорядочивай их, сохраняй на диск"* &mdash; файловый граф задач с зависимостями, закладывающий основу для многоагентного сотрудничества
>
> **s08** &nbsp; *"Запускай медленные операции в фоне; agent продолжает думать"* &mdash; daemon threads выполняют команды и отправляют уведомления по завершении
>
> **s09** &nbsp; *"Когда задача слишком велика для одного -- делегируй товарищам по команде"* &mdash; постоянные teammates + async mailboxes
>
> **s10** &nbsp; *"Teammates нужны общие правила коммуникации"* &mdash; один паттерн запрос-ответ управляет всеми переговорами
>
> **s11** &nbsp; *"Teammates сами просматривают доску и берут задачи"* &mdash; лидеру не нужно назначать каждую задачу вручную
>
> **s12** &nbsp; *"Каждый работает в своей директории, без помех"* &mdash; tasks управляют целями, worktrees управляют директориями, связанными по ID

---

## Основной паттерн

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

Каждая сессия добавляет один механизм harness поверх этого loop -- не изменяя сам loop. Loop принадлежит agent. Механизмы принадлежат harness.

## Область охвата (важно)

Этот репозиторий -- учебный проект уровня 0->1 по harness engineering: построению среды, окружающей model-agent.
Намеренно упрощены или опущены некоторые производственные механизмы:

- Полные шины событий/хуков (например, PreToolUse, SessionStart/End, ConfigChange).
  s12 включает только минимальный append-only поток событий жизненного цикла в учебных целях.
- Управление permissions на основе правил и рабочие процессы доверия
- Управление жизненным циклом сессии (resume/fork) и расширенное управление жизненным циклом worktree
- Полные детали MCP runtime (transport/OAuth/resource subscribe/polling)

Рассматривайте протокол team JSONL mailbox в этом репозитории как учебную реализацию, а не как утверждение о каких-либо конкретных производственных внутренностях.

## Быстрый старт

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env   # Edit .env with your ANTHROPIC_API_KEY

python agents/s01_agent_loop.py       # Start here
python agents/s12_worktree_task_isolation.py  # Full progression endpoint
python agents/s_full.py               # Capstone: all mechanisms combined
```

### Веб-платформа

Интерактивные визуализации, пошаговые диаграммы, просмотр исходного кода и документация.

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## Путь обучения

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

## Архитектура

```
learn-claude-code/
|
|-- agents/                        # Python reference implementations (s01-s12 + s_full capstone)
|-- docs/{en,zh,ja}/               # Mental-model-first documentation (3 languages)
|-- web/                           # Interactive learning platform (Next.js)
|-- skills/                        # Skill files for s05
+-- .github/workflows/ci.yml      # CI: typecheck + build
```

## Документация

Подход «сначала ментальная модель»: проблема, решение, ASCII-диаграмма, минимальный код.
Доступно на [English](./docs/en/) | [中文](./docs/zh/) | [日本語](./docs/ja/) | [Русский](./docs/ru/).

| Сессия | Тема | Motto |
|---------|-------|-------|
| [s01](./docs/ru/s01-the-agent-loop.md) | The Agent Loop | *Один loop и Bash -- это всё, что нужно* |
| [s02](./docs/ru/s02-tool-use.md) | Tool Use | *Добавить tool -- значит добавить один обработчик* |
| [s03](./docs/ru/s03-todo-write.md) | TodoWrite | *Agent без плана блуждает* |
| [s04](./docs/ru/s04-subagent.md) | Subagents | *Дели большие задачи; каждая подзадача получает чистый context* |
| [s05](./docs/ru/s05-skill-loading.md) | Skills | *Загружай knowledge тогда, когда это нужно, а не заранее* |
| [s06](./docs/ru/s06-context-compact.md) | Context Compact | *Context заполняется; нужен способ освободить место* |
| [s07](./docs/ru/s07-task-system.md) | Tasks | *Дели большие цели на малые задачи, упорядочивай их, сохраняй на диск* |
| [s08](./docs/ru/s08-background-tasks.md) | Background Tasks | *Запускай медленные операции в фоне; agent продолжает думать* |
| [s09](./docs/ru/s09-agent-teams.md) | Agent Teams | *Когда задача слишком велика для одного -- делегируй teammates* |
| [s10](./docs/ru/s10-team-protocols.md) | Team Protocols | *Teammates нужны общие правила коммуникации* |
| [s11](./docs/ru/s11-autonomous-agents.md) | Autonomous Agents | *Teammates сами просматривают доску и берут задачи* |
| [s12](./docs/ru/s12-worktree-task-isolation.md) | Worktree + Task Isolation | *Каждый работает в своей директории, без помех* |

## Что дальше -- от понимания к созданию продуктов

После 12 сессий вы понимаете harness engineering изнутри и снаружи. Два способа применить эти знания:

### Kode Agent CLI -- CLI coding agent с открытым исходным кодом

> `npm i -g @shareai-lab/kode`

Поддержка Skill и LSP, готовность к Windows, совместимость с GLM / MiniMax / DeepSeek и другими открытыми model. Устанавливайте и работайте.

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- встраивайте возможности Agent в своё приложение

Официальный Claude Code Agent SDK взаимодействует с полноценным CLI-процессом под капотом -- каждый одновременный пользователь означает отдельный процесс терминала. Kode SDK -- это автономная библиотека без накладных расходов на процесс для каждого пользователя, встраиваемая в бэкенды, расширения браузера, встраиваемые устройства или любую среду выполнения.

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## Родственный репозиторий: от *сессий по запросу* до *постоянно работающего ассистента*

Harness, которому учит этот репозиторий, -- **использовать и выбрасывать**: открыл терминал, дал agent задачу, закрыл по завершении, следующая сессия начинается с чистого листа. Такова модель Claude Code.

[OpenClaw](https://github.com/openclaw/openclaw) доказал другую возможность: поверх того же ядра agent два механизма harness превращают agent из «ткни, чтобы он двинулся» в «просыпается каждые 30 секунд, чтобы проверить, есть ли работа»:

- **Heartbeat** -- каждые 30 секунд harness отправляет agent сообщение: есть ли что-то, что нужно сделать? Нет? Обратно спать. Есть? Действовать немедленно.
- **Cron** -- agent может планировать свои будущие задачи, которые автоматически выполняются в нужное время.

Добавьте многоканальную IM-маршрутизацию (WhatsApp / Telegram / Slack / Discord, 13+ платформ), постоянную память context и систему личности Soul -- и agent превратится из одноразового инструмента в постоянно работающего персонального ИИ-ассистента.

**[claw0](https://github.com/shareAI-lab/claw0)** -- наш сопутствующий учебный репозиторий, деконструирующий эти механизмы harness с нуля:

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(agent harness core:                (proactive always-on harness:
 loop, tools, planning,              heartbeat, cron, IM channels,
 teams, worktree isolation)          memory, soul personality)
```

## О нас
<img width="260" src="https://github.com/user-attachments/assets/fe8b852b-97da-4061-a467-9694906b5edf" /><br>

Сканируйте WeChat, чтобы подписаться,
или следите в X: [shareAI-Lab](https://x.com/baicai003)

## Лицензия

MIT

---

**Model -- это agent. Код -- это harness. Стройте отличные harnesses. Agent сделает остальное.**

**Bash is all you need. Real agents are all the universe needs.**
