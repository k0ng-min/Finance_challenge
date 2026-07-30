import { Modal } from "./Modal";

/** 삭제처럼 되돌릴 수 없는 동작을 브라우저 기본 alert(window.confirm) 대신 앱 톤에 맞는
 * 모달로 확인받는다. */
export function ConfirmDialog({
  open, title, message, confirmLabel = "삭제", onConfirm, onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal open={open} onClose={onCancel} title={title}>
      <p style={{ marginTop: 0, color: "var(--text)" }}>{message}</p>
      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button type="button" className="btn-secondary" style={{ flex: 1 }} onClick={onCancel}>
          취소
        </button>
        <button
          type="button"
          className="btn-primary"
          style={{ flex: 1, background: "#e5484d", boxShadow: "none" }}
          onClick={onConfirm}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
