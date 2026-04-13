# Cô lập task bằng worktree (Worktree Task Isolation)

> *Task trả lời cần làm gì; worktree trả lời làm ở đâu. Giữ hai thứ tách biệt giúp parallel work an toàn hơn.*

## Vấn Đề

Nhiều worker sửa cùng repo có thể conflict hoặc ghi đè nhau. Worktree isolation tạo lane filesystem riêng cho task hoặc actor.

## WorktreeRecord

Nên có:

- path
- task binding
- owner/actor
- status
- base branch/commit nếu cần
- closeout decision

## Luồng

```text
task claimed
  -> create or enter worktree
  -> run tools inside that path
  -> record changes
  -> closeout: keep, merge, discard, handoff
```

## TaskBinding

Binding nối task với lane execution, nhưng không gộp hai object. Task vẫn là goal; worktree vẫn là nơi thực thi.

## Closeout

Closeout quan trọng vì lane không tự biến mất khi task xong. Cần quyết định:

- giữ lại để review
- merge changes
- discard
- chuyển cho teammate khác
- mark blocked nếu conflict

## Ranh Giới

Worktree không thay permission. Shell/file tools vẫn phải chạy trong control plane. Worktree chỉ giới hạn nơi action xảy ra.

## Bài Tập Tối Thiểu

Tạo record bind task -> directory, đảm bảo command chạy trong directory đó, rồi ghi closeout status. Sau chương này, parallel work có lane rõ thay vì chen vào cùng workspace.
