import { apiFetch } from "./client";
import type { BenchmarkRequest, BenchmarkResult } from "./types";

export function runBenchmark(
  request: BenchmarkRequest,
  signal?: AbortSignal,
): Promise<BenchmarkResult> {
  return apiFetch<BenchmarkResult>("/benchmark/run", {
    method: "POST",
    body: request,
    signal,
  });
}
