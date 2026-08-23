import { useRef, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FrameScrollbar } from "./FrameScrollbar";

export function Modal({
  open,
  onClose,
  title,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** 기본 폭(360px)보다 넓혀야 할 때(예: 표 비교) 쓴다 — modal-card에 그대로 이어붙인다. */
  className?: string;
}) {
  // 팝업 안에서도 메인 화면과 같은 막대를 쓴다 — OS 기본 막대는 가장자리에
  // 바짝 붙어 둔근 모서리와 겹치고, 같은 앱 안에서 한쪽만 다른 프로그램처럼 보인다.
  const bodyRef = useRef<HTMLDivElement>(null);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className={`modal-card${className ? ` ${className}` : ""}`}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-card__head">
              <strong>{title}</strong>
              <button type="button" className="modal-card__close" onClick={onClose}>
                ✕
              </button>
            </div>
            <div className="modal-card__body" ref={bodyRef}>{children}</div>
            <FrameScrollbar targetRef={bodyRef} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
