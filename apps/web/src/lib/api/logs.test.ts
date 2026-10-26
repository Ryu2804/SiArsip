import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./client", () => ({
  apiRequest: vi.fn(),
}));

import { apiRequest } from "./client";
import { listLogs } from "./logs";

const mockRequest = vi.mocked(apiRequest);

beforeEach(() => {
  mockRequest.mockReset();
  mockRequest.mockResolvedValue({ success: true, message: "OK", data: [], meta: null });
});

function lastQuery() {
  return mockRequest.mock.calls.at(-1)?.[1]?.query ?? {};
}

describe("listLogs", () => {
  it("sends no filters when none are set", async () => {
    await listLogs(1, 20);
    expect(lastQuery()).toEqual({
      page: 1,
      size: 20,
      action: undefined,
      date_from: undefined,
      date_to: undefined,
    });
  });

  it("widens whole days to the start and end of the day", async () => {
    await listLogs(1, 20, { from: "2026-03-05", to: "2026-03-05" });
    const { date_from, date_to } = lastQuery() as { date_from: string; date_to: string };
    expect(date_from).toBe(new Date("2026-03-05T00:00:00").toISOString());
    expect(date_to).toBe(new Date("2026-03-05T23:59:59.999").toISOString());
    expect(new Date(date_to).getTime()).toBeGreaterThan(new Date(date_from).getTime());
  });

  it("passes the action filter through", async () => {
    await listLogs(2, 10, { action: "share_image" });
    expect(lastQuery()).toMatchObject({ page: 2, size: 10, action: "share_image" });
  });

  it("falls back to a meta built from the items when the server sends none", async () => {
    const page = await listLogs(1, 20);
    expect(page).toEqual({ items: [], meta: { page: 1, size: 20, total: 0 } });
  });
});
