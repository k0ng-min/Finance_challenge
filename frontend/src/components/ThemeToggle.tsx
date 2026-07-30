import { motion } from "framer-motion";
import { useTheme } from "../context/ThemeContext";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      className="theme-switch"
      onClick={toggleTheme}
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
      aria-pressed={isDark}
    >
      <motion.span
        className="theme-switch__knob"
        animate={{ x: isDark ? 26 : 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 32 }}
      >
        <img src={`/3d/${isDark ? "moon" : "sun"}.webp`} alt="" className="theme-switch__icon" />
      </motion.span>
    </button>
  );
}
