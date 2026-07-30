import type { ReactNode } from "react";
import { motion } from "framer-motion";

/** 큼직한 히어로 3D 아이콘들이 가만히 멈춰있지 않도록 은은하게 좌우로 흔들리는 idle 애니메이션을 씌운다. */
export function FloatingIcon({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.div
      animate={{ rotate: [-4, 4, -4], y: [0, -4, 0] }}
      transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay }}
      style={{ display: "inline-block" }}
    >
      {children}
    </motion.div>
  );
}
