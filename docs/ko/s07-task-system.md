# s07: 태스크 시스템

`s01 > s02 > s03 > s04 > s05 > s06 | [ s07 ] s08 > s09 > s10 > s11 > s12`

> *"Break big goals into small tasks, order them, persist to disk"* -- 의존성을 가진 파일 기반 task graph로, 멀티 에이전트 협업의 기반을 다집니다.
>
> **Harness layer**: 영속적인 task -- 단일 대화의 수명을 넘어서 살아남는 목표.

## 문제

s03의 TodoManager는 메모리에 떠 있는 평면적인 체크리스트입니다. 순서도, 의존성도 없고, 상태도 "끝났는지 아닌지" 둘 중 하나뿐입니다. 그러나 현실의 목표에는 구조가 있습니다 -- task B는 task A에 의존하고, task C와 D는 병렬로 실행 가능하며, task E는 C와 D가 모두 끝나기를 기다립니다.

명시적인 관계가 없으면 에이전트는 무엇이 준비됐는지, 무엇이 막혀 있는지, 무엇을 동시에 돌릴 수 있는지 알 수 없습니다. 게다가 목록이 메모리에만 존재하기 때문에 context 압축(s06)이 일어나면 그대로 사라져 버립니다.

## 해결책

체크리스트를 디스크에 영속화되는 **task graph**로 끌어올립니다. 각 task는 status와 의존성(`blockedBy`)을 가진 JSON 파일입니다. 이 graph는 매 순간 다음 세 가지 질문에 답할 수 있습니다.

- **무엇이 준비됐는가?** -- `pending` 상태이면서 `blockedBy`가 비어 있는 task.
- **무엇이 막혀 있는가?** -- 아직 끝나지 않은 dependency를 기다리는 task.
- **무엇이 완료됐는가?** -- `completed` task. 이들이 완료되면 의존 관계가 자동으로 풀립니다.

```
.tasks/
  task_1.json  {"id":1, "status":"completed"}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending"}
  task_3.json  {"id":3, "blockedBy":[1], "status":"pending"}
  task_4.json  {"id":4, "blockedBy":[2,3], "status":"pending"}

Task graph (DAG):
                 +----------+
            +--> | task 2   | --+
            |    | pending  |   |
+----------+     +----------+    +--> +----------+
| task 1   |                          | task 4   |
| completed| --> +----------+    +--> | blocked  |
+----------+     | task 3   | --+     +----------+
                 | pending  |
                 +----------+

Ordering:     task 1 must finish before 2 and 3
Parallelism:  tasks 2 and 3 can run at the same time
Dependencies: task 4 waits for both 2 and 3
Status:       pending -> in_progress -> completed
```

이 task graph는 s07 이후의 모든 것을 조율하는 중추가 됩니다. background 실행(s08), 멀티 에이전트 team(s09+), worktree 격리(s12) 모두가 동일한 구조를 읽고 씁니다.

## 동작 원리

1. **TaskManager**: task당 JSON 파일 하나, dependency graph와 함께 CRUD를 제공합니다.

```python
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def create(self, subject, description=""):
        task = {"id": self._next_id, "subject": subject,
                "status": "pending", "blockedBy": [],
                "owner": ""}
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)
```

2. **Dependency 해소**: 하나의 task를 완료하면 그 ID가 다른 모든 task의 `blockedBy` 목록에서 제거되어, 의존 task들이 자동으로 unblock 됩니다.

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **상태 + dependency 연결**: `update`가 상태 전이와 의존성 엣지를 함께 처리합니다.

```python
def update(self, task_id, status=None,
           add_blocked_by=None, remove_blocked_by=None):
    task = self._load(task_id)
    if status:
        task["status"] = status
        if status == "completed":
            self._clear_dependency(task_id)
    if add_blocked_by:
        task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
    if remove_blocked_by:
        task["blockedBy"] = [x for x in task["blockedBy"] if x not in remove_blocked_by]
    self._save(task)
```

4. 네 개의 task 도구를 dispatch map에 등록합니다.

```python
TOOL_HANDLERS = {
    # ...base tools...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

s07부터는 여러 단계로 이루어진 작업의 기본값이 task graph입니다. s03의 Todo는 단일 세션에서 빠르게 쓰는 체크리스트 용도로 남아 있습니다.

## s06에서 무엇이 바뀌었나

| 구성 요소 | 이전 (s06) | 이후 (s07) |
|---|---|---|
| Tools | 5 | 8 (`task_create/update/list/get`) |
| 계획 모델 | 평면 체크리스트 (인메모리) | 의존성을 가진 task graph (디스크) |
| 관계 | 없음 | `blockedBy` 엣지 |
| 상태 추적 | 완료 여부 | `pending` -> `in_progress` -> `completed` |
| 영속성 | 압축 시 소실 | 압축과 재시작 이후에도 유지 |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s07_task_system.py
```

1. `Create 3 tasks: "Setup project", "Write code", "Write tests". Make them depend on each other in order.`
2. `List all tasks and show the dependency graph`
3. `Complete task 1 and then list tasks to see task 2 unblocked`
4. `Create a task board for refactoring: parse -> transform -> emit -> test, where transform and emit can run in parallel after parse`
