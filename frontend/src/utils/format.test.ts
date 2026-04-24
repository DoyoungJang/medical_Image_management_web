import { describe, expect, it } from "vitest";

import { flattenMetadata, formatBytes } from "./format";

describe("format utilities", () => {
  it("formats bytes in a readable way", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
  });

  it("flattens nested metadata objects", () => {
    const rows = flattenMetadata({ root: { child: "value" } });
    expect(rows).toEqual([{ key: "root.child", value: "value" }]);
  });
});
