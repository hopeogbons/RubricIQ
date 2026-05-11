import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "destructive";

export interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  pushToast: (message: string, variant?: ToastVariant) => void;
  dismiss: (id: number) => void;
  toasts: Toast[];
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION_MS = 3000;

export function ToastProvider({
  children,
  durationMs = DEFAULT_DURATION_MS,
}: {
  children: ReactNode;
  durationMs?: number;
}): JSX.Element {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idCounter = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback(
    (message: string, variant: ToastVariant = "default") => {
      idCounter.current += 1;
      const id = idCounter.current;
      setToasts((prev) => [...prev, { id, message, variant }]);
      window.setTimeout(() => dismiss(id), durationMs);
    },
    [dismiss, durationMs],
  );

  const value = useMemo<ToastContextValue>(
    () => ({ pushToast, dismiss, toasts }),
    [pushToast, dismiss, toasts],
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}

const VARIANT_CLASSES: Record<ToastVariant, string> = {
  default: "bg-foreground text-background",
  success: "bg-green-600 text-white",
  destructive: "bg-destructive text-destructive-foreground",
};

export function Toaster(): JSX.Element {
  const { toasts, dismiss } = useToast();
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 flex-col gap-2"
      data-testid="toaster"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}): JSX.Element {
  // Re-run on every mount; no cleanup needed since dismiss removes from the list.
  useEffect(() => {
    // No-op; the provider schedules dismissal. This effect is here so the item
    // has a stable identity hook should we add per-item timers later.
  }, []);
  return (
    <div
      role="status"
      data-testid={`toast-${toast.variant}`}
      className={cn(
        "pointer-events-auto cursor-pointer rounded-md px-4 py-3 text-sm shadow-lg",
        VARIANT_CLASSES[toast.variant],
      )}
      onClick={onDismiss}
    >
      {toast.message}
    </div>
  );
}
