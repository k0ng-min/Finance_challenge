import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon3D } from "../components/Icon3D";

const CARDS = [
  { to: "/trip", icon: "suitcase", bg: "var(--tan)", title: "내 여행 준비", desc: "여행 정보로 딱 맞는 보장을 찾아드려요" },
  { to: "/policies", icon: "umbrella", bg: "var(--orange-soft)", title: "내 보험 보관함", desc: "가입한 보험을 한 곳에 안전하게" },
  { to: "/incident", icon: "chat-bubble", bg: "var(--yellow-soft)", title: "사고가 발생했어요", desc: "당황하지 마세요, 하나씩 도와드릴게요" },
  { to: "/checklist", icon: "file-text", bg: "var(--mint-soft)", title: "서류 체크", desc: "필요한 서류를 빠짐없이" },
  { to: "/mistakes", icon: "shield", bg: "var(--orange-soft)", title: "실수 방지 점검", desc: "놓친 건 없는지 한 번 더" },
  { to: "/highlights", icon: "notebook", bg: "var(--tan)", title: "약관 형광펜", desc: "근거가 되는 약관을 색깔로" },
];

export function Home() {
  const navigate = useNavigate();
  return (
    <div className="page home">
      <motion.div
        className="home__hero"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <motion.div
          initial={{ scale: 0.6, rotate: -8, opacity: 0 }}
          animate={{ scale: 1, rotate: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 220, damping: 16 }}
        >
          <Icon3D src="explorer" size={104} bg="var(--yellow-soft)" rounded="38%" />
        </motion.div>
        <h1 className="home__title">안녕하세요!{"\n"}오늘도 든든하게 떠나볼까요?</h1>
        <p className="home__subtitle">
          6개 보험사의 실제 약관을 근거로, 여행 전 보장 비교부터 사고 후 청구까지 한 곳에서 도와드려요.
        </p>
      </motion.div>

      <div className="home__grid">
        {CARDS.map((c, i) => (
          <motion.button
            key={c.to}
            className="home-card"
            onClick={() => navigate(c.to)}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i, duration: 0.3 }}
            whileTap={{ scale: 0.98 }}
            whileHover={{ y: -3 }}
          >
            <Icon3D src={c.icon} size={68} bg={c.bg} rounded="32%" />
            <div className="home-card__text">
              <strong>{c.title}</strong>
              <span>{c.desc}</span>
            </div>
            <span className="home-card__arrow">›</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
