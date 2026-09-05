import { NextResponse } from "next/server";
import { listFundManagers } from "@/lib/store";

// GET /api/fund-managers — not in the PRD's endpoint list (§32), added so the Fund
// Manager Dashboard has something real to call rather than importing mock data directly.
export async function GET() {
  return NextResponse.json({ fundManagers: listFundManagers() });
}
