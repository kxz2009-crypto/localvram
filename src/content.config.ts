import { defineCollection, z } from "astro:content";

const blog = defineCollection({
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

export const collections = { blog };
