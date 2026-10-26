import type { ActivityAction } from "@/lib/api/types";

export const ACTION_LABELS: Record<ActivityAction, string> = {
  login: "Masuk",
  logout: "Keluar",
  upload: "Unggah file",
  download: "Unduh file",
  view: "Lihat file",
  update: "Ubah data",
  delete: "Hapus",
  share_image: "Unduh untuk konsultasi",
};

export const ACTIONS = Object.keys(ACTION_LABELS) as ActivityAction[];
