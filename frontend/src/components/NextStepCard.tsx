import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon3D } from "./Icon3D";

interface NextStepCardProps {
  to: string;
  icon: string;
  iconBg?: string;
  label: string;
  title: string;
}

export function NextStepCard({ to, icon, iconBg, label, title }: NextStepCardProps) {
  const navigate = useNavigate();
  return (
    <motion.button
      type="button"
      className="next-step-card"
      onClick={() => navigate(to)}
      whileTap={{ scale: 0.98 }}
      whileHover={{ y: -2 }}
    >
      <Icon3D src={icon} size={52} bg={iconBg} rounded="30%" />
      <div className="next-step-card__text">
        <div className="next-step-card__label">{label}</div>
        <div className="next-step-card__title">{title}</div>
      </div>
      <span className="next-step-card__arrow">›</span>
    </motion.button>
  );
}
