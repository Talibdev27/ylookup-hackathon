import { NextResponse } from "next/server";
import { getDocument, getStatement } from "@/lib/store";

// GET /api/documents/{document_id}/financial-data
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ documentId: string }> }
) {
  const { documentId } = await params;
  const doc = await getDocument(documentId);
  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }
  const statement = await getStatement(documentId);
  if (!statement) {
    return NextResponse.json({ error: "No structured data for this document yet" }, { status: 404 });
  }
  return NextResponse.json(statement);
}
