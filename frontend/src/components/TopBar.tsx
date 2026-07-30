import { useNavigate } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";

export function TopBar({ title }: { title: string }) {
  const navigate = useNavigate();
  return (
    <div className="topbar">
      <button className="topbar__home" onClick={() => navigate("/")} aria-label="홈으로">
        ←
      </button>
      <span className="topbar__title">{title}</span>
      <span className="topbar__spacer" />
      <ThemeToggle />
    </div>
  );
}
