import { Request, Response, NextFunction } from "express";
import { config } from "../config";

export function adminAuth(req: Request, res: Response, next: NextFunction) {
  const k = req.header("x-admin-key");
  if (!k || k !== config.adminApiKey) {
    return res.status(401).json({ error: "UNAUTHORIZED" });
  }
  next();
}
