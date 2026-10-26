import { describe, expect, it } from "vitest";

import { ApiError, friendlyMessage } from "./errors";

describe("friendlyMessage", () => {
  it.each([
    [0, "terhubung"],
    [401, "Sesi"],
    [404, "tidak ditemukan"],
    [413, "Ukuran file"],
    [415, "Jenis file"],
    [429, "Terlalu banyak"],
  ])("maps status %i to an Indonesian message", (status, fragment) => {
    expect(friendlyMessage(new ApiError(status, "x", "english"))).toContain(fragment);
  });

  it("hides server detail on 5xx", () => {
    const message = friendlyMessage(new ApiError(500, "boom", "stack trace here"));
    expect(message).not.toContain("stack trace");
  });

  it("falls back to the server message for other statuses", () => {
    expect(friendlyMessage(new ApiError(422, "validation_error", "Nama wajib diisi"))).toBe(
      "Nama wajib diisi",
    );
  });

  it("handles values that are not ApiError", () => {
    expect(friendlyMessage(new Error("x"))).toMatch(/tidak terduga/);
    expect(friendlyMessage("x")).toMatch(/tidak terduga/);
  });
});
