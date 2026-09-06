import { NextResponse } from "next/server";
import { createUploadedDocument, finishProcessing, getAnalysis, getCompany, getStatement } from "@/lib/store";
import type { Document } from "@/lib/types";

const EXT_TO_FORMAT: Record<string, Document["sourceFormat"]> = {
  pdf: "pdf",
  jpg: "jpg",
  jpeg: "jpg",
  png: "png",
  xlsx: "excel",
  xls: "excel",
  csv: "csv",
};

function guessStatementKind(name: string): Document["statementKind"] {
  const n = name.toLowerCase();
  if (n.includes("income") || n.includes("p&l") || n.includes("profit")) return "income_statement";
  if (n.includes("cash")) return "cash_flow";
  return "balance_sheet";
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// POST /api/documents/upload — multipart form: file, companyId, and optional statementKind.
// No real OCR/LLM behind this (see docs/truss1.0.md) — it simulates the processing delay
// server-side and returns plausible structured data.
export async function POST(req: Request) {
  const form = await req.formData().catch(() => null);
  if (!form) {
    return NextResponse.json({ error: "Expected multipart/form-data" }, { status: 400 });
  }

  const companyId = form.get("companyId");
  const file = form.get("file");

  if (typeof companyId !== "string" || !getCompany(companyId)) {
    return NextResponse.json({ error: "Unknown companyId" }, { status: 400 });
  }
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Missing file" }, { status: 400 });
  }

  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const sourceFormat = EXT_TO_FORMAT[ext] ?? "screenshot";
  const statementKindField = form.get("statementKind");
  const statementKind =
    typeof statementKindField === "string" && statementKindField
      ? (statementKindField as Document["statementKind"])
      : guessStatementKind(file.name);

  const doc = await createUploadedDocument({
    companyId,
    name: file.name.replace(/\.[^.]+$/, ""),
    sourceFormat,
    statementKind,
  });

  await sleep(1400);
  await finishProcessing(doc.id);

  return NextResponse.json({
    document: doc,
    statement: await getStatement(doc.id),
    analysis: await getAnalysis(doc.id),
  });
}
