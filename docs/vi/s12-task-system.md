# Hệ thống task (Task System)

> *Todo giúp một session; task system điều phối work bền vững sống lâu hơn session đó.*

## Vấn Đề

Một project lớn không thể chỉ dựa vào todo trong một chat. Work cần status, dependency, owner và khả năng resume.

`TaskRecord` là durable work goal.

## TaskRecord

Một task có thể gồm:

- id
- title / goal
- status
- dependencies
- assignee hoặc claimant
- notes / artifacts
- created/updated timestamps

## Dependency

Task graph cho biết việc nào bị block và việc nào được unlock khi dependency done.

```text
A done -> unlock B -> B can be claimed
```

## Todo vs Task

| Todo | Task |
|---|---|
| sống trong session | durable |
| giúp agent hiện tại tập trung | điều phối work lâu dài |
| ít metadata | có status/dependency/owner |
| không cần background runtime | có thể chạy nền hoặc schedule |

## Luồng

```text
create task records
  -> mark dependencies
  -> claim runnable task
  -> run work
  -> update status
  -> unlock next tasks
```

## Dừng Ở Đâu

Tối thiểu, làm task board in-memory hoặc file-backed có create/list/update và dependency unlock. Đừng thêm teams vội; trước hết task graph phải đứng độc lập.
