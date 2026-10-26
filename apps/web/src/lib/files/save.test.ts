import { describe, expect, it } from "vitest";

import { previewKind } from "./save";

describe("previewKind", () => {
  it.each([
    ["image/jpeg", "image"],
    ["image/png", "image"],
    ["application/pdf", "pdf"],
    ["video/mp4", "video"],
  ])("previews %s as %s", (mime, kind) => {
    expect(previewKind(mime)).toBe(kind);
  });

  it("has no preview for Office documents", () => {
    expect(
      previewKind("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ).toBeNull();
    expect(previewKind("application/zip")).toBeNull();
  });
});
