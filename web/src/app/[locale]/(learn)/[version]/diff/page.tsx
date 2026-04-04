import { LEARNING_PATH } from "@/lib/constants";
import { DiffPageContent } from "./diff-content";

export function generateStaticParams() {
  return LEARNING_PATH.map((version) => ({ version }));
}

export default async function DiffPage({
  params,
}: {
  params: Promise<{ locale: string; version: string }>;
}) {
  const { version } = await params;
  return <DiffPageContent version={version} />;
}
