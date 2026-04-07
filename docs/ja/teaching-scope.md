# 教材の守備範囲

> この文書は、この教材が何を教え、何を意図的に主線から外すかを明示するためのものです。

## この教材の目標

これは、ある実運用コードベースを逐行で注釈するためのリポジトリではありません。

本当の目標は:

**高完成度の coding-agent harness を 0 から自力で作れるようにすること**

です。

そのために守るべき条件は 3 つあります。

1. 学習者が本当に自分で作り直せること
2. 主線が side detail に埋もれないこと
3. 実在しない mechanism を学ばせないこと

## 主線章で必ず明示すべきこと

各章は次をはっきりさせるべきです。

- その mechanism が何の問題を解くか
- どの module / layer に属するか
- どんな state を持つか
- どんな data structure を導入するか
- loop にどうつながるか
- runtime flow がどう変わるか

## 主線を支配させない方がよいもの

次の話題は存在してよいですが、初心者向け主線の中心に置くべきではありません。

- packaging / build / release flow
- cross-platform compatibility glue
- telemetry / enterprise policy wiring
- historical compatibility branches
- product 固有の naming accident
- 上流コードとの逐行一致

## ここでいう高忠実度とは何か

高忠実度とは、すべての周辺 detail を 1:1 で再現することではありません。

ここで寄せるべき対象は:

- core runtime model
- module boundaries
- key records
- state transitions
- major subsystem cooperation

つまり:

**幹には忠実に、枝葉は教材として意識的に簡略化する**

ということです。

## 想定読者

標準的な想定読者は:

- 基本的な Python は読める
- 関数、クラス、list、dict は分かる
- ただし agent platform は初学者でもよい

したがって文章は:

- 先に概念を説明する
- 1つの概念を1か所で完結させる
- `what -> why -> how` の順で進める

のが望ましいです。

## 各章の推奨構成

1. これが無いと何が困るか
2. 先に新しい言葉を説明する
3. 最小の心智モデルを示す
4. 主要 record / data structure を示す
5. 最小で正しい実装を示す
6. loop への接続点を示す
7. 初学者がやりがちな誤りを示す
8. 高完成度版で後から足すものを示す

## 用語の扱い

次の種類の語が出るときは、名前だけ投げず意味を説明した方がよいです。

- design pattern
- data structure
- concurrency term
- protocol / networking term
- 一般的ではない engineering vocabulary

例:

- state machine
- scheduler
- queue
- worktree
- DAG
- protocol envelope

## 最小正解版の原則

現実の mechanism は複雑でも、教材は最初から全分岐を見せる必要はありません。

よい順序は:

1. 最小で正しい版を示す
2. それで既に解ける core problem を示す
3. 後で何を足すかを示す

例:

- permission: `deny -> mode -> allow -> ask`
- error recovery: 主要な回復枝から始める
- task system: records / dependencies / unlocks から始める
- team protocol: request / response + `request_id` から始める

## 逆向きソースの使い方

逆向きで得たソースは:

**保守者の校正材料**

として使うのが正しいです。

役割は:

- 主線 mechanism の説明がズレていないか確かめる
- 重要な境界や record が抜けていないか確かめる
- 教材実装が fiction に流れていないか確かめる

読者がそれを見ないと本文を理解できない構成にしてはいけません。

## 一文で覚える

**よい教材は、細部をたくさん言うことより、重要な細部を完全に説明し、重要でない細部を安全に省くことによって質が決まります。**
