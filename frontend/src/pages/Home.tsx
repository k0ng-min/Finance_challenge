import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon3D } from "../components/Icon3D";
import { ThemeToggle } from "../components/ThemeToggle";
import { PenWriteCompass } from "../components/PenWriteCompass";
import { useApp } from "../context/AppContext";
import { INSURER_COUNT } from "../data/insurers";

// 자주 쓰는 핵심 기능만 설명과 함께 크게 보여준다.
const MAIN_CARDS = [
  { to: "/trip", icon: "suitcase", title: "내 여행 준비", desc: "여행 정보로 딱 맞는 보장을 찾아드려요" },
  { to: "/incident", icon: "collision", title: "사고가 발생했어요", desc: "당황하지 마세요, 하나씩 도와드릴게요" },
];

// 나머지는 아이콘 + 이름만 두고, 들어가서 살펴보게 한다. 4칸을 넘기지 않는다 —
// 칸이 늘면 한 줄이 두 줄이 되면서 히어로가 눌린다.
//
// 첫 칸만 로그인 상태에 따라 바뀐다. 「내 보험」은 로그인해야 쓸 수 있는 화면이라
// 비로그인 상태에서는 눌러봐야 로그인 안내로 튕긴다 — 그 자리에 계정 없이도 볼 수 있는
// 「보험료 비교」를 둔다. 로그인하면 보험료 비교는 「내 보험」 화면 안의 버튼으로 들어간다.
const QUICK_LOGGED_IN = { to: "/policies", icon: "umbrella", title: "내 보험" };
const QUICK_GUEST = { to: "/premium", icon: "wallet", title: "보험료 비교" };
const QUICK_REST = [
  { to: "/checklist", icon: "file-text", title: "청구 전 점검" },
  { to: "/onsite", icon: "airplane", title: "해외 서류 챙기기" },
  { to: "/highlights", icon: "highlighter", title: "약관 형광펜" },
];

export function Home() {
  const navigate = useNavigate();
  const { isLoggedIn, nickname } = useApp();
  const quickItems = [isLoggedIn ? QUICK_LOGGED_IN : QUICK_GUEST, ...QUICK_REST];
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
          <PenWriteCompass />
        </motion.div>
        <h1 className="home__title">안녕하세요!{"\n"}오늘도 든든하게 떠나볼까요?</h1>
        <p className="home__subtitle">
          {INSURER_COUNT}개 보험사의 실제 약관을 근거로, 여행 전 보장 비교부터 사고 후 청구까지 한 곳에서 도와드려요.
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
        {quickItems.map((c, i) => (
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
            <Icon3D src={c.icon} size={34} />
            <span className="home-quick__label">{c.title}</span>
          </motion.button>
        ))}
      </div>

      <p className="home__footer">© 2026 BohumPen</p>
    </div>
  );
}
