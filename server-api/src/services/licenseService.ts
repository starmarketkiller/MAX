import { prisma } from "../prisma";
import { LicenseStatus } from "@prisma/client";
import { normalizeLicenseKey } from "../utils/licenseKey";
import { config } from "../config";

export type VerifyResult = {
  status: "VALID" | "INVALID";
  expires_at: string | null;
  seats_used: number;
  seats_max: number;
  grace_seconds: number;
  code: string;
  message: string;
};

function seatsUsed(seats: { accountLogin: bigint | null }[]): number {
  return seats.filter(s => s.accountLogin !== null).length;
}

function valid(currentPeriodEnd: Date | null, used: number, code: string, message: string): VerifyResult {
  return {
    status: "VALID",
    expires_at: currentPeriodEnd ? currentPeriodEnd.toISOString() : null,
    seats_used: used,
    seats_max: 2,
    grace_seconds: config.graceSeconds,
    code,
    message
  };
}

function invalid(currentPeriodEnd: Date | null, code: string, message: string): VerifyResult {
  return {
    status: "INVALID",
    expires_at: currentPeriodEnd ? currentPeriodEnd.toISOString() : null,
    seats_used: 0,
    seats_max: 2,
    grace_seconds: config.graceSeconds,
    code,
    message
  };
}

async function logEvent(licenseId: string | null, eventType: string, payload: any) {
  await prisma.licenseEvent.create({
    data: { licenseId, eventType, payload }
  });
}

function safeParams(p: any) {
  return {
    license_key: p.license_key,
    account_login: p.account_login?.toString?.() ?? p.account_login,
    account_server: p.account_server,
    ea_id: p.ea_id,
    ea_version: p.ea_version
  };
}

