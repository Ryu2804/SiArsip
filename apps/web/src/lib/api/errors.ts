export class ApiError extends Error {
  /** HTTP status, or 0 when the request never reached the server. */
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  0: "Tidak dapat terhubung ke server. Periksa koneksi Anda lalu coba lagi.",
  401: "Sesi Anda berakhir. Silakan masuk kembali.",
  403: "Anda tidak memiliki akses ke data ini.",
  404: "Data yang diminta tidak ditemukan.",
  409: "Integritas file gagal diverifikasi. File mungkin telah diubah.",
  413: "Ukuran file melebihi batas yang diizinkan.",
  415: "Jenis file tidak didukung.",
  429: "Terlalu banyak permintaan. Coba lagi sebentar lagi.",
  503: "Layanan penyimpanan sedang tidak tersedia. Coba lagi nanti.",
};

/** Indonesian, user-facing text for any thrown value. */
export function friendlyMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const mapped = STATUS_MESSAGES[error.status];
    if (mapped) return mapped;
    if (error.status >= 500) {
      return "Terjadi kesalahan di server. Coba lagi nanti.";
    }
    return error.message;
  }
  return "Terjadi kesalahan yang tidak terduga.";
}
