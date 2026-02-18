import { Router } from "express";
import { z } from "zod";
import { validateBody } from "../middleware/validate";
import { createCheckoutSession } from "../services/stripeService";

const router = Router();

const CreateSessionSchema = z.object({
  license_key: z.string().min(10)
});

router.post("/create-session", validateBody(CreateSessionSchema), async (req, res, next) => {
  try {
    const r = await createCheckoutSession(req.body);
    res.json(r);
  } catch (e) {
    next(e);
  }
});

export default router;
