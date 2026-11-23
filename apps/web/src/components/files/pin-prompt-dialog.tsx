"use client";

import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, friendlyMessage } from "@/lib/api/errors";
import { PIN_MAX_LENGTH, validatePin } from "@/lib/files/pin";

interface PinPromptDialogProps {
  open: boolean;
  title: string;
  description: string;
  submitLabel?: string;
  onOpenChange: (open: boolean) => void;
  /** Runs the protected action. A rejection is shown inline instead of closing. */
  onSubmit: (pin: string) => Promise<void>;
}

export function PinPromptDialog({
  open,
  title,
  description,
  submitLabel = "Lanjutkan",
  onOpenChange,
  onSubmit,
}: PinPromptDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so a cancelled attempt never keeps the PIN. */}
        {open && (
          <PinPromptForm
            submitLabel={submitLabel}
            onSubmit={onSubmit}
            onCancel={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function PinPromptForm({
  submitLabel,
  onSubmit,
  onCancel,
}: {
  submitLabel: string;
  onSubmit: (pin: string) => Promise<void>;
  onCancel: () => void;
}) {
  const id = useId();
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const problem = validatePin(pin);
    if (problem) {
      setError(problem);
      return;
    }

    setError(null);
    setPending(true);
    try {
      await onSubmit(pin.trim());
    } catch (err) {
      if (
        err instanceof ApiError &&
        (err.code === "invalid_pin" || err.code === "pin_required")
      ) {
        setError("PIN salah. Periksa kembali lalu coba lagi.");
        setPin("");
        setPending(false);
        return;
      }
      setError(friendlyMessage(err));
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${id}-pin`}>PIN</Label>
        <Input
          id={`${id}-pin`}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          maxLength={PIN_MAX_LENGTH}
          autoFocus
          value={pin}
          disabled={pending}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => {
            setPin(event.target.value);
            setError(null);
          }}
        />
        {error && (
          <p id={`${id}-error`} role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel} disabled={pending}>
          Batal
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "Memproses…" : submitLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}
