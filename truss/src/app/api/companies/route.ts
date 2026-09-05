import { NextResponse } from "next/server";
import { listCompanies } from "@/lib/store";

// GET /api/companies
export async function GET() {
  return NextResponse.json({ companies: listCompanies() });
}
