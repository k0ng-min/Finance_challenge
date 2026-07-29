import { Icon3D } from "./Icon3D";

interface PageHeroProps {
  icon: string;
  iconBg?: string;
  eyebrow: string;
  title: string;
  subtitle: string;
}

export function PageHero({ icon, iconBg, eyebrow, title, subtitle }: PageHeroProps) {
  return (
    <div className="hero">
      <div className="hero__blob hero__blob--a" />
      <div className="hero__blob hero__blob--b" />
      <div className="hero__text">
        <span className="hero__eyebrow">{eyebrow}</span>
        <h1 className="hero__title">{title}</h1>
        <p className="hero__subtitle">{subtitle}</p>
      </div>
      <Icon3D src={icon} size={116} bg={iconBg} rounded="34%" className="hero__icon" />
    </div>
  );
}
