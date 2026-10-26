import { Badge } from "@/components/ui/badge";
import type { CipherAlgorithm, CipherChoice } from "@/lib/api/types";
import { getCipherInfo } from "@/lib/ciphers";

interface CipherBadgeProps {
  algorithm: CipherAlgorithm | CipherChoice;
  /** Also show the "Direkomendasikan" / "Tidak disarankan" advice as text. */
  showAdvice?: boolean;
}

export function CipherBadge({ algorithm, showAdvice = false }: CipherBadgeProps) {
  const { label, recommended } = getCipherInfo(algorithm);

  return (
    <span className="inline-flex items-center gap-1.5">
      <Badge variant={recommended ? "secondary" : "destructive"}>{label}</Badge>
      {showAdvice && (
        <Badge variant="outline">
          {recommended ? "Direkomendasikan" : "Tidak disarankan"}
        </Badge>
      )}
    </span>
  );
}
