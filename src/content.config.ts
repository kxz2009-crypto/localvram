import { defineCollection, z } from "astro:content";

const blog = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    lang: z.enum(["en", "zh"]).default("en"),
    intent: z.enum(["troubleshooting", "hardware", "benchmark", "guide", "cost"]).default("guide")
  })
});

const blogI18n = defineCollection({
  type: "content"
});

export const collections = {
  blog,
  "blog-i18n": blogI18n
};
