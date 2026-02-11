import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  ImageRun,
  Footer,
  Table,
  TableRow,
  TableCell,
  WidthType,
  VerticalAlign,
  AlignmentType,
  BorderStyle,
  PageBreak,
  ShadingType,
  TextWrappingType,
  TextWrappingSide,
} from 'docx';
import type { CVData, SectionContent } from './schema';

export interface TemplateConfig {
  name: string;
  colors: {
    primary: string;
    sectionBg: string | null; // null = border-bottom style instead of background
    border: string;
    period: string;
    text: string;
    white: string;
  };
  fonts: {
    main: string;
    sizes: {
      title: number;
      subtitle: number;
      section: number;
      subsection: number;
      text: number;
      footer: number;
    };
  };
  spacing: {
    paragraph: number;
    section: number;
    sectionAfter?: number;
    subsection: number;
    subsectionAfter?: number;
    bullet: number;
    competence: number;
  };
  margins: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
  logo: {
    width: number;
    height: number;
    position?: string; // 'left' (default) | 'right'
  };
  header?: {
    layout?: string; // 'centered' (default) | 'table'
    titleBoldItalic?: boolean;
  };
  subSectionStyle?: {
    borderBottom?: boolean; // default true
  };
  experienceStyle?: {
    titleBold?: boolean;
    titleItalic?: boolean; // default true
    titleBorderBottom?: boolean; // default true
    titleLineSpacing?: number;
  };
  skipSections?: string[]; // section IDs to skip (e.g. ['competences'])
  diplomeStyle?: {
    separator?: string; // default ' - '
    compact?: boolean; // no spacing between diploma entries
  };
  footer: {
    enabled?: boolean; // default true
    line1: string;
    line2: string;
  };
}

