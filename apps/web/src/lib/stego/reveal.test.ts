import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { MAX_FILE_BYTES } from "@/lib/files/rules";

import { NO_IDENTITY_MESSAGE, describeRevealError, validateRevealFile } from "./reveal";

const file = (name: string, size = 10) => ({ name, size }) as File;

describe("validateRevealFile", () => {
  it.each(["a.png", "b.JPG", "c.jpeg"])("accepts %s", (name) => {
    expect(validateRevealFile(file(name))).toBeNull();
  });

  it.each(["a.pdf", "b.gif", "png"])("rejects %s", (name) => {
    expect(validateRevealFile(file(name))).toMatch(/PNG atau JPEG/);
  });

  it("rejects empty and oversized files", () => {
    expect(validateRevealFile(file("a.png", 0))).toMatch(/kosong/);
    expect(validateRevealFile(file("a.png", MAX_FILE_BYTES + 1))).toMatch(/maksimal/);
  });
});

describe("describeRevealError", () => {
  it("shows one message for every reveal_failed reason", () => {
    for (const reason of ["no_data", "decryption", "malformed"]) {
      const error = new ApiError(422, "reveal_failed", "server detail", { reason });
      expect(describeRevealError(error)).toBe(NO_IDENTITY_MESSAGE);
    }
  });

  it("explains an unsupported image type", () => {
    expect(describeRevealError(new ApiError(415, "unsupported_image_type", "x"))).toMatch(
      /PNG atau JPEG/,
    );
  });

  it("uses the generic message for anything else", () => {
    expect(describeRevealError(new ApiError(0, "network_error", "x"))).toMatch(/terhubung/);
  });
});
