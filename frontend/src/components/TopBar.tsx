import { useNavigate } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";

// 브라우저 탭 제목·아이콘은 "약관형광펜"으로 고정한다(index.html의 <title>, favicon.svg) —
// 페이지를 옮겨다녀도 바뀌지 않아야 하므로 여기서 document.title을 건드리지 않는다.
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
