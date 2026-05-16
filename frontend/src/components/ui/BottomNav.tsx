import { motion } from "framer-motion";
import type { Screen } from "@/stores/app";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";

/**
 * Bottom navigation — 5 entries with a centered FAB-style "Practices"
 * compass-rose button. Mapping below decides which tab is highlighted
 * for any given screen, including nested screens (e.g. tarot, moon and
 * mac all live under the Practices tab).
 */
const SCREEN_TO_TAB: Partial<Record<Screen, NavId>> = {
  home: "home",
  horoscopes: "horoscopes",
  discover: "discover",
  tarot: "discover",
  moon: "discover",
  mac: "discover",
  natal: "discover",
  transits: "discover",
  synastry: "discover",
  synastry_invite: "discover",
  glossary: "discover",
  glossary_term: "discover",
  news: "discover",
  news_detail: "discover",
  premium: "premium",
  profile: "profile",
};

type NavId = "home" | "horoscopes" | "discover" | "premium" | "profile";

interface NavItem {
  id: NavId;
  screen: Screen;
  label: string;
  icon: JSX.Element;
  fab?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "home",
    screen: "home",
    label: "Главная",
    icon: <HomeIcon />,
  },
  {
    id: "horoscopes",
    screen: "horoscopes",
    label: "Гороскопы",
    icon: <PlanetIcon />,
  },
  {
    id: "discover",
    screen: "discover",
    label: "Практики",
    icon: <CompassRoseIcon />,
    fab: true,
  },
  {
    id: "premium",
    screen: "premium",
    label: "Звёзды",
    icon: <StarIcon />,
  },
  {
    id: "profile",
    screen: "profile",
    label: "Профиль",
    icon: <UserIcon />,
  },
];

export function BottomNav() {
  const { screen, setScreen } = useAppStore();
  const { selection } = useHaptic();
  const activeTab = SCREEN_TO_TAB[screen] ?? "home";

  const handleNav = (item: NavItem) => {
    if (item.screen === screen) return;
    selection();
    setScreen(item.screen);
  };

  return (
    <nav className="bottom-nav bottom-nav--fab">
      {NAV_ITEMS.map((item) => {
        const active = activeTab === item.id;
        if (item.fab) {
          return (
            <button
              key={item.id}
              className={`nav-fab-item ${active ? "active" : ""}`}
              onClick={() => handleNav(item)}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
            >
              <span className={`nav-fab ${active ? "active" : ""}`}>
                {item.icon}
              </span>
              <span className="nav-label">{item.label}</span>
              {active && (
                <motion.div
                  className="nav-fab-dot"
                  layoutId="nav-fab-dot"
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              )}
            </button>
          );
        }
        return (
          <button
            key={item.id}
            className={`nav-item ${active ? "active" : ""}`}
            onClick={() => handleNav(item)}
            aria-label={item.label}
            aria-current={active ? "page" : undefined}
          >
            {active && (
              <motion.div
                className="nav-indicator"
                layoutId="nav-indicator"
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
              />
            )}
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

/* ── Icons ───────────────────────────────────────────────────────────────── */

function HomeIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M3 9.5L10 3l7 6.5V17a1 1 0 0 1-1 1h-3v-5h-6v5H4a1 1 0 0 1-1-1V9.5z" />
    </svg>
  );
}

function PlanetIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="5" />
      <ellipse cx="10" cy="10" rx="9" ry="2.6" transform="rotate(-22 10 10)" />
    </svg>
  );
}

function CompassRoseIcon() {
  // Compass rose used for the central FAB
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <polygon points="12,3 13.5,11 12,21 10.5,11" />
      <polygon points="3,12 11,10.5 21,12 11,13.5" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <polygon points="10 1.7 12.6 7.5 18.8 8.2 14.1 12.5 15.4 18.6 10 15.4 4.6 18.6 5.9 12.5 1.2 8.2 7.4 7.5" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="7" r="3.5" />
      <path d="M2.5 18c0-4.142 3.358-7 7.5-7s7.5 2.858 7.5 7" />
    </svg>
  );
}
