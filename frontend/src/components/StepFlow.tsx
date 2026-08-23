import { useEffect, type ReactNode } from "react";
import { motion } from "framer-motion";
import { Icon3D } from "./Icon3D";
import { FloatingIcon } from "./FloatingIcon";

interface StepFlowProps {
  icon: string;
  eyebrow: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
  stepIndex: number;
  onBack?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  loading?: boolean;
}

export function StepFlow({
  icon, eyebrow, title, subtitle, children,
  stepIndex, onBack, onNext, nextLabel, nextDisabled, loading,
}: StepFlowProps) {
  // 다음 단계로 넘어가면 늘 화면 맨 위부터 보여준다. 예전에는 앞 단계에서 내려둔
  // 스크롤 위치가 그대로 남아, 새 단계가 열리자마자 맨 아래(버튼 근처)가 보였다.
  useEffect(() => {
    const main = document.querySelector(".app-main");
    if (main) main.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }, [stepIndex]);

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
          <FloatingIcon>
            <Icon3D src={icon} size={84} className="step__icon" />
          </FloatingIcon>
        </motion.div>
        <span className="step__eyebrow">{eyebrow}</span>
        <h1 className="step__title">{title}</h1>
        {subtitle && <p className="step__subtitle">{subtitle}</p>}
        {children && <div className="step__content">{children}</div>}
      </motion.div>

      <div className="step__actions">
        {onBack && (
          <motion.button
            whileTap={{ scale: 0.9 }}
            whileHover={{ y: -2 }}
            type="button"
            className="step__back"
            onClick={onBack}
            aria-label="이전"
            title="이전"
          >
            <span aria-hidden>←</span>
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
