import { ReviewQueue } from "@/components/ReviewQueue";

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  return <ReviewQueue companyId={companyId} />;
}
