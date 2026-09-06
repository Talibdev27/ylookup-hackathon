import { NextResponse } from "next/server";
import { getCompany, listDocumentsForCompany } from "@/lib/store";

// GET /api/companies/{company_id}/documents
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ companyId: string }> }
) {
  const { companyId } = await params;
  if (!getCompany(companyId)) {
    return NextResponse.json({ error: "Company not found" }, { status: 404 });
  }
  return NextResponse.json({ documents: await listDocumentsForCompany(companyId) });
}
