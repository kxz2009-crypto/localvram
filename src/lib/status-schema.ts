type StatusSchemaItem = {
  name: string;
  path: string;
};

type StatusSchemaOptions = {
  name: string;
  description: string;
  path: string;
  dateModified?: string;
  keywords?: string[];
};

const SITE_ORIGIN = "https://localvram.com";
const ORGANIZATION = {
  "@type": "Organization",
  name: "LocalVRAM",
  url: `${SITE_ORIGIN}/en/`,
};

function absoluteUrl(path: string): string {
  return new URL(path, SITE_ORIGIN).toString();
}

function cleanDate(value: unknown): string | undefined {
  const normalized = String(value ?? "").trim();
  return normalized || undefined;
}

function breadcrumb(path: string, name: string) {
  const baseItems = [
    {
      "@type": "ListItem",
      position: 1,
      name: "LocalVRAM",
      item: absoluteUrl("/en/"),
    },
    {
      "@type": "ListItem",
      position: 2,
      name: "Operations Health",
      item: absoluteUrl("/en/status/"),
    },
  ];
  const itemListElement =
    path === "/en/status/"
      ? baseItems
      : [
          ...baseItems,
          {
            "@type": "ListItem",
            position: 3,
            name,
            item: absoluteUrl(path),
          },
        ];

  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement,
  };
}

export function buildStatusDatasetSchema(options: StatusSchemaOptions) {
  const dateModified = cleanDate(options.dateModified);
  return [
    {
      "@context": "https://schema.org",
      "@type": "Dataset",
      name: options.name,
      description: options.description,
      url: absoluteUrl(options.path),
      inLanguage: "en",
      isAccessibleForFree: true,
      publisher: ORGANIZATION,
      creator: ORGANIZATION,
      license: absoluteUrl("/legal/"),
      mainEntityOfPage: absoluteUrl(options.path),
      ...(dateModified ? { dateModified } : {}),
      ...(options.keywords?.length ? { keywords: options.keywords.join(", ") } : {}),
    },
    breadcrumb(options.path, options.name),
  ];
}

export function buildStatusCollectionSchema(options: StatusSchemaOptions & { items: StatusSchemaItem[] }) {
  const dateModified = cleanDate(options.dateModified);
  return [
    {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: options.name,
      description: options.description,
      url: absoluteUrl(options.path),
      inLanguage: "en",
      isAccessibleForFree: true,
      publisher: ORGANIZATION,
      ...(dateModified ? { dateModified } : {}),
      mainEntity: {
        "@type": "ItemList",
        numberOfItems: options.items.length,
        itemListElement: options.items.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.name,
          url: absoluteUrl(item.path),
        })),
      },
    },
    breadcrumb(options.path, options.name),
  ];
}
