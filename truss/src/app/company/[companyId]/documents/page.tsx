import { listDocumentsForCompany } from "@/lib/store";
import { DocumentsBrowser } from "@/components/DocumentsBrowser";

export default async function CompanyDocumentsPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const documents = listDocumentsForCompany(companyId);
  return <DocumentsBrowser companyId={companyId} documents={documents} />;
}
