import { PrismaClient, LicenseStatus } from "@prisma/client";
import { generateLicenseKey } from "../src/utils/licenseKey";

const prisma = new PrismaClient();

async function main() {
  const key = generateLicenseKey();

  const license = await prisma.license.create({
    data: {
      licenseKey: key,
      plan: "PRO_199",
      status: LicenseStatus.ACTIVE,
      currentPeriodEnd: new Date(Date.now() + 30 * 24 * 3600 * 1000),
      seats: {
        create: [{ seatIndex: 0 }, { seatIndex: 1 }]
      }
    },
    include: { seats: true }
  });

  console.log("Seeded license:", license.licenseKey);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
