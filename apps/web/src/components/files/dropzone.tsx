"use client";

import { useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface DropzoneProps {
  onFile: (file: File) => void;
  accept?: string;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
}

/** Drag-and-drop target backed by a real file input, so keyboard users can pick too. */
export function Dropzone({ onFile, accept, disabled, invalid, describedBy }: DropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) onFile(file);
    if (inputRef.current) inputRef.current.value = ""; // allow re-picking the same file
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        "focus-within:border-ring focus-within:ring-ring/50 flex min-h-28 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-4 text-center text-sm transition-colors focus-within:ring-3",
        dragging && "border-primary bg-muted",
        invalid && "border-destructive",
        disabled && "opacity-50",
      )}
    >
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        disabled={disabled}
        aria-invalid={invalid ? true : undefined}
        aria-describedby={describedBy}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <label htmlFor={inputId} className={cn("cursor-pointer", disabled && "cursor-not-allowed")}>
        Tarik file ke sini, atau{" "}
        <span className="font-medium underline underline-offset-4">pilih file</span>
      </label>
      <p className="text-muted-foreground text-xs">Maksimal 100 MB</p>
    </div>
  );
}
