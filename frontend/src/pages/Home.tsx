import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon3D } from "../components/Icon3D";
import { FloatingIcon } from "../components/FloatingIcon";
import { ThemeToggle } from "../components/ThemeToggle";
import { PenWriteIcon } from "../components/PenWriteIcon";
import { PenWriteLabel } from "../components/PenWriteLabel";
import { useApp } from "../context/AppContext";

// 자주 쓰는 핵심 기능만 설명과 함께 크게 보여준다.
const MAIN_CARDS = [
  { to: "/trip", icon: "suitcase", title: "내 여행 준비", desc: "여행 정보로 딱 맞는 보장을 찾아드려요" },
  { to: "/incident", icon: "chat-bubble", title: "사고가 발생했어요", desc: "당황하지 마세요, 하나씩 도와드릴게요" },
];

// 나머지는 아이콘 + 이름만 두고, 들어가서 살펴보게 한다.
const QUICK_ITEMS = [
  { to: "/policies", icon: "umbrella", title: "내 보험" },
  { to: "/checklist", icon: "file-text", title: "청구 전 점검" },
  { to: "/premium", icon: "wallet", title: "보험료 비교공시" },
  { to: "/highlights", icon: "notebook", title: "약관 형광펜" },
];

export function Home() {
  const navigate = useNavigate();
  const { isLoggedIn, nickname } = useApp();
  return (
    <div className="page home">
      <div className="home__topbar">
        <ThemeToggle />
        <span className="home__topbar-spacer" />
        <button type="button" className="account-pill" onClick={() => navigate("/account")}>
          <Icon3D src={isLoggedIn ? "key" : "lock"} size={18} />
          {isLoggedIn ? nickname : "로그인"}
        </button>
      </div>

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
          <FloatingIcon>
            <Icon3D src="explorer" size={68} />
          </FloatingIcon>
        </motion.div>
        <h1 className="home__title">안녕하세요!{"\n"}오늘도 든든하게 떠나볼까요?</h1>
        <p className="home__subtitle">
          6개 보험사의 실제 약관을 근거로, 여행 전 보장 비교부터 사고 후 청구까지 한 곳에서 도와드려요.
        </p>
      </motion.div>

      <div className="home__grid">
        {MAIN_CARDS.map((c, i) => (
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
            <Icon3D src={c.icon} size={48} />
            <div className="home-card__text">
              <strong>{c.title}</strong>
              <span>{c.desc}</span>
            </div>
            <span className="home-card__arrow">›</span>
          </motion.button>
        ))}
      </div>

      <div className="home__quick-grid">
        {QUICK_ITEMS.map((c, i) => (
          <motion.button
            key={c.to}
            type="button"
            className="home-quick"
            onClick={() => navigate(c.to)}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.06 * i + 0.16, duration: 0.3 }}
            whileTap={{ scale: 0.95 }}
          >
            {c.to === "/highlights" ? <PenWriteIcon size={34} /> : <Icon3D src={c.icon} size={34} />}
            {c.to === "/highlights" ? (
              <PenWriteLabel text={c.title} />
            ) : (
              <span className="home-quick__label">{c.title}</span>
            )}
          </motion.button>
        ))}
      </div>

      <p className="home__footer">© 2026 BohumPen</p>
    </div>
  );
}
