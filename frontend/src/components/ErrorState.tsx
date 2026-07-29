import { Icon3D } from "./Icon3D";

interface ErrorStateProps {
  code?: "404" | "403" | "502" | "error";
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const ICON_BY_CODE: Record<string, { icon: string; bg: string }> = {
  "404": { icon: "zoom", bg: "var(--yellow-soft)" },
  "403": { icon: "lock", bg: "var(--orange-soft)" },
  "502": { icon: "wifi", bg: "var(--mint-soft)" },
  error: { icon: "bell", bg: "var(--orange-soft)" },
};

export function ErrorState({ code = "error", title, message, actionLabel, onAction }: ErrorStateProps) {
  const meta = ICON_BY_CODE[code];
  return (
    <div className="empty-state">
      <Icon3D src={meta.icon} size={76} bg={meta.bg} rounded="34%" />
      <strong style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", color: "#5a4632" }}>{title}</strong>
      {message && <p className="muted">{message}</p>}
      {onAction && (
        <button type="button" className="btn-secondary" onClick={onAction}>
          {actionLabel ?? "다시 시도"}
        </button>
      )}
    </div>
  );
}
