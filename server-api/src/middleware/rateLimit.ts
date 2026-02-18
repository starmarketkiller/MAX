import rateLimit from "express-rate-limit";
import { config } from "../config";

export const ipLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: config.rlPerIpPerMin,
  standardHeaders: true,
  legacyHeaders: false,
});

export const licenseLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: config.rlPerLicensePerMin,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    const lk = (req.body?.license_key || req.query?.license_key || "").toString();
    return lk ? `LK:${lk}` : `LK:__missing__:${req.ip}`;
  }
});
