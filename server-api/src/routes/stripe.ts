import { Router } from "express";
import { stripe, handleStripeWebhook } from "../services/stripeService";
import { config } from "../config";

const router = Router();

router.post("/webhook", async (req, res) => {
  const sig = req.headers["stripe-signature"];
  if (!sig || typeof sig !== "string") {
    return res.status(400).send("Missing stripe-signature");
  }

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, config.stripeWebhookSecret);
  } catch (err: any) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  try {
    await handleStripeWebhook(event);
    res.json({ received: true });
  } catch (e) {
    console.error("Webhook handler error:", e);
    res.status(500).send("Webhook handler failed");
  }
});

export default router;
