import { Router } from "express";
import { z } from "zod";
import { validateBody } from "../middleware/validate";
import { licenseLimiter } from "../middleware/rateLimit";
import { verifyAndBindSeat } from "../services/licenseService";

const router = Router();

const VerifySchema = z.object({
  license_key: z.string().min(10),
  account_login: z.union([z.number().int().nonnegative(), z.string()]).transform((v) => BigInt(v)),
  account_server: z.string().min(3).max(128),
  ea_id: z.string().min(2).max(64),
  ea_version: z.string().min(1).max(32)
});

router.post(
  "/verify",
  licenseLimiter,
  validateBody(VerifySchema),
  async (req, res, next) => {
    try {
      const r = await verifyAndBindSeat(req.body);
      res.json(r);
    } catch (e) {
      next(e);
    }
  }
);

export default router;