function createHelpers(
  config: TemplateConfig,
  logoData: ArrayBuffer | null
) {
  const { colors, fonts, spacing } = config;

  return {
    sectionTitle: (title: string) => {
      const afterSpacing = config.spacing.sectionAfter ?? spacing.subsection;

      if (colors.sectionBg) {
        // Background style (Gemini)
        return new Paragraph({
          spacing: { before: spacing.section, after: afterSpacing },
          shading: {
            type: ShadingType.SOLID,
            color: colors.sectionBg,
            fill: colors.sectionBg,
          },
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({
              text: title,
              bold: true,
              size: fonts.sizes.section,
              color: colors.white,
              font: fonts.main,
            }),
          ],
        });
      }

      // Border-bottom style (Craftmania)
      return new Paragraph({
        spacing: { before: spacing.section, after: afterSpacing },
        border: {
          bottom: {
            style: BorderStyle.SINGLE,
            size: 12,
            space: 3,
            color: colors.border,
          },
        },
        children: [
          new TextRun({
            text: title,
            bold: true,
            size: fonts.sizes.section,
            color: colors.text,
            font: fonts.main,
          }),
        ],
      });
    },

    subSectionTitle: (title: string) => {
      const hasBorder = config.subSectionStyle?.borderBottom !== false;
      const afterSpacing = config.spacing.subsectionAfter ?? spacing.paragraph;

      return new Paragraph({
        spacing: { before: spacing.subsection, after: afterSpacing },
        ...(hasBorder
          ? {
              border: {
                bottom: {
                  style: BorderStyle.SINGLE,
                  size: 18,
                  space: 5,
                  color: colors.border,
                },
              },
            }
          : {}),
        children: [
          new TextRun({
            text: title,
            bold: true,
            size: fonts.sizes.subsection,
            color: colors.text,
            font: fonts.main,
          }),
        ],
      });
    },

    competenceLine: (category: string, values: string) =>
      new Paragraph({
        spacing: { before: spacing.competence, after: spacing.competence },
        children: [
          new TextRun({
            text: category,
            bold: true,
            size: fonts.sizes.text,
            font: fonts.main,
          }),
          new TextRun({
            text: ' : ' + values,
            size: fonts.sizes.text,
            font: fonts.main,
          }),
        ],
      }),

    bullet: (text: string, level = 0) => {
      const indent = 400 + level * 400;
      const marker = level === 0 ? '\u2022 ' : level === 1 ? '\u25CB ' : '\u25AA ';
      return new Paragraph({
        spacing: { before: spacing.bullet, after: spacing.bullet },
        indent: { left: indent, hanging: 200 },
        children: [
          new TextRun({
            text: marker + text,
            size: fonts.sizes.text,
            font: fonts.main,
          }),
        ],
      });
    },

    text: (content: string, options: { bold?: boolean; italic?: boolean } = {}) =>
      new Paragraph({
        spacing: { before: spacing.paragraph, after: spacing.paragraph },
        children: [
          new TextRun({
            text: content,
            size: fonts.sizes.text,
            font: fonts.main,
            bold: options.bold || false,
            italics: options.italic || false,
          }),
        ],
      }),

    expHeader: (client: string, periode: string, titre: string) => {
      const style = config.experienceStyle;
      const titleBold = style?.titleBold ?? false;
      const titleItalic = style?.titleItalic ?? true;
      const titleBorderBottom = style?.titleBorderBottom ?? true;
      const titleLineSpacing = style?.titleLineSpacing;

      return [
        new Paragraph({
          spacing: { before: spacing.subsection, after: 60 },
          children: [
            new TextRun({
              text: client,
              bold: true,
              size: fonts.sizes.text,
              font: fonts.main,
              color: colors.text,
            }),
            new TextRun({
              text: ' | ',
              size: fonts.sizes.text,
              font: fonts.main,
              color: colors.period,
            }),
            new TextRun({
              text: periode,
              size: fonts.sizes.text,
              font: fonts.main,
              color: colors.period,
            }),
          ],
        }),
        new Paragraph({
          spacing: {
            after: spacing.paragraph,
            ...(titleLineSpacing ? { line: titleLineSpacing } : {}),
          },
          ...(titleBorderBottom
            ? {
                border: {
                  bottom: {
                    style: BorderStyle.SINGLE,
                    size: 18,
                    space: 5,
                    color: colors.border,
                  },
                },
              }
            : {}),
          children: [
            new TextRun({
              text: titre,
              bold: titleBold,
              italics: titleItalic,
              size: fonts.sizes.text,
              font: fonts.main,
              color: colors.text,
            }),
          ],
        }),
      ];
    },

    diplome: (date: string, titre: string, etablissement: string) => {
      const sep = config.diplomeStyle?.separator ?? ' - ';
      const compact = config.diplomeStyle?.compact ?? false;
      return [
        new Paragraph({
          spacing: { before: compact ? 40 : spacing.paragraph, after: compact ? 0 : 40 },
          children: [
            new TextRun({
              text: date + sep + titre,
              bold: true,
              size: fonts.sizes.text,
              font: fonts.main,
            }),
          ],
        }),
        new Paragraph({
          spacing: { after: compact ? 40 : spacing.paragraph },
          children: [
            new TextRun({
              text: etablissement,
              size: fonts.sizes.text,
              font: fonts.main,
            }),
          ],
        }),
      ];
    },

    header: (cvHeader: { titre: string; experience: string }): (Paragraph | Table)[] => {
      const headerLayout = config.header?.layout || 'centered';
      const titleBoldItalic = config.header?.titleBoldItalic ?? false;

      if (headerLayout === 'table') {
        // Table layout (Craftmania): title left, logo right
        const noBorder = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
        const cellBorders = {
          top: noBorder,
          bottom: noBorder,
          left: noBorder,
          right: noBorder,
        };

        const leftCellChildren = [
          new Paragraph({
            spacing: { after: 60 },
            children: [
              new TextRun({
                text: cvHeader.titre,
                bold: true,
                italics: titleBoldItalic,
                size: fonts.sizes.title,
                font: fonts.main,
              }),
            ],
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: cvHeader.experience,
                italics: true,
                size: fonts.sizes.subtitle,
                font: fonts.main,
              }),
            ],
          }),
        ];

        const rightCellChildren: Paragraph[] = [];
        if (logoData) {
          rightCellChildren.push(
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [
                new ImageRun({
                  type: 'png',
                  data: logoData,
                  transformation: {
                    width: config.logo.width,
                    height: config.logo.height,
                  },
                }),
              ],
            })
          );
        } else {
          rightCellChildren.push(new Paragraph({}));
        }

        return [
          new Table({
            width: { size: 100, type: WidthType.PERCENTAGE },
            borders: {
              top: noBorder,
              bottom: noBorder,
              left: noBorder,
              right: noBorder,
              insideHorizontal: noBorder,
              insideVertical: noBorder,
            },
            rows: [
              new TableRow({
                children: [
                  new TableCell({
                    width: { size: 60, type: WidthType.PERCENTAGE },
                    verticalAlign: VerticalAlign.CENTER,
                    borders: cellBorders,
                    children: leftCellChildren,
                  }),
                  new TableCell({
                    width: { size: 40, type: WidthType.PERCENTAGE },
                    verticalAlign: VerticalAlign.CENTER,
                    borders: cellBorders,
                    children: rightCellChildren,
                  }),
                ],
              }),
            ],
          }),
          new Paragraph({ spacing: { after: spacing.section } }),
        ];
      }

      // Centered layout (Gemini): floating logo left, centered title
      const elements: (Paragraph | Table)[] = [];
      const titleColor = colors.sectionBg || colors.primary;

      if (logoData) {
        elements.push(
          new Paragraph({
            children: [
              new ImageRun({
                type: 'png',
                data: logoData,
                transformation: {
                  width: config.logo.width,
                  height: config.logo.height,
                },
                floating: {
                  horizontalPosition: { relative: 'margin' as const, align: 'left' },
                  verticalPosition: { relative: 'margin' as const, align: 'top' },
                  wrap: {
                    type: TextWrappingType.SQUARE,
                    side: TextWrappingSide.BOTH_SIDES,
                  },
                },
              }),
            ],
          })
        );
      }

      elements.push(
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [
            new TextRun({
              text: cvHeader.titre,
              bold: true,
              size: fonts.sizes.title,
              color: titleColor,
              font: fonts.main,
            }),
          ],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: spacing.section },
          children: [
            new TextRun({
              text: cvHeader.experience,
              italics: true,
              size: fonts.sizes.subtitle,
              color: titleColor,
              font: fonts.main,
            }),
          ],
        })
      );

      return elements;
    },

    footer: () => {
      const footerColor = colors.sectionBg || colors.primary;
      return new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { after: 40 },
            children: [
              new TextRun({
                text: config.footer.line1,
                bold: true,
                size: fonts.sizes.footer,
                color: footerColor,
                font: fonts.main,
              }),
            ],
          }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: config.footer.line2,
                size: fonts.sizes.footer,
                color: footerColor,
                font: fonts.main,
              }),
            ],
          }),
        ],
      });
    },

    pageBreak: () => new Paragraph({ children: [new PageBreak()] }),
  };
}

