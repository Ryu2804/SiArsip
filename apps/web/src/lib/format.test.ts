import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, maskNik } from "./format";

describe("formatDate", () => {
  it("shows a date-only string without shifting the day", () => {
    const text = formatDate("1980-05-12");
    expect(text).toContain("12");
    expect(text).toContain("1980");
  });

  it.each([null, undefined, "", "not-a-date"])("returns a dash for %j", (value) => {
    expect(formatDate(value)).toBe("-");
  });
});

describe("formatDateTime", () => {
  it("formats an ISO timestamp", () => {
    expect(formatDateTime("2026-05-12T14:05:00Z")).toContain("2026");
  });

  it.each([null, undefined, "", "garbage"])("returns a dash for %j", (value) => {
    expect(formatDateTime(value)).toBe("-");
  });
});

describe("maskNik", () => {
  it("keeps the first and last four digits", () => {
    expect(maskNik("3201234567890001")).toBe("3201********0001");
  });

  it("masks short values completely", () => {
    expect(maskNik("12345678")).toBe("********");
  });

  it("returns a dash when there is no NIK", () => {
    expect(maskNik(null)).toBe("-");
    expect(maskNik("")).toBe("-");
  });
});
