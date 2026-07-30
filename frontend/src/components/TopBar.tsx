import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";

const APP_NAME = "여행자보험 전 생애주기 AI";

export function TopBar({ title }: { title: string }) {
  const navigate = useNavigate();
  useEffect(() => {
    document.title = title || APP_NAME;
    return () => {
      document.title = APP_NAME;
    };
  }, [title]);
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
