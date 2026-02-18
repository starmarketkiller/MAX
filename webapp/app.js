const tg = window.Telegram?.WebApp;
if (tg) tg.ready();

const initData = tg?.initData || "";
const out = document.getElementById("out");
const adminMode = new URLSearchParams(location.search).get("admin") === "1";
if (adminMode) document.getElementById("adminBox").style.display = "block";

async function refresh() {
  const licenseKey = document.getElementById("licenseKey").value.trim();
  if (!licenseKey) return;
  const res = await fetch(`/api/v1/webapp/license/status?license_key=${encodeURIComponent(licenseKey)}`, {
    headers: { "x-tg-initdata": initData }
  });
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}

async function unbind() {
  const licenseKey = document.getElementById("licenseKey").value.trim();
  const seat_index = parseInt(document.getElementById("seatIdx").value, 10);
  const adminKey = document.getElementById("adminKey").value.trim();
  const res = await fetch("/api/v1/admin/license/unbind", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-admin-key": adminKey,
      "x-tg-initdata": initData
    },
    body: JSON.stringify({ license_key: licenseKey, seat_index })
  });
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}

document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("unbindBtn")?.addEventListener("click", unbind);
