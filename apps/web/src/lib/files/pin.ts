// Mirrors FileUploadRequest.normalize_pin in apps/api: 4–8 digits, stored as a
// string. The server is authoritative; this only prevents a doomed round trip.
export const PIN_MIN_LENGTH = 4;
export const PIN_MAX_LENGTH = 8;

const PIN_PATTERN = /^\d+$/;
const PIN_FORMAT_MESSAGE = "PIN harus terdiri dari 4 hingga 8 digit angka.";

/** Error for a PIN the user submitted, or null when it can be sent. */
export function validatePin(value: string): string | null {
  const pin = value.trim();
  if (!pin) return "PIN wajib diisi.";
  if (!PIN_PATTERN.test(pin) || pin.length < PIN_MIN_LENGTH || pin.length > PIN_MAX_LENGTH) {
    return PIN_FORMAT_MESSAGE;
  }
  return null;
}

/** Upload PINs are optional: an empty field means "no PIN". */
export function validateOptionalPin(value: string): string | null {
  return value.trim() ? validatePin(value) : null;
}

/** The PIN as the API expects it: trimmed, or undefined for "no PIN". */
export function pinForRequest(value: string): string | undefined {
  const pin = value.trim();
  return pin ? pin : undefined;
}
