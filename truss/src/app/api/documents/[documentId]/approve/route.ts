import { NextResponse } from "next/server";
import { getDocument, setDocumentStatus } from "@/lib/store";

// POST /api/documents/{document_id}/approve
export async function POST(
  req: Request,
  { params }: { params: Promise<{ documentId: string }> }
) {
  const { documentId } = await params;
  if (!getDocument(documentId)) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }
  const body = await req.json().catch(() => ({}));
  const reviewedBy = typeof body?.reviewedBy === "string" ? body.reviewedBy : "Reviewer";
  const doc = setDocumentStatus(documentId, "verified", reviewedBy);
  return NextResponse.json(doc);
}
