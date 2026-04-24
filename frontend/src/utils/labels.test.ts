import { describe, expect, it } from "vitest";

import { statusLabel, translateServerMessage } from "./labels";

describe("label utilities", () => {
  it("translates known image statuses to Korean labels", () => {
    expect(statusLabel("ok")).toBe("정상");
    expect(statusLabel("corrupted")).toBe("손상됨");
    expect(statusLabel("unreadable")).toBe("읽기 불가");
  });

  it("keeps unknown status values visible", () => {
    expect(statusLabel("custom")).toBe("custom");
  });

  it("translates common server errors", () => {
    expect(translateServerMessage("Invalid credentials.")).toBe("사용자명 또는 비밀번호가 올바르지 않습니다.");
  });
});
