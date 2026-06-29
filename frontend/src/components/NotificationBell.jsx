import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import api from "@/lib/api";

export default function NotificationBell() {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchCount = async () => {
      try {
        const { data } = await api.get("/coach/notifications");
        if (!cancelled) setUnread(data.unread || 0);
      } catch (e) { console.warn("notification bell fetch failed", e); }
    };
    fetchCount();
    const iv = setInterval(fetchCount, 5 * 60 * 1000); // every 5 min
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  return (
    <Link to="/coach" title="Notifiche del Coach"
          className="relative h-9 w-9 rounded-lg border border-border hover:bg-secondary flex items-center justify-center"
          data-testid="header-bell-btn">
      <Bell className="h-4 w-4"/>
      {unread > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center"
              data-testid="header-bell-badge">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}
