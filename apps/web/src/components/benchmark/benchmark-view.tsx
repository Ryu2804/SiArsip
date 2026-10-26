"use client";

import { useState } from "react";

import { BenchmarkChart } from "@/components/benchmark/benchmark-chart";
import { CipherBadge } from "@/components/cipher-badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { friendlyMessage } from "@/lib/api/errors";
import {
  DEFAULT_ITERATIONS,
  DEFAULT_SIZE,
  ITERATION_OPTIONS,
  SIZE_OPTIONS,
} from "@/lib/benchmark/options";
import { useRunBenchmark } from "@/lib/benchmark/queries";
import { formatBytes } from "@/lib/files/rules";

const decimal = (value: number, digits = 2) =>
  value.toLocaleString("id-ID", { maximumFractionDigits: digits });

export function BenchmarkView() {
  const [size, setSize] = useState(DEFAULT_SIZE);
  const [iterations, setIterations] = useState(DEFAULT_ITERATIONS);
  const run = useRunBenchmark();
  const data = run.data;

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Benchmark cipher</h1>
        <p className="text-muted-foreground text-sm">
          Membandingkan AES-GCM, DES-CBC, dan RC4 dengan jalur enkripsi yang sama seperti
          unggahan file. Data uji dibuat di server dan tidak disimpan.
        </p>
      </div>

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          run.mutate({ size_bytes: size, iterations });
        }}
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="bench-ukuran">Ukuran data</Label>
          <Select
            items={SIZE_OPTIONS}
            value={size}
            disabled={run.isPending}
            onValueChange={(value) => value && setSize(value)}
          >
            <SelectTrigger id="bench-ukuran" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SIZE_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="bench-putaran">Jumlah putaran</Label>
          <Select
            items={ITERATION_OPTIONS}
            value={iterations}
            disabled={run.isPending}
            onValueChange={(value) => value && setIterations(value)}
          >
            <SelectTrigger id="bench-putaran" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ITERATION_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button type="submit" disabled={run.isPending}>
          {run.isPending ? "Menjalankan…" : data ? "Jalankan ulang" : "Jalankan benchmark"}
        </Button>
      </form>

      {run.isPending && (
        <p role="status" className="text-muted-foreground text-sm">
          Benchmark berjalan di server. Ukuran dan putaran yang besar bisa memakan waktu
          beberapa detik.
        </p>
      )}

      {run.error && (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border p-4">
          <p className="text-destructive text-sm">{friendlyMessage(run.error)}</p>
          <Button variant="outline" onClick={() => run.mutate({ size_bytes: size, iterations })}>
            Coba lagi
          </Button>
        </div>
      )}

      {!data && !run.isPending && !run.error && (
        <p className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
          Belum ada hasil. Pilih ukuran data dan jumlah putaran, lalu jalankan benchmark.
        </p>
      )}

      {data && (
        <>
          <p className="text-muted-foreground text-sm" aria-live="polite">
            Hasil untuk data {formatBytes(data.size_bytes)}, rata-rata dari {data.iterations}{" "}
            putaran.
          </p>

          <div className="grid gap-4 lg:grid-cols-2">
            <BenchmarkChart
              title="Waktu per operasi"
              unit="ms, lebih kecil lebih cepat"
              results={data.results}
              encrypt={(r) => r.encrypt_ms}
              decrypt={(r) => r.decrypt_ms}
            />
            <BenchmarkChart
              title="Kecepatan"
              unit="MB/s, lebih besar lebih cepat"
              results={data.results}
              encrypt={(r) => r.encrypt_mb_s}
              decrypt={(r) => r.decrypt_mb_s}
            />
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cipher</TableHead>
                  <TableHead className="text-right">Enkripsi (ms)</TableHead>
                  <TableHead className="text-right">Dekripsi (ms)</TableHead>
                  <TableHead className="text-right">Enkripsi (MB/s)</TableHead>
                  <TableHead className="text-right">Dekripsi (MB/s)</TableHead>
                  <TableHead className="text-right">Tambahan ukuran</TableHead>
                  <TableHead>Hasil dekripsi</TableHead>
                  <TableHead>Perubahan data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.results.map((r) => (
                  <TableRow key={r.algorithm}>
                    <TableCell>
                      <CipherBadge algorithm={r.algorithm} showAdvice />
                    </TableCell>
                    <TableCell className="text-right">{decimal(r.encrypt_ms)}</TableCell>
                    <TableCell className="text-right">{decimal(r.decrypt_ms)}</TableCell>
                    <TableCell className="text-right">{decimal(r.encrypt_mb_s)}</TableCell>
                    <TableCell className="text-right">{decimal(r.decrypt_mb_s)}</TableCell>
                    <TableCell className="text-right">
                      {formatBytes(r.overhead_bytes)} ({decimal(r.overhead_percent)}%)
                    </TableCell>
                    <TableCell>{r.verified ? "Sama dengan aslinya" : "Tidak sama"}</TableCell>
                    <TableCell>
                      {r.tamper_detected ? "Terdeteksi" : "Tidak terdeteksi"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </section>
  );
}
