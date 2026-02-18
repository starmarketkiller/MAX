import dotenv from "dotenv";
dotenv.config();

function must(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

export const config = {
  port: parseInt(process.env.PORT || "8080", 10),
  baseUrl: process.env.BASE_URL || "http://localhost:8080",
  nodeEnv: process.env.NODE_ENV || "development",

  databaseUrl: must("DATABASE_URL"),

  stripeSecretKey: must("STRIPE_SECRET_KEY"),
  stripeWebhookSecret: must("STRIPE_WEBHOOK_SECRET"),
  priceIdPro199: must("PRICE_ID_PRO_199"),

  adminApiKey: must("ADMIN_API_KEY"),

  rlPerLicensePerMin: parseInt(process.env.RL_PER_LICENSE_PER_MIN || "30", 10),
  rlPerIpPerMin: parseInt(process.env.RL_PER_IP_PER_MIN || "60", 10),

  graceSeconds: 48 * 3600,
};
