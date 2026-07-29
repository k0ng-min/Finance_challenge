import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/trip", label: "내 여행 준비", icon: "✈" },
  { to: "/policies", label: "내 보험 보관함", icon: "📁" },
  { to: "/incident", label: "사고가 발생했어요", icon: "🚨" },
  { to: "/checklist", label: "서류 체크", icon: "📋" },
  { to: "/mistakes", label: "실수 방지 점검", icon: "⚠" },
  { to: "/highlights", label: "약관 형광펜", icon: "🖍" },
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
          <span className="app-nav__icon">{item.icon}</span>
          <span className="app-nav__label">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
