import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon3D } from "./Icon3D";

interface NextStepCardProps {
  to: string;
  icon: string;
  label: string;
  title: string;
  /** 다음 단계가 다른 화면이 아니라 같은 화면의 다른 탭일 때 쓴다(청구 전 점검처럼 두
   *  화면을 탭으로 합쳐 둔 곳). 주면 `to`로 이동하는 대신 이걸 부른다 — 합쳐진 화면에서
   *  옛 경로로 navigate하면 같은 화면이 다시 마운트되며 탭이 첫 번째로 되돌아간다. */
  onNavigate?: () => void;
}

export function NextStepCard({ to, icon, label, title, onNavigate }: NextStepCardProps) {
  const navigate = useNavigate();
  return (
    <motion.button
      type="button"
      className="next-step-card"
      onClick={() => (onNavigate ? onNavigate() : navigate(to))}
      whileTap={{ scale: 0.98 }}
      whileHover={{ y: -2 }}
    >
      <Icon3D src={icon} size={52} />
      <div className="next-step-card__text">
        <div className="next-step-card__label">{label}</div>
        <div className="next-step-card__title">{title}</div>
      </div>
      <span className="next-step-card__arrow">›</span>
    </motion.button>
  );
}
