import crypto from "crypto";
import { Request, Response, NextFunction } from "express";
import { config } from "../config";

function verifyInitData(initData: string, botToken: string): boolean {
  if (!initData) return false;
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if (!hash) return false;

  params.delete("hash");
  const dataCheckString = Array.from(params.keys())
    .sort()
    .map((k) => `${k}=${params.get(k)}`)
    .join("\n");

  const secretKey = crypto.createHash("sha256").update(botToken).digest();
  const calc = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");
  return calc === hash;
}

export function tgInitDataAuth(req: Request, res: Response, next: NextFunction) {
  if (config.devBypassInitData) return next();
  const initData = (req.header("x-tg-initdata") || "").toString();
  const ok = verifyInitData(initData, config.botToken);
  if (!ok) return res.status(401).json({ error: "UNAUTHORIZED_INITDATA" });
  next();
}

export function verifyInitDataRaw(initData: string): boolean {
  if (config.devBypassInitData) return true;
  return verifyInitData(initData, config.botToken);
}
