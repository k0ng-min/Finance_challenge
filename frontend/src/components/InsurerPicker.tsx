import { motion } from "framer-motion";
import { INSURERS } from "../data/insurers";

interface InsurerPickerProps {
  value: string;
  onChange: (name: string) => void;
}

export function InsurerPicker({ value, onChange }: InsurerPickerProps) {
  return (
    <div className="insurer-grid">
      {INSURERS.map((ins, i) => {
        const active = value === ins.name;
        return (
          <motion.button
            key={ins.code}
            type="button"
            className={`insurer-card${active ? " insurer-card--active" : ""}`}
            // 고른 보험사를 다시 누르면 선택이 풀린다 — 이 칸은 "모르면 비워두세요"인데
            // 한 번 누르면 비울 방법이 없어서 창을 닫았다 다시 열어야 했다.
            onClick={() => onChange(active ? "" : ins.name)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            whileTap={{ scale: 0.95 }}
            whileHover={{ y: -2 }}
          >
            <span className="insurer-card__logo">
              <img src={ins.logo} alt={ins.name} />
            </span>
            <span className="insurer-card__name">{ins.name}</span>
          </motion.button>
        );
      })}
    </div>
  );
}
