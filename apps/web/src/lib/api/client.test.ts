import { describe, expect, it } from "vitest";

import { buildUrl, parseApiError } from "./client";

describe("parseApiError", () => {
  it("reads the error envelope", () => {
    const body = JSON.stringify({
      success: false,
      error: { code: "reveal_failed", message: "nope", details: { reason: "no_data" } },
    });
    const error = parseApiError(422, "Unprocessable", body);
    expect(error.status).toBe(422);
    expect(error.code).toBe("reveal_failed");
    expect(error.message).toBe("nope");
    expect(error.details).toEqual({ reason: "no_data" });
  });

  it("copes with a non-JSON body", () => {
    const error = parseApiError(502, "Bad Gateway", "<html>proxy</html>");
    expect(error.status).toBe(502);
    expect(error.code).toBe("http_error");
    expect(error.message).toBe("Bad Gateway");
  });

  it("copes with an empty body and no status text", () => {
    expect(parseApiError(500, "", "").message).toBe("HTTP 500");
  });

  it("copes with JSON that is not an error envelope", () => {
    expect(parseApiError(400, "Bad Request", "{}").code).toBe("http_error");
  });
});

describe("buildUrl", () => {
  it("joins the path and keeps real values in the query", () => {
    const url = new URL(buildUrl("/patients", { page: 2, size: 20, flag: false }));
    expect(url.pathname).toBe("/patients");
    expect(url.searchParams.get("page")).toBe("2");
    expect(url.searchParams.get("flag")).toBe("false");
  });

  it("skips null and undefined query values", () => {
    const url = new URL(buildUrl("files", { category: undefined, q: null }));
    expect(url.pathname).toBe("/files");
    expect(url.search).toBe("");
  });
});
