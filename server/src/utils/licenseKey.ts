import crypto from "crypto";

export function generateLicenseKey(): string {
  const chunk = () => crypto.randomBytes(2).toString("hex").toUpperCase().slice(0,4);
  return `EDL-${chunk()}-${chunk()}-${chunk()}`.replace(/[^A-Z0-9-]/g, "X");
}

export function normalizeLicenseKey(key: string): string {
  return key.trim().toUpperCase();
}
