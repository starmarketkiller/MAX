import express from "express";
import helmet from "helmet";
import cors from "cors";
import morgan from "morgan";
import path from "path";
import { ipLimiter } from "./middleware/rateLimit";
import { errorHandler } from "./middleware/errorHandler";

import licenseRoutes from "./routes/license";
import adminRoutes from "./routes/admin";
import stripeRoutes from "./routes/stripe";
import checkoutRoutes from "./routes/checkout";
import webappRoutes from "./routes/webapp";

export const app = express();

app.use(helmet());
app.use(cors());

app.use("/api/v1/stripe/webhook", express.raw({ type: "application/json" }));
app.use(express.json({ limit: "1mb" }));

app.use(morgan("combined"));
app.use("/api/", ipLimiter);

const webappPath = path.resolve(process.cwd(), "../webapp");
app.use("/webapp", express.static(webappPath));

app.get("/health", (_req, res) => res.json({ ok: true }));

app.use("/api/v1/license", licenseRoutes);
app.use("/api/v1/admin", adminRoutes);
app.use("/api/v1/stripe", stripeRoutes);
app.use("/api/v1/checkout", checkoutRoutes);
app.use("/api/v1/webapp", webappRoutes);

app.use(errorHandler);
