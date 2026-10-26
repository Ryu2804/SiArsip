import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/errors";

import {
  MAX_FILE_BYTES,
  describeUploadError,
  formatBytes,
  getCategory,
  validateFile,
} from "./rules";

const fileOfSize = (size: number) => ({ size }) as File;

describe("formatBytes", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
  ])("formats %i", (bytes, expected) => {
    expect(formatBytes(bytes)).toBe(expected);
  });

  it("scales through KB and MB", () => {
    expect(formatBytes(1024)).toMatch(/^1 KB$/);
    expect(formatBytes(5 * 1024 * 1024)).toMatch(/^5 MB$/);
    expect(formatBytes(MAX_FILE_BYTES)).toMatch(/^100 MB$/);
  });
});

describe("validateFile", () => {
  it("rejects an empty file", () => {
    expect(validateFile(fileOfSize(0))).toMatch(/kosong/);
  });

  it("rejects a file over the limit", () => {
    expect(validateFile(fileOfSize(MAX_FILE_BYTES + 1))).toMatch(/melebihi batas/);
  });

  it("accepts a file exactly at the limit", () => {
    expect(validateFile(fileOfSize(MAX_FILE_BYTES))).toBeNull();
  });
});

describe("describeUploadError", () => {
  it("explains 413 with the limit", () => {
    const text = describeUploadError(new ApiError(413, "file_too_large", "x"), "video");
    expect(text).toContain("100 MB");
  });

  it("lists the allowed types on 415, by readable name", () => {
    const error = new ApiError(415, "unsupported", "x", {
      allowed: ["image/jpeg", "image/png"],
    });
    const text = describeUploadError(error, "clinical_image");
    expect(text).toContain(getCategory("clinical_image").label);
    expect(text).toContain("JPG, PNG");
  });

  it("still explains 415 when the server lists no allowed types", () => {
    const text = describeUploadError(new ApiError(415, "unsupported", "x"), "video");
    expect(text).toContain("tidak sesuai");
    expect(text).not.toContain("diizinkan:");
  });

  it("falls back to the generic message for other errors", () => {
    expect(describeUploadError(new ApiError(0, "network_error", "x"), "video")).toMatch(
      /terhubung/,
    );
  });
});
