/**
 * QueryStateFallback — one place that maps a React Query state onto the
 * three user-visible states: loading, error, ready. Screens used to
 * hand-roll this inconsistently — some rendered a spinner and no error
 * branch, so a failed request just showed an empty screen. Half the
 * critical findings in the 2026-07-04 UX audit collapsed into that one
 * missing pattern.
 *
 * Usage:
 *
 *   const q = useQuery(...);
 *   return (
 *     <QueryStateFallback query={q} onRetry={q.refetch}>
 *       {(data) => <MyReport data={data} />}
 *     </QueryStateFallback>
 *   );
 *
 * The children function is only called with a defined, successful `data`.
 * Loading and error states get consistent copy + a retry button.
 */
import type { ReactNode } from "react";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useHaptic } from "@/hooks/useTelegram";

interface QueryLike<T> {
  data: T | undefined;
  isLoading?: boolean;
  isPending?: boolean;
  isError: boolean;
  error?: unknown;
}

interface Props<T> {
  query: QueryLike<T>;
  children: (data: T) => ReactNode;
  onRetry?: () => void;
  loadingMessage?: string;
  errorTitle?: string;
  errorHint?: string;
  /** Custom skeleton element to render instead of the default spinner. */
  skeleton?: ReactNode;
}

export function QueryStateFallback<T>({
  query,
  children,
  onRetry,
  loadingMessage = "Загружаем…",
  errorTitle = "Не удалось загрузить",
  errorHint = "Проверьте подключение и попробуйте ещё раз.",
  skeleton,
}: Props<T>) {
  const { impact } = useHaptic();
  const loading = query.isLoading ?? query.isPending ?? false;

  if (loading && !query.data) {
    return skeleton ? (
      <>{skeleton}</>
    ) : (
      <div className="query-fallback query-fallback--loading">
        <LoadingSpinner message={loadingMessage} />
      </div>
    );
  }

  if (query.isError && !query.data) {
    return (
      <div className="query-fallback query-fallback--error">
        <p className="query-fallback__title">{errorTitle}</p>
        <p className="query-fallback__hint">{errorHint}</p>
        {onRetry && (
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              impact("light");
              onRetry();
            }}
          >
            Повторить
          </button>
        )}
      </div>
    );
  }

  if (query.data === undefined) return null;
  return <>{children(query.data)}</>;
}
