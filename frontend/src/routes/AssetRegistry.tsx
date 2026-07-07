import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { AssetRegistryContent } from "@/components/assets/AssetRegistryContent";

export function AssetRegistry() {
  return (
    <AppShell>
      <PageHeader
        title="Asset Registry"
        subtitle="Plant hierarchy and equipment register · Meridian Specialty Chemicals"
      />
      <AssetRegistryContent />
    </AppShell>
  );
}
