import { apiRequest } from "./client";
import type { ActivityAction, ActivityLog, Meta } from "./types";

export interface LogPage {
  items: ActivityLog[];
  meta: Meta;
}

export interface LogFilter {
  action?: ActivityAction;
  /** Local date `YYYY-MM-DD`, inclusive. */
  from?: string;
  to?: string;
}

/** The signed-in user's own activity, newest first. Carries no patient identity. */
export async function listLogs(
  page: number,
  size: number,
  filter: LogFilter = {},
  signal?: AbortSignal,
): Promise<LogPage> {
  const envelope = await apiRequest<ActivityLog[]>("/logs", {
    query: {
      page,
      size,
      action: filter.action,
      // Date inputs give whole days; widen them to the start and end of that day.
      date_from: filter.from ? new Date(`${filter.from}T00:00:00`).toISOString() : undefined,
      date_to: filter.to ? new Date(`${filter.to}T23:59:59.999`).toISOString() : undefined,
    },
    signal,
  });
  const items = envelope.data ?? [];
  return { items, meta: envelope.meta ?? { page, size, total: items.length } };
}
