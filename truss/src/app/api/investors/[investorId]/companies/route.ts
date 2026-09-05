import { NextResponse } from "next/server";
import { getInvestor, listCompaniesForInvestor } from "@/lib/store";

// GET /api/investors/{investorId}/companies
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ investorId: string }> }
) {
  const { investorId } = await params;
  const investor = getInvestor(investorId);
  if (!investor) {
    return NextResponse.json({ error: "Investor not found" }, { status: 404 });
  }
  return NextResponse.json({ companies: listCompaniesForInvestor(investorId) });
}