export async function verifyAndBindSeat(params: {
  license_key: string;
  account_login: bigint;
  account_server: string;
  ea_id: string;
  ea_version: string;
}): Promise<VerifyResult> {
  const licenseKey = normalizeLicenseKey(params.license_key);
  const now = new Date();

  const lic = await prisma.license.findUnique({
    where: { licenseKey },
    include: { seats: true }
  });

  if (!lic) {
    await logEvent(null, "VERIFY_DENY", { code: "NOT_FOUND", licenseKey, ...safeParams(params) });
    return invalid(null, "NOT_FOUND", "License not found");
  }

  if (lic.status === LicenseStatus.SUSPENDED) {
    await logEvent(lic.id, "VERIFY_DENY", { code: "SUSPENDED", ...safeParams(params) });
    return invalid(lic.currentPeriodEnd, "SUSPENDED", "Subscription suspended (payment issue)");
  }
  if (lic.status === LicenseStatus.CANCELED) {
    await logEvent(lic.id, "VERIFY_DENY", { code: "CANCELED", ...safeParams(params) });
    return invalid(lic.currentPeriodEnd, "CANCELED", "Subscription canceled");
  }
  if (!lic.currentPeriodEnd || lic.currentPeriodEnd <= now) {
    if (lic.status !== LicenseStatus.EXPIRED) {
      await prisma.license.update({ where: { id: lic.id }, data: { status: LicenseStatus.EXPIRED } });
    }
    await logEvent(lic.id, "VERIFY_DENY", { code: "EXPIRED", ...safeParams(params) });
    return invalid(lic.currentPeriodEnd, "EXPIRED", "Subscription expired");
  }
  if (lic.status !== LicenseStatus.ACTIVE) {
    await logEvent(lic.id, "VERIFY_DENY", { code: "INVALID_STATUS", status: lic.status, ...safeParams(params) });
    return invalid(lic.currentPeriodEnd, "INVALID_STATUS", "License not active");
  }

  const existing = lic.seats.find(
    (s) => s.accountLogin === params.account_login && (s.accountServer || "") === params.account_server
  );

  if (existing) {
    await prisma.licenseSeat.update({ where: { id: existing.id }, data: { lastSeenAt: now } });
    await logEvent(lic.id, "VERIFY_OK", { bound: true, seatIndex: existing.seatIndex, ...safeParams(params) });
    return valid(lic.currentPeriodEnd, seatsUsed(lic.seats), "OK", "License valid (seat already bound)");
  }

  const freeSeat = lic.seats.find((s) => s.accountLogin === null);
  if (!freeSeat) {
    await logEvent(lic.id, "VERIFY_DENY", { code: "SEATS_FULL", ...safeParams(params) });
    return invalid(lic.currentPeriodEnd, "SEATS_FULL", "Seats full (max 2 MT5 accounts)");
  }

  const updated = await prisma.licenseSeat.updateMany({
    where: { id: freeSeat.id, accountLogin: null },
    data: {
      accountLogin: params.account_login,
      accountServer: params.account_server,
      boundAt: now,
      lastSeenAt: now
    }
  });

  if (updated.count !== 1) {
    const lic2 = await prisma.license.findUnique({ where: { licenseKey }, include: { seats: true } });
    if (!lic2) return invalid(null, "NOT_FOUND", "License not found");

    const ex2 = lic2.seats.find(
      (s) => s.accountLogin === params.account_login && (s.accountServer || "") === params.account_server
    );
    if (ex2) {
      await logEvent(lic.id, "VERIFY_OK", { bound: true, seatIndex: ex2.seatIndex, race: true, ...safeParams(params) });
      return valid(lic.currentPeriodEnd, seatsUsed(lic2.seats), "OK", "License valid (seat already bound)");
    }

    const free2 = lic2.seats.find((s) => s.accountLogin === null);
    if (!free2) {
      await logEvent(lic.id, "VERIFY_DENY", { code: "SEATS_FULL", race: true, ...safeParams(params) });
      return invalid(lic.currentPeriodEnd, "SEATS_FULL", "Seats full (max 2 MT5 accounts)");
    }

    await prisma.licenseSeat.update({
      where: { id: free2.id },
      data: {
        accountLogin: params.account_login,
        accountServer: params.account_server,
        boundAt: now,
        lastSeenAt: now
      }
    });

    await logEvent(lic.id, "BIND_SEAT", { seatIndex: free2.seatIndex, ...safeParams(params) });
    return valid(lic.currentPeriodEnd, seatsUsed(lic2.seats) + 1, "OK", "License valid (seat bound)");
  }

  await logEvent(lic.id, "BIND_SEAT", { seatIndex: freeSeat.seatIndex, ...safeParams(params) });
  return valid(lic.currentPeriodEnd, seatsUsed(lic.seats) + 1, "OK", "License valid (seat bound)");
}

export async function adminUnbindSeat(params: { license_key: string; seat_index: number }) {
  const licenseKey = normalizeLicenseKey(params.license_key);
  const lic = await prisma.license.findUnique({ where: { licenseKey }, include: { seats: true } });
  if (!lic) return { ok: false, error: "NOT_FOUND" };

  const seat = lic.seats.find((s) => s.seatIndex === params.seat_index);
  if (!seat) return { ok: false, error: "SEAT_NOT_FOUND" };

  await prisma.licenseSeat.update({
    where: { id: seat.id },
    data: { accountLogin: null, accountServer: null, boundAt: null, lastSeenAt: null }
  });
  await logEvent(lic.id, "ADMIN_UNBIND", { seatIndex: params.seat_index });

  return { ok: true };
}

export async function getLicenseStatusReadOnly(license_key: string): Promise<VerifyResult | null> {
  const licenseKey = normalizeLicenseKey(license_key);
  const lic = await prisma.license.findUnique({ where: { licenseKey }, include: { seats: true } });
  if (!lic) return null;

  const now = new Date();
  if (!lic.currentPeriodEnd || lic.currentPeriodEnd <= now || lic.status !== LicenseStatus.ACTIVE) {
    return invalid(lic.currentPeriodEnd, lic.status === LicenseStatus.ACTIVE ? "EXPIRED" : lic.status, "License not active");
  }
  return valid(lic.currentPeriodEnd, seatsUsed(lic.seats), "OK", "License valid");
}
