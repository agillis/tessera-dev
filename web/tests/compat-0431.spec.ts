// Updating from app 0.4.31 keeps what people have, in the editor too (app 0.4.32, the tile catalogue): every page the app
// of 0.4.31 saved in the compatibility corpus (tests/compat_corpus.py, fixtures/compat/golden-0.4.31.json.gz) passes the
// editor's own checks and projects to the tiles the add-on compiles from it.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { gunzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { projectLayout, validatePages } from "../src/model/pages";

const golden = JSON.parse(gunzipSync(readFileSync(resolve(process.cwd(), "../tests/fixtures/compat/golden-0.4.31.json.gz"))).toString("utf8"));
const saved = Object.entries(golden.cases as Record<string, any>).filter(([, record]) => !("refused" in record));

describe("pages saved by app 0.4.31", () => {
  it("are all in the corpus", () => { expect(saved.length).toBeGreaterThan(14000); });
  it("pass the editor's checks and project to the tiles the add-on compiled", () => {
    const broken: string[] = [];
    for (const [key, record] of saved) {
      const [columns, rows] = key.split(" ")[0].split("x").map(Number);
      const grid = { columns, rows };
      try {
        validatePages(record.document, grid);
        const projected = projectLayout(record.document, grid).tiles;
        const compiled = (record.compiled as any[]).filter((tile) => !("in" in tile));
        if (projected.length !== compiled.length || projected.some((tile, i) => tile.entity !== compiled[i].entity || (tile.options?.size ?? "single") !== (compiled[i].options?.size ?? "single")))
          broken.push(`${key}: projects to other tiles`);
      } catch (error: any) {
        broken.push(`${key}: ${error.message}`);
      }
    }
    expect(broken.slice(0, 10)).toEqual([]);
  });
});
