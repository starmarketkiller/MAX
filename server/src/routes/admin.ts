import { Router } from "express";
import { z } from "zod";
import { validateBody } from "../middleware/validate";
import { adminAuth } from "../middleware/adminAuth";
import { adminUnbindSeat } from "../services/licenseService";
import { prisma } from "../prisma";

const router = Router();

const UnbindSchema = z.object({
  license_key: z.string().min(10),
  seat_index: z.number().int().min(0).max(1)
});

router.post("/license/unbind", adminAuth, validateBody(UnbindSchema), async (req, res) => {
  const r = await adminUnbindSeat(req.body);
  if (!r.ok) return res.status(404).json({ ok: false, error: r.error });
  res.json({ ok: true });
});

router.get("/license/status/:license_key", adminAuth, async (req, res) => {
  const key = req.params.license_key.toUpperCase();
  const lic = await prisma.license.findUnique({
    where: { licenseKey: key },
    include: { seats: true }
  });
  if (!lic) return res.status(404).json({ error: "NOT_FOUND" });

  res.json({
    license_key: lic.licenseKey,
    plan: lic.plan,
    status: lic.status,
    current_period_end: lic.currentPeriodEnd?.toISOString() ?? null,
    seats: lic.seats.map(s => ({
      seat_index: s.seatIndex,
      account_login: s.accountLogin ? s.accountLogin.toString() : null,
      account_server: s.accountServer ?? null,
      bound_at: s.boundAt?.toISOString() ?? null,
      last_seen_at: s.lastSeenAt?.toISOString() ?? null
    }))
  });
});

export default router;
