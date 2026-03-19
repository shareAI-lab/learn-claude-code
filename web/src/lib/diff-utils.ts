import { diffLines } from "diff";

export function computeDiffRows(oldSource: string, newSource: string) {
  const changes = diffLines(oldSource, newSource);
  let oldLine = 1;
  let newLine = 1;

  const rows: {
    oldNum: number | null;
    newNum: number | null;
    type: "add" | "remove" | "context";
    text: string;
  }[] = [];

  for (const change of changes) {
    const lines = change.value.replace(/\n$/, "").split("\n");
    for (const line of lines) {
      if (change.added) {
        rows.push({ oldNum: null, newNum: newLine++, type: "add", text: line });
      } else if (change.removed) {
        rows.push({
          oldNum: oldLine++,
          newNum: null,
          type: "remove",
          text: line,
        });
      } else {
        rows.push({
          oldNum: oldLine++,
          newNum: newLine++,
          type: "context",
          text: line,
        });
      }
    }
  }
  return rows;
}