function renderContent(
  content: SectionContent[],
  helpers: ReturnType<typeof createHelpers>,
  isExperienceSection = false
): Paragraph[] {
  const elements: Paragraph[] = [];

  content.forEach((item, index) => {
    switch (item.type) {
      case 'subsection':
        // Add spacing between consecutive subsections
        if (index > 0 && content[index - 1].type === 'subsection') {
          elements.push(
            new Paragraph({ spacing: { before: 120, after: 120 } })
          );
        }
        elements.push(helpers.subSectionTitle(item.title));
        elements.push(...renderContent(item.content, helpers));
        break;
      case 'competence':
        elements.push(helpers.competenceLine(item.category, item.values));
        break;
      case 'bullet':
        elements.push(helpers.bullet(item.text, item.level || 0));
        break;
      case 'text':
        elements.push(helpers.text(item.text, { bold: item.bold }));
        break;
      case 'diplome':
        elements.push(
          ...helpers.diplome(item.date, item.titre, item.etablissement)
        );
        break;
      case 'experience':
        elements.push(
          ...helpers.expHeader(item.client, item.periode, item.titre)
        );
        if (item.description) {
          elements.push(helpers.text(item.description));
        }
        elements.push(...renderContent(item.content, helpers));
        if (item.environnement) {
          elements.push(
            helpers.competenceLine('Environnement', item.environnement)
          );
        }
        if (isExperienceSection && index < content.length - 1) {
          elements.push(helpers.pageBreak());
        }
        break;
    }
  });

  return elements;
}

function renderSections(
  sections: CVData['sections'],
  helpers: ReturnType<typeof createHelpers>,
  config: TemplateConfig
): Paragraph[] {
  const elements: Paragraph[] = [];
  const skipSections = config.skipSections ?? [];

  sections.forEach((section) => {
    if (skipSections.includes(section.id)) return;

    elements.push(helpers.sectionTitle(section.title));
    const isExperienceSection = section.id === 'experiences';
    elements.push(
      ...renderContent(section.content, helpers, isExperienceSection)
    );
    if (section.id === 'certifications') {
      elements.push(helpers.pageBreak());
    }
  });

  return elements;
}

/**
 * Load logo from public directory. Returns null if not found.
 */
async function loadLogo(logoPath: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(logoPath);
    if (!response.ok) return null;
    return await response.arrayBuffer();
  } catch {
    return null;
  }
}

/**
 * Generate a DOCX blob from CV data and template config.
 * Designed for browser usage - returns a Blob for download.
 */
export async function generateCV(
  cvData: CVData,
  config: TemplateConfig,
  logoPath?: string
): Promise<Blob> {
  const logoData = logoPath ? await loadLogo(logoPath) : null;
  const helpers = createHelpers(config, logoData);

  const hasFooter = config.footer.enabled !== false;

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: {
            font: config.fonts.main,
            size: config.fonts.sizes.text,
          },
        },
      },
    },
    sections: [
      {
        properties: {
          page: { margin: config.margins },
        },
        ...(hasFooter ? { footers: { default: helpers.footer() } } : {}),
        children: [
          ...helpers.header(cvData.header),
          ...renderSections(cvData.sections, helpers, config),
        ],
      },
    ],
  });

  return Packer.toBlob(doc);
}
