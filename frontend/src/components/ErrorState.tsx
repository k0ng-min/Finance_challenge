import { Icon3D } from "./Icon3D";

interface ErrorStateProps {
  code?: "404" | "403" | "502" | "error";
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const ICON_BY_CODE: Record<string, string> = {
  "404": "zoom",
  "403": "lock",
  "502": "wifi",
  error: "bell",
};

export function ErrorState({ code = "error", title, message, actionLabel, onAction }: ErrorStateProps) {
  const icon = ICON_BY_CODE[code];
  return (
    <div className="empty-state">
      <Icon3D src={icon} size={76} />
      <strong style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", color: "var(--heading)" }}>{title}</strong>
      {message && <p className="muted">{message}</p>}
      {onAction && (
        <button type="button" className="btn-secondary" onClick={onAction}>
          {actionLabel ?? "다시 시도"}
        </button>
      )}
    </div>
  );
}
