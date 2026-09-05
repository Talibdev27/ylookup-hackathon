import { NextResponse } from "next/server";
import { getAnalysis, getDocument } from "@/lib/store";

// GET /api/documents/{document_id}/analysis
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ documentId: string }> }
) {
  const { documentId } = await params;
  const doc = getDocument(documentId);
  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }
  return NextResponse.json(getAnalysis(documentId));
}
