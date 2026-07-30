import { motion } from "framer-motion";
import { Icon3D } from "./Icon3D";

export function LoadingState({ label = "불러오는 중이에요..." }: { label?: string }) {
  return (
    <div className="loading-state">
      <motion.div
        animate={{ rotate: [0, -8, 8, 0], scale: [1, 1.04, 1] }}
        transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
      >
        <Icon3D src="zoom" size={84} />
      </motion.div>
      <p>{label}</p>
    </div>
  );
}
