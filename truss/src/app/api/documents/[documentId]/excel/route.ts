import ExcelJS from "exceljs";
import { NextResponse } from "next/server";
import { getCompany, getDocument, getStatement } from "@/lib/store";

// GET /api/documents/{document_id}/excel — a real .xlsx built from the structured data,
// not a fake download. See docs/truss1.0.md.
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
  const company = getCompany(doc.companyId);

  const workbook = new ExcelJS.Workbook();
  workbook.creator = "TRUSS";
  const sheet = workbook.addWorksheet(doc.statementKind.replace("_", " "));

  sheet.addRow([company?.name ?? "", doc.name]);
  sheet.addRow([]);

  const header = ["Metric", ...statement.periods];
  sheet.addRow(header).font = { bold: true };

  for (const line of statement.lines) {
    sheet.addRow([line.metric, ...statement.periods.map((p) => line.values[p] ?? "")]);
  }

  sheet.getColumn(1).width = 28;
  statement.periods.forEach((_, i) => {
    sheet.getColumn(i + 2).width = 16;
    sheet.getColumn(i + 2).numFmt = '"£"#,##0';
  });

  const buffer = await workbook.xlsx.writeBuffer();
  const filename = `${company?.name ?? "company"}-${doc.name}`.replace(/\s+/g, "_") + ".xlsx";

  return new NextResponse(buffer as unknown as BodyInit, {
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}
