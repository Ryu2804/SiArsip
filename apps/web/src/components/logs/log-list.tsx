"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import type { ActivityAction } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { ACTIONS, ACTION_LABELS } from "@/lib/logs/actions";
import { useLogs } from "@/lib/logs/queries";

const PAGE_SIZE = 20;
const ALL = "all";

const actionItems = [
  { value: ALL, label: "Semua aktivitas" },
  ...ACTIONS.map((a) => ({ value: a, label: ACTION_LABELS[a] })),
];

export function LogList() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<ActivityAction | typeof ALL>(ALL);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const rangeInvalid = Boolean(from && to && from > to);

  const { data, error, isPending, isFetching, refetch } = useLogs(page, PAGE_SIZE, {
    action: action === ALL ? undefined : action,
    from: rangeInvalid ? undefined : from || undefined,
    to: rangeInvalid ? undefined : to || undefined,
  });

  const total = data?.meta.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = action !== ALL || Boolean(from) || Boolean(to);

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Log aktivitas</h1>
        <p className="text-muted-foreground text-sm">
          Riwayat aktivitas akun Anda. Identitas pasien tidak dicatat di sini.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="log-aksi">Aktivitas</Label>
          <Select
            items={actionItems}
            value={action}
            onValueChange={(value) => {
              setAction((value as ActivityAction | typeof ALL | null) ?? ALL);
              setPage(1);
            }}
          >
            <SelectTrigger id="log-aksi" className="w-52">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {actionItems.map((a) => (
                <SelectItem key={a.value} value={a.value}>
                  {a.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="log-dari">Dari tanggal</Label>
          <Input
            id="log-dari"
            type="date"
            value={from}
            aria-invalid={rangeInvalid ? true : undefined}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="log-sampai">Sampai tanggal</Label>
          <Input
            id="log-sampai"
            type="date"
            value={to}
            aria-invalid={rangeInvalid ? true : undefined}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(1);
            }}
          />
        </div>
        {filtered && (
          <Button
            variant="ghost"
            onClick={() => {
              setAction(ALL);
              setFrom("");
              setTo("");
              setPage(1);
            }}
          >
            Reset filter
          </Button>
        )}
      </div>
      {rangeInvalid && (
        <p role="alert" className="text-destructive text-sm">
          Tanggal awal tidak boleh setelah tanggal akhir.
        </p>
      )}

      {isPending ? (
        <p role="status" className="text-muted-foreground text-sm">
          Memuat log…
        </p>
      ) : error ? (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border p-4">
          <p className="text-destructive text-sm">{friendlyMessage(error)}</p>
          <Button variant="outline" onClick={() => refetch()}>
            Coba lagi
          </Button>
        </div>
      ) : total === 0 ? (
        <p className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
          {filtered ? "Tidak ada aktivitas yang cocok dengan filter." : "Belum ada aktivitas."}
        </p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Waktu</TableHead>
                  <TableHead>Aktivitas</TableHead>
                  <TableHead>ID file</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{formatDateTime(log.created_at)}</TableCell>
                    <TableCell>{ACTION_LABELS[log.action] ?? log.action}</TableCell>
                    <TableCell className="font-mono text-xs" title={log.file_id ?? undefined}>
                      {log.file_id ? `${log.file_id.slice(0, 8)}…` : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-muted-foreground" aria-live="polite">
              Halaman {page} dari {totalPages} · {total} aktivitas
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={page <= 1 || isFetching}
                onClick={() => setPage((p) => p - 1)}
              >
                Sebelumnya
              </Button>
              <Button
                variant="outline"
                disabled={page >= totalPages || isFetching}
                onClick={() => setPage((p) => p + 1)}
              >
                Berikutnya
              </Button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
