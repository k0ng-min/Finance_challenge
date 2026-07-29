import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Icon3D } from "./Icon3D";

interface StepFlowProps {
  icon: string;
  iconBg?: string;
  eyebrow: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
  stepIndex: number;
  stepCount: number;
  onBack?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  loading?: boolean;
}

export function StepFlow({
  icon, iconBg, eyebrow, title, subtitle, children,
  stepIndex, stepCount, onBack, onNext, nextLabel, nextDisabled, loading,
}: StepFlowProps) {
  return (
    <div className="step">
      <motion.div
        key={stepIndex}
        initial={{ x: 24 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}
      >
        <motion.div
          className="step__icon-wrap"
          initial={{ scale: 0.7 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 18 }}
        >
          <div className="step__icon-glow" />
          <Icon3D src={icon} size={148} bg={iconBg} rounded="38%" className="step__icon" />
        </motion.div>
        <span className="step__eyebrow">{eyebrow}</span>
        <h1 className="step__title">{title}</h1>
        {subtitle && <p className="step__subtitle">{subtitle}</p>}
        {children && <div className="step__content">{children}</div>}
      </motion.div>


      <div className="step__dots">
        {Array.from({ length: stepCount }).map((_, i) => (
          <motion.span
            key={i}
            className={`dot${i === stepIndex ? " dot--active" : ""}`}
            animate={{ width: i === stepIndex ? 22 : 8 }}
            transition={{ duration: 0.2 }}
          />
        ))}
      </div>

      <div className="step__actions">
        {onBack && (
          <motion.button whileTap={{ scale: 0.96 }} type="button" className="btn-secondary step__back" onClick={onBack}>
            이전
          </motion.button>
        )}
        {onNext && (
          <motion.button
            whileTap={{ scale: 0.98 }}
            type="button"
            className="btn-primary step__next"
            onClick={onNext}
            disabled={nextDisabled || loading}
          >
            {loading ? "처리 중..." : (nextLabel ?? "다음")}
          </motion.button>
        )}
      </div>
    </div>
  );
}
