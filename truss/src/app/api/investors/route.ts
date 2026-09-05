import { NextResponse } from "next/server";
import { listInvestors } from "@/lib/store";

// GET /api/investors
export async function GET() {
  return NextResponse.json({ investors: listInvestors() });
}
