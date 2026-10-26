import { describe, expect, it } from "vitest";

import { CIPHERS, getCipherInfo } from "./ciphers";

describe("getCipherInfo", () => {
  it("finds a cipher by form value and by stored algorithm", () => {
    expect(getCipherInfo("aes")).toBe(getCipherInfo("aes-gcm"));
    expect(getCipherInfo("des").label).toBe("DES-CBC");
    expect(getCipherInfo("rc4").algorithm).toBe("rc4");
  });

  it("throws for an unknown cipher", () => {
    // @ts-expect-error deliberately outside the type
    expect(() => getCipherInfo("blowfish")).toThrow(/Unknown cipher/);
  });

  it("recommends only AES-GCM", () => {
    expect(CIPHERS.filter((c) => c.recommended).map((c) => c.choice)).toEqual(["aes"]);
  });
});
