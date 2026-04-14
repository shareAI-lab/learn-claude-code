export const GENERIC_OVERVIEW_VERSIONS = new Set([
  "s07",
  "s08",
  "s09",
  "s10",
  "s11",
  "s12",
  "s13",
  "s14",
  "s15",
  "s16",
  "s17",
  "s18",
  "s19",
]);

export const GENERIC_SCENARIO_VERSIONS = new Set(GENERIC_OVERVIEW_VERSIONS);

export const GENERIC_ANNOTATION_VERSIONS = new Set(GENERIC_OVERVIEW_VERSIONS);

export function resolveLegacySessionAssetVersion(version: string): string {
  return version;
}

export function isGenericOverviewVersion(version: string): boolean {
  return GENERIC_OVERVIEW_VERSIONS.has(version);
}

export function isGenericScenarioVersion(version: string): boolean {
  return GENERIC_SCENARIO_VERSIONS.has(version);
}

export function isGenericAnnotationVersion(version: string): boolean {
  return GENERIC_ANNOTATION_VERSIONS.has(version);
}
