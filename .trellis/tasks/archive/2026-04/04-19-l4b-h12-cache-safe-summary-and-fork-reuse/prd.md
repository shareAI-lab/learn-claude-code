# L4-b: H12 cache-safe summary and fork reuse

## Goal

补齐 H12 最接近 Claude Code fork 价值的部分：cache-safe summary 和 fork reuse。

## Requirements

* summary 必须尽量复用已有 fork/cache-safe params
* fork reuse 必须保持 prefix continuity
* 不为旧 placeholder/replacement 形态做兼容层

## Acceptance Criteria

* [ ] background fork summary 能复用 cache-safe continuity
* [ ] fork reuse 不破坏 prompt/tool identity contract
* [ ] summary/reuse 走统一 fork continuity seam
