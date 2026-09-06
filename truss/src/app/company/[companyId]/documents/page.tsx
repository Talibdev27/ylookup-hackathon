import { listDocumentsForCompany } from "@/lib/store";
import { DocumentsBrowser } from "@/components/DocumentsBrowser";
import { BackendUpload } from "@/components/BackendUpload";
import { fetchCompanies } from "@/lib/backend";

export default async function CompanyDocumentsPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;

  // Real companies (the Python matcher's own four funds) get real uploads, wired to the
  // Flask backend; everything else keeps the mock upload flow. See
  // docs/backend-integration.md for why these are two different data paths, and
  // src/ui/app.py's /api/upload and /api/gl-migration/upload for what this calls.
  const realCompanies = await fetchCompanies();
  if (realCompanies.some((company) => company.id === companyId)) {
    return <BackendUpload companyId={companyId} />;
  }

  const documents = await listDocumentsForCompany(companyId);
  return <DocumentsBrowser companyId={companyId} documents={documents} />;
}
