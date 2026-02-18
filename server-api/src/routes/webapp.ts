import { Router } from "express";
import { z } from "zod";
import { getLicenseStatusReadOnly } from "../services/licenseService";
import { tgInitDataAuth, verifyInitDataRaw } from "../middleware/tgAuth";

const router = Router();

router.get("/license/status", tgInitDataAuth, async (req, res) => {
  const q = z.object({ license_key: z.string().min(10) }).safeParse(req.query);
  if (!q.success) return res.status(400).json({ error: "BAD_REQUEST" });

  const r = await getLicenseStatusReadOnly(q.data.license_key);
  if (!r) return res.status(404).json({ error: "NOT_FOUND" });
  return res.json(r);
});

router.post("/auth/verify", (req, res) => {
  const initData = (req.header("x-tg-initdata") || "").toString();
  const ok = verifyInitDataRaw(initData);
  if (!ok) return res.status(401).json({ ok: false });
  res.json({ ok: true });
});

export default router;
