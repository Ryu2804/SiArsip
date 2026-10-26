const LOCALE = "id-ID";

/** A date-only string ("1980-05-12") shown as "12 Mei 1980", with no timezone shift. */
export function formatDate(dateOnly: string | null | undefined): string {
  if (!dateOnly) return "-";
  const [year, month, day] = dateOnly.split("-").map(Number);
  if (!year || !month || !day) return "-";
  return new Date(year, month - 1, day).toLocaleDateString(LOCALE, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Same masking the API uses for list rows: first 4 and last 4 digits. */
export function maskNik(nik: string | null | undefined): string {
  if (!nik) return "-";
  if (nik.length <= 8) return "*".repeat(nik.length);
  return `${nik.slice(0, 4)}${"*".repeat(nik.length - 8)}${nik.slice(-4)}`;
}

/** An ISO timestamp shown in the viewer's timezone, e.g. "12 Mei 2026 14.05". */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(LOCALE, {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
