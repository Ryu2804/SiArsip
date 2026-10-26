"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listLogs, type LogFilter } from "@/lib/api/logs";

export const logKeys = {
  all: ["logs"] as const,
  list: (page: number, size: number, filter: LogFilter) =>
    [...logKeys.all, page, size, filter] as const,
};

export function useLogs(page: number, size: number, filter: LogFilter) {
  return useQuery({
    queryKey: logKeys.list(page, size, filter),
    queryFn: ({ signal }) => listLogs(page, size, filter, signal),
    placeholderData: keepPreviousData,
  });
}
