import Stripe from "stripe";
import { config } from "../config";
import { prisma } from "../prisma";
import { LicenseStatus } from "@prisma/client";
import { normalizeLicenseKey } from "../utils/licenseKey";

export const stripe = new Stripe(config.stripeSecretKey, {
  apiVersion: "2024-06-20"
});

function mapSubStatusToLicenseStatus(subStatus: Stripe.Subscription.Status): LicenseStatus {
  if (subStatus === "active" || subStatus === "trialing") return LicenseStatus.ACTIVE;
  if (subStatus === "past_due" || subStatus === "unpaid") return LicenseStatus.SUSPENDED;
  if (subStatus === "canceled") return LicenseStatus.CANCELED;
  return LicenseStatus.SUSPENDED;
}

export async function handleStripeWebhook(event: Stripe.Event) {
  switch (event.type) {
    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const sub = event.data.object as Stripe.Subscription;
      await upsertSubscription(sub);
      break;
    }

    case "invoice.paid": {
      const inv = event.data.object as Stripe.Invoice;
      if (inv.subscription) {
        const sub = await stripe.subscriptions.retrieve(inv.subscription as string);
        await upsertSubscription(sub);
      }
      break;
    }

    case "invoice.payment_failed": {
      const inv = event.data.object as Stripe.Invoice;
      if (inv.subscription) {
        const sub = await stripe.subscriptions.retrieve(inv.subscription as string);
        await upsertSubscription(sub);
      }
      break;
    }

    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      await handleCheckoutCompleted(session);
      break;
    }

    default:
      break;
  }
}

async function upsertSubscription(sub: Stripe.Subscription) {
  const currentPeriodEnd = sub.current_period_end ? new Date(sub.current_period_end * 1000) : null;
  const status = mapSubStatusToLicenseStatus(sub.status);

  const licBySub = await prisma.license.findFirst({
    where: { stripeSubscriptionId: sub.id }
  });

  if (licBySub) {
    await prisma.license.update({
      where: { id: licBySub.id },
      data: {
        stripeCustomerId: (sub.customer as string) || licBySub.stripeCustomerId,
        status,
        currentPeriodEnd
      }
    });
    await prisma.licenseEvent.create({
      data: {
        licenseId: licBySub.id,
        eventType: "WEBHOOK_UPDATE",
        payload: { type: "subscription", subId: sub.id, status: sub.status, currentPeriodEnd }
      }
    });
    return;
  }

  await prisma.licenseEvent.create({
    data: {
      licenseId: null,
      eventType: "WEBHOOK_UPDATE",
      payload: { type: "subscription_unlinked", subId: sub.id, status: sub.status, currentPeriodEnd }
    }
  });
}

async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const licenseKey = normalizeLicenseKey((session.metadata?.license_key || "").toString());
  if (!licenseKey) return;

  const customerId = (session.customer as string) || null;
  const subId = (session.subscription as string) || null;
  if (!subId) return;

  const sub = await stripe.subscriptions.retrieve(subId);
  const currentPeriodEnd = sub.current_period_end ? new Date(sub.current_period_end * 1000) : null;
  const status = mapSubStatusToLicenseStatus(sub.status);

  const lic = await prisma.license.findUnique({ where: { licenseKey } });
  if (!lic) {
    await prisma.licenseEvent.create({
      data: {
        licenseId: null,
        eventType: "WEBHOOK_UPDATE",
        payload: { type: "checkout_completed_license_not_found", licenseKey, customerId, subId }
      }
    });
    return;
  }

  await prisma.license.update({
    where: { id: lic.id },
    data: {
      stripeCustomerId: customerId || lic.stripeCustomerId,
      stripeSubscriptionId: subId,
      status,
      currentPeriodEnd
    }
  });

  await prisma.licenseEvent.create({
    data: {
      licenseId: lic.id,
      eventType: "WEBHOOK_UPDATE",
      payload: { type: "checkout_completed_linked", licenseKey, customerId, subId, status: sub.status, currentPeriodEnd }
    }
  });
}

export async function createCheckoutSession(params: { license_key: string }) {
  const licenseKey = normalizeLicenseKey(params.license_key);

  const lic = await prisma.license.findUnique({ where: { licenseKey } });
  if (!lic) throw new Error("LICENSE_NOT_FOUND");

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    line_items: [{ price: config.priceIdPro199, quantity: 1 }],
    success_url: `${config.baseUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${config.baseUrl}/cancel`,
    metadata: { license_key: licenseKey }
  });

  await prisma.licenseEvent.create({
    data: {
      licenseId: lic.id,
      eventType: "CHECKOUT_CREATED",
      payload: { sessionId: session.id }
    }
  });

  return { url: session.url };
}
