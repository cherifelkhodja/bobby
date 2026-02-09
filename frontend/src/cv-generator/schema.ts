import { z } from 'zod';

// Content types
const BulletSchema = z.object({
  type: z.literal('bullet'),
  text: z.string(),
  level: z.number().min(0).max(2).default(0),
});

const TextSchema = z.object({
  type: z.literal('text'),
  text: z.string(),
  bold: z.boolean().default(false),
});

const CompetenceSchema = z.object({
  type: z.literal('competence'),
  category: z.string(),
  values: z.string(),
});

const DiplomeSchema = z.object({
  type: z.literal('diplome'),
  date: z.string(),
  titre: z.string(),
  etablissement: z.string(),
});

const ExperienceSchema = z.object({
  type: z.literal('experience'),
  client: z.string(),
  periode: z.string(),
  titre: z.string(),
  description: z.string().optional(),
  content: z.array(z.union([BulletSchema, TextSchema, CompetenceSchema])),
  environnement: z.string().optional(),
});

const ContentItemSchema = z.union([
  BulletSchema,
  TextSchema,
  CompetenceSchema,
  DiplomeSchema,
  ExperienceSchema,
]);

const SubSectionSchema = z.object({
  type: z.literal('subsection'),
  title: z.string(),
  content: z.array(ContentItemSchema),
});

const SectionContentSchema = z.union([ContentItemSchema, SubSectionSchema]);

const SectionSchema = z.object({
  type: z.literal('section'),
  id: z.enum([
    'profil',
    'competences',
    'formations',
    'certifications',
    'experiences',
  ]),
  title: z.string(),
  content: z.array(SectionContentSchema),
});

export const CVSchema = z.object({
  header: z.object({
    titre: z.string(),
    experience: z.string(),
  }),
  sections: z.array(SectionSchema),
});

export type CVData = z.infer<typeof CVSchema>;
export type Section = z.infer<typeof SectionSchema>;
export type SectionContent = z.infer<typeof SectionContentSchema>;
export type ContentItem = z.infer<typeof ContentItemSchema>;
export type Bullet = z.infer<typeof BulletSchema>;
export type TextBlock = z.infer<typeof TextSchema>;
export type Competence = z.infer<typeof CompetenceSchema>;
export type Diplome = z.infer<typeof DiplomeSchema>;
export type Experience = z.infer<typeof ExperienceSchema>;
export type SubSection = z.infer<typeof SubSectionSchema>;

const SECTION_ORDER = [
  'profil',
  'competences',
  'formations',
  'certifications',
  'experiences',
];

export function validateCV(
  data: unknown
):
  | { valid: true; data: CVData }
  | { valid: false; errors: Array<{ path: string; message: string }> } {
  const result = CVSchema.safeParse(data);
  if (!result.success) {
    return {
      valid: false,
      errors: result.error.errors.map((e) => ({
        path: e.path.join('.'),
        message: e.message,
      })),
    };
  }

  // Sort sections in canonical order
  result.data.sections.sort(
    (a, b) => SECTION_ORDER.indexOf(a.id) - SECTION_ORDER.indexOf(b.id)
  );

  return { valid: true, data: result.data };
}
