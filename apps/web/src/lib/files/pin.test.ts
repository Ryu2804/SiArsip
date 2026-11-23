import { describe, expect, it } from "vitest";

import { pinForRequest, validateOptionalPin, validatePin } from "./pin";

describe("validatePin", () => {
  it.each(["1234", "123456", "12345678", " 1234 "])("accepts %j", (pin) => {
    expect(validatePin(pin)).toBeNull();
  });

  it.each(["", "   ", "123", "123456789", "abcd", "12a4", "12 34"])(
    "rejects %j",
    (pin) => {
      expect(validatePin(pin)).not.toBeNull();
    },
  );
});

describe("validateOptionalPin", () => {
  it("accepts an empty value as no PIN", () => {
    expect(validateOptionalPin("")).toBeNull();
    expect(validateOptionalPin("  ")).toBeNull();
  });

  it("still checks a non-empty PIN", () => {
    expect(validateOptionalPin("1234")).toBeNull();
    expect(validateOptionalPin("12")).toContain("4 hingga 8");
  });
});

describe("pinForRequest", () => {
  it("trims a PIN and maps empty to undefined", () => {
    expect(pinForRequest(" 123456 ")).toBe("123456");
    expect(pinForRequest("   ")).toBeUndefined();
  });
});
