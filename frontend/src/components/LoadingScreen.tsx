import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Icon3D } from "./Icon3D";

const DEFAULT_MESSAGES = [
  "실제 약관 원문을 대조하고 있어요",
  "보험사별 조건을 비교하고 있어요",
  "근거가 되는 조항을 찾고 있어요",
];

/** 제미나이 호출처럼 몇 초 걸리는 작업을 기다릴 때, 점 세 개 대신 보여주는 전용 로딩 화면.
 * 3D 아이콘이 계속 회전하고, 안내 문구가 몇 초마다 바뀌어 "멈춘 게 아니라 진행 중"임을 알려준다. */
export function LoadingScreen({
  icon = "explorer",
  title = "잠시만 기다려주세요",
  messages = DEFAULT_MESSAGES,
}: {
  icon?: string;
  title?: string;
  messages?: string[];
}) {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setMsgIndex((i) => (i + 1) % messages.length), 1900);
    return () => clearInterval(id);
  }, [messages.length]);

  return (
    <div className="loading-screen">
      <div className="loading-screen__glow" />
      <motion.div
        className="loading-screen__icon"
        animate={{ rotate: 360 }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }}
      >
        <Icon3D src={icon} size={104} />
      </motion.div>
      <h2 className="loading-screen__title">{title}</h2>
      <AnimatePresence mode="wait">
        <motion.p
          key={msgIndex}
          className="loading-screen__msg"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
        >
          {messages[msgIndex]}
        </motion.p>
      </AnimatePresence>
      <div className="loading-screen__dots">
        <motion.span animate={{ y: [0, -6, 0] }} transition={{ duration: 0.9, repeat: Infinity, delay: 0 }} />
        <motion.span animate={{ y: [0, -6, 0] }} transition={{ duration: 0.9, repeat: Infinity, delay: 0.15 }} />
        <motion.span animate={{ y: [0, -6, 0] }} transition={{ duration: 0.9, repeat: Infinity, delay: 0.3 }} />
      </div>
    </div>
  );
}
