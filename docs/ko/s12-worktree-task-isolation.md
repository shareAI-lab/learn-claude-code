# s12: Worktree + 태스크 격리

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *"각자 자기 디렉터리에서 일한다, 서로 간섭하지 않는다"* -- 태스크는 목표를 관리하고, worktree (워크트리 — git worktree, 같은 저장소를 여러 디렉터리에 동시에 체크아웃하는 기능)는 디렉터리를 관리하며, ID로 묶여 있습니다.
>
> **하네스 레이어**: 디렉터리 격리(Directory isolation) -- 절대 충돌하지 않는 병렬 실행 레인.

## 문제

s11에 이르러 에이전트들은 자율적으로 태스크를 claim하고 완료할 수 있습니다. 하지만 모든 태스크가 하나의 shared 디렉터리에서 돌아갑니다. 두 에이전트가 동시에 다른 모듈을 리팩터링하면 충돌이 납니다. 에이전트 A가 `config.py`를 수정하고, 에이전트 B도 `config.py`를 수정하면 unstaged 변경 사항이 뒤섞여 어느 쪽도 깔끔하게 롤백할 수 없습니다.

task board는 *무엇을 할지*는 추적하지만 *어디서 할지*에 대해서는 아무 의견이 없습니다. 해결책은 이렇습니다. 각 태스크에 자신만의 git worktree 디렉터리를 줍니다. 태스크는 목표를 관리하고 worktree는 실행 컨텍스트를 관리합니다. 둘은 태스크 ID로 묶입니다.

## 해결책

```
Control plane (.tasks/)             Execution plane (.worktrees/)
+------------------+                +------------------------+
| task_1.json      |                | auth-refactor/         |
|   status: in_progress  <------>   branch: wt/auth-refactor
|   worktree: "auth-refactor"   |   task_id: 1             |
+------------------+                +------------------------+
| task_2.json      |                | ui-login/              |
|   status: pending    <------>     branch: wt/ui-login
|   worktree: "ui-login"       |   task_id: 2             |
+------------------+                +------------------------+
                                    |
                          index.json (worktree registry)
                          events.jsonl (lifecycle log)

State machines:
  Task:     pending -> in_progress -> completed
  Worktree: absent  -> active      -> removed | kept
```

## 동작 원리

1. **태스크를 생성합니다.** 먼저 목표를 영속화합니다.

```python
TASKS.create("Implement auth refactor")
# -> .tasks/task_1.json  status=pending  worktree=""
```

2. **worktree를 만들고 태스크에 바인딩합니다.** `task_id`를 전달하면 태스크가 자동으로 `in_progress`로 진행됩니다.

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json gets new entry, task_1.json gets worktree="auth-refactor"
```

바인딩은 양쪽에 상태를 기록합니다.

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

3. **worktree에서 명령을 실행합니다.** `cwd`가 격리된 디렉터리를 가리킵니다.

```python
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

4. **마무리합니다.** 두 가지 선택지가 있습니다:
   - `worktree_keep(name)` -- 디렉터리를 나중을 위해 보존합니다.
   - `worktree_remove(name, complete_task=True)` -- 디렉터리를 제거하고, 바인딩된 태스크를 완료 처리하며, 이벤트를 emit합니다. 한 번의 호출로 teardown + 완료가 함께 처리됩니다.

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

5. **event stream.** 모든 lifecycle 단계는 `.worktrees/events.jsonl`로 emit됩니다.

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

emit되는 이벤트: `worktree.create.before/after/failed`, `worktree.remove.before/after/failed`, `worktree.keep`, `task.completed`.

크래시가 발생하면, 디스크 위의 `.tasks/` + `.worktrees/index.json`로부터 상태가 재구성됩니다. 대화 메모리는 휘발성이지만, 파일 상태는 영속적입니다.

## s11에서 무엇이 바뀌었나

| 구성 요소           | 이전 (s11)                  | 이후 (s12)                                     |
|--------------------|----------------------------|------------------------------------------------|
| 조율               | task board (소유자/상태)    | task board + 명시적인 worktree 바인딩          |
| 실행 범위          | 공유 디렉터리                | 태스크 단위 격리 디렉터리                       |
| 복구 가능성        | 태스크 상태만                | 태스크 상태 + worktree 인덱스                  |
| Teardown           | 태스크 완료                  | 태스크 완료 + 명시적인 keep/remove             |
| Lifecycle 가시성   | 로그에 암묵적                | `.worktrees/events.jsonl`에 명시적 이벤트       |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s12_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.`
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".`
3. `Run "git status --short" in worktree "auth-refactor".`
4. `Keep worktree "ui-login", then list worktrees and inspect events.`
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.`
