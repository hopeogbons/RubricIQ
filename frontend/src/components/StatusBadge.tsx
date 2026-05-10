import { cn } from "@/lib/utils";
import type { SubmissionStatus } from "@/lib/submissions";

const STATUS_CLASSES: Record<SubmissionStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  processing: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  complete: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  failed: "bg-destructive/15 text-destructive",
};

export function StatusBadge({ status }: { status: SubmissionStatus }): JSX.Element {
  return (
    <span
      data-testid={`status-badge-${status}`}
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize",
        STATUS_CLASSES[status],
      )}
    >
      {status}
    </span>
  );
}
