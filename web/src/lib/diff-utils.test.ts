import test from "node:test";
import assert from "node:assert";
import { computeDiffRows } from "./diff-utils.js";

test("computeDiffRows", async (t) => {
  await t.test("computes correct rows for added, removed, and context lines", () => {
    const oldSource = "line 1\nline 2\nline 3\nline 4";
    const newSource = "line 1\nline 2 changed\nline 3\nline 4 added\nline 5 added";

    const rows = computeDiffRows(oldSource, newSource);

    assert.deepStrictEqual(rows, [
      { oldNum: 1, newNum: 1, type: "context", text: "line 1" },
      { oldNum: 2, newNum: null, type: "remove", text: "line 2" },
      { oldNum: null, newNum: 2, type: "add", text: "line 2 changed" },
      { oldNum: 3, newNum: 3, type: "context", text: "line 3" },
      { oldNum: 4, newNum: null, type: "remove", text: "line 4" },
      { oldNum: null, newNum: 4, type: "add", text: "line 4 added" },
      { oldNum: null, newNum: 5, type: "add", text: "line 5 added" },
    ]);
  });

  await t.test("computes correct rows for identical sources", () => {
    const source = "line 1\nline 2";
    const rows = computeDiffRows(source, source);

    assert.deepStrictEqual(rows, [
      { oldNum: 1, newNum: 1, type: "context", text: "line 1" },
      { oldNum: 2, newNum: 2, type: "context", text: "line 2" },
    ]);
  });

  await t.test("computes correct rows for completely different sources", () => {
    const oldSource = "old 1\nold 2";
    const newSource = "new 1\nnew 2";

    const rows = computeDiffRows(oldSource, newSource);

    assert.deepStrictEqual(rows, [
      { oldNum: 1, newNum: null, type: "remove", text: "old 1" },
      { oldNum: 2, newNum: null, type: "remove", text: "old 2" },
      { oldNum: null, newNum: 1, type: "add", text: "new 1" },
      { oldNum: null, newNum: 2, type: "add", text: "new 2" },
    ]);
  });
});
