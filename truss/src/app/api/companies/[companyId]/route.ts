import { NextResponse } from "next/server";
import { getCompany } from "@/lib/store";

// GET /api/companies/{company_id}
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ companyId: string }> }
) {
  const { companyId } = await params;
  const company = getCompany(companyId);
  if (!company) {
    return NextResponse.json({ error: "Company not found" }, { status: 404 });
  }
  return NextResponse.json(company);
}
