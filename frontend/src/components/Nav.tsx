import { NavLink } from "react-router-dom";
import { Icon3D } from "./Icon3D";

const ITEMS = [
  { to: "/trip", label: "내 여행 준비", icon: "suitcase" },
  { to: "/policies", label: "내 보험 보관함", icon: "umbrella" },
  { to: "/incident", label: "사고가 발생했어요", icon: "chat-bubble" },
  { to: "/checklist", label: "서류 체크", icon: "file-text" },
  { to: "/mistakes", label: "실수 방지 점검", icon: "shield" },
  { to: "/highlights", label: "약관 형광펜", icon: "notebook" },
];

export function Nav() {
  return (
    <nav className="app-nav">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => "app-nav__item" + (isActive ? " app-nav__item--active" : "")}
        >
          <span className="app-nav__icon">
            <Icon3D src={item.icon} size={30} bg="#f6ead9" rounded="32%" />
          </span>
          <span className="app-nav__label">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
