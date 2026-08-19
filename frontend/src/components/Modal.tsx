import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";

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
            <div className="modal-card__body">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
