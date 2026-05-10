import { lazy, Suspense, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import { BottomNav } from "@/components/ui/BottomNav";
import { usersApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useStartParam, useTelegramReady } from "@/hooks/useTelegram";
import { LoadingScreenFull } from "@/components/screens/LoadingScreen";

const Onboarding = lazy(() =>
  import("@/components/screens/Onboarding").then((m) => ({
    default: m.Onboarding,
  })),
);
const Home = lazy(() =>
  import("@/components/screens/Home").then((m) => ({ default: m.Home })),
);
const Discover = lazy(() =>
  import("@/components/screens/Discover").then((m) => ({
    default: m.Discover,
  })),
);
const Tarot = lazy(() =>
  import("@/components/screens/Tarot").then((m) => ({ default: m.Tarot })),
);
const Moon = lazy(() =>
  import("@/components/screens/Moon").then((m) => ({ default: m.Moon })),
);
const Natal = lazy(() =>
  import("@/components/screens/Natal").then((m) => ({ default: m.Natal })),
);
const Mac = lazy(() =>
  import("@/components/screens/Mac").then((m) => ({ default: m.Mac })),
);
const Profile = lazy(() =>
  import("@/components/screens/Profile").then((m) => ({ default: m.Profile })),
);
const Transits = lazy(() =>
  import("@/components/screens/Transits").then((m) => ({
    default: m.Transits,
  })),
);
const Synastry = lazy(() =>
  import("@/components/screens/Synastry").then((m) => ({
    default: m.Synastry,
  })),
);
const SynastryInvite = lazy(() =>
  import("@/components/screens/SynastryInvite").then((m) => ({
    default: m.SynastryInvite,
  })),
);
const Glossary = lazy(() =>
  import("@/components/screens/Glossary").then((m) => ({
    default: m.Glossary,
  })),
);
const GlossaryTerm = lazy(() =>
  import("@/components/screens/GlossaryTerm").then((m) => ({
    default: m.GlossaryTerm,
  })),
);
const News = lazy(() =>
  import("@/components/screens/News").then((m) => ({
    default: m.News,
  })),
);
const NewsDetail = lazy(() =>
  import("@/components/screens/NewsDetail").then((m) => ({
    default: m.NewsDetail,
  })),
);

function SplashScreen() {
  return (
    <motion.div
      style={{ position: "fixed", inset: 0, zIndex: 999 }}
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
    >
      <LoadingScreenFull />
    </motion.div>
  );
}

export default function App() {
  const {
    screen,
    navDirection,
    setScreen,
    onboardingComplete,
    setOnboardingComplete,
    setUser,
    pendingInviteToken,
    setPendingInviteToken,
  } = useAppStore();
  const [ready, setReady] = useState(false);
  const [synced, setSynced] = useState(false);
  useTelegramReady();
  const startParam = useStartParam();
  const [inviteHandled, setInviteHandled] = useState(false);

  const syncUser = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (u) => {
      setUser(u);
      // If user has no gender/sign — they were deleted or never completed onboarding
      if (!u.gender && !u.sun_sign) {
        setOnboardingComplete(false);
      }
      setSynced(true);
    },
    onError: () => {
      setSynced(true);
    },
  });

  useEffect(() => {
    syncUser.mutate();
    const timer = setTimeout(() => setReady(true), 3500);
    return () => clearTimeout(timer);
  }, []);

  // Capture syn_<token> from start_param into the persisted store as soon as
  // we see it — before splash, before onboarding gate. The token survives a
  // mid-onboarding reload that way.
  useEffect(() => {
    if (startParam?.startsWith("syn_")) {
      const token = startParam.slice(4);
      if (token && token !== pendingInviteToken) {
        setPendingInviteToken(token);
      }
    }
  }, [startParam, pendingInviteToken, setPendingInviteToken]);

  // After both splash timer and sync are done, route the onboarded user.
  // If they have a pending invite waiting, jump straight to the invite
  // landing page; otherwise the usual home screen.
  useEffect(() => {
    if (!ready || !synced || !onboardingComplete) return;
    if (screen !== "onboarding") return;
    setScreen(pendingInviteToken ? "synastry_invite" : "home");
  }, [
    ready,
    synced,
    onboardingComplete,
    screen,
    pendingInviteToken,
    setScreen,
  ]);

  // Already-onboarded user opening a fresh invite link: jump to the invite
  // page immediately. Non-onboarded users wait until onboarding finishes
  // (the effect above handles that branch).
  useEffect(() => {
    if (inviteHandled || !ready || !synced || !onboardingComplete) return;
    if (pendingInviteToken) {
      setScreen("synastry_invite");
      setInviteHandled(true);
    }
  }, [
    pendingInviteToken,
    ready,
    synced,
    onboardingComplete,
    inviteHandled,
    setScreen,
  ]);

  const showSplash = !ready || !synced;
  const showNav = !showSplash && screen !== "onboarding";

  if (showSplash) {
    return (
      <div className="app">
        <AnimatePresence mode="wait">
          <SplashScreen />
        </AnimatePresence>
      </div>
    );
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        <Suspense fallback={null}>
          <AnimatePresence mode="wait">
            <motion.div
              key={screen}
              className="screen-container"
              initial={{ opacity: 0, x: navDirection === "back" ? -20 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: navDirection === "back" ? 20 : -20 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
            >
              {screen === "onboarding" && <Onboarding />}
              {screen === "home" && <Home />}
              {screen === "discover" && <Discover />}
              {screen === "tarot" && <Tarot />}
              {screen === "moon" && <Moon />}
              {screen === "natal" && <Natal />}
              {screen === "mac" && <Mac />}
              {screen === "profile" && <Profile />}
              {screen === "transits" && <Transits />}
              {screen === "synastry" && <Synastry />}
              {screen === "synastry_invite" && <SynastryInvite />}
              {screen === "glossary" && <Glossary />}
              {screen === "glossary_term" && <GlossaryTerm />}
              {screen === "news" && <News />}
              {screen === "news_detail" && <NewsDetail />}
            </motion.div>
          </AnimatePresence>
        </Suspense>

        {showNav && <BottomNav />}
      </div>
    </MotionConfig>
  );
}
