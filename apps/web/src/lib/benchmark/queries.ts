"use client";

import { useMutation } from "@tanstack/react-query";

import { runBenchmark } from "@/lib/api/benchmark";
import type { BenchmarkRequest } from "@/lib/api/types";

export function useRunBenchmark() {
  return useMutation({
    mutationFn: (request: BenchmarkRequest) => runBenchmark(request),
  });
}
