"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CipherBenchmark } from "@/lib/api/types";
import { getCipherInfo } from "@/lib/ciphers";

interface BenchmarkChartProps {
  title: string;
  unit: string;
  results: CipherBenchmark[];
  encrypt: (r: CipherBenchmark) => number;
  decrypt: (r: CipherBenchmark) => number;
}

const TICK = { fill: "var(--muted-foreground)", fontSize: 12 };

const number = (value: number) =>
  value.toLocaleString("id-ID", { maximumFractionDigits: 2 });

/**
 * Grouped bars: one group per cipher, encrypt vs decrypt side by side. Two series
 * on one axis in one unit; the table below the charts carries every exact value.
 */
export function BenchmarkChart({ title, unit, results, encrypt, decrypt }: BenchmarkChartProps) {
  const data = results.map((r) => ({
    cipher: getCipherInfo(r.algorithm).label,
    Enkripsi: encrypt(r),
    Dekripsi: decrypt(r),
  }));

  return (
    <figure className="flex flex-col gap-2 rounded-xl border p-4">
      <figcaption className="text-sm font-medium">
        {title} <span className="text-muted-foreground font-normal">({unit})</span>
      </figcaption>
      <div className="h-64 w-full" role="img" aria-label={`Grafik batang: ${title}. Nilai lengkap ada di tabel.`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="cipher" tick={TICK} axisLine={false} tickLine={false} />
            <YAxis tick={TICK} axisLine={false} tickLine={false} width={48} tickFormatter={number} />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.5 }}
              formatter={(value) => `${number(Number(value))} ${unit}`}
              contentStyle={{
                background: "var(--popover)",
                color: "var(--popover-foreground)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="Enkripsi" fill="var(--chart-1)" maxBarSize={24} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Dekripsi" fill="var(--chart-2)" maxBarSize={24} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
