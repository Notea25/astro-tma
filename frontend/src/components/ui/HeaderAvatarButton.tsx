import { useState } from "react";
import { useAppStore } from "@/stores/app";
import { useHaptic, useTelegramUser } from "@/hooks/useTelegram";

export function HeaderAvatarButton() {
  const setScreen = useAppStore((s) => s.setScreen);
  const user = useAppStore((s) => s.user);
  const tgUser = useTelegramUser();
  const { impact } = useHaptic();
  const [photoFailed, setPhotoFailed] = useState(false);

  const showPhoto = !!tgUser.photoUrl && !photoFailed;
  const initial =
    user?.name?.[0]?.toUpperCase() ||
    tgUser.firstName?.[0]?.toUpperCase() ||
    "?";

  return (
    <button
      className={`header-avatar${showPhoto ? " header-avatar--photo" : ""}`}
      onClick={() => {
        impact("light");
        setScreen("profile");
      }}
      aria-label="Открыть профиль"
    >
      {showPhoto ? (
        <img
          src={tgUser.photoUrl}
          alt=""
          onError={() => setPhotoFailed(true)}
        />
      ) : (
        initial
      )}
    </button>
  );
}
