import { marked, type Tokens } from 'marked';

export type MarkdownHeadingLevel = 1 | 2 | 3;

export type MarkdownHeading = {
    id: string;
    text: string;
    level: MarkdownHeadingLevel;
};

const slugifyHeading = (value: string) => {
    const normalized = value
        .trim()
        .toLowerCase()
        .replace(/<[^>]+>/g, '')
        .replace(/[^\p{L}\p{N}\s-]/gu, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    return normalized || 'section';
};

export const createSlugger = () => {
    const counts = new Map<string, number>();
    return (value: string) => {
        const base = slugifyHeading(value);
        const current = counts.get(base) ?? 0;
        counts.set(base, current + 1);
        return current === 0 ? base : `${base}-${current}`;
    };
};

export const preprocessMarkdown = (value: string) => {
    let processed = value;
    processed = processed.replace(/\*\*\s*`(.+?)`\s*\*\*/g, '**$1**');
    processed = processed.replace(
        /\*\*([^*]*?[\(??[][^*]*?[\)??]][^*]*?)\*\*/g,
        '<strong>$1</strong>',
    );
    processed = processed.replace(/`(\$[^`]+?\$)`/g, '$1');
    processed = processed.replace(/(\$[^$]+?\$)/g, (match) => match.replace(/_/g, '\\_'));
    return processed;
};

export const extractHeadings = (content: string): MarkdownHeading[] => {
    if (!content?.trim()) return [];
    const processed = preprocessMarkdown(content);
    const tokens = marked.lexer(processed, {
        breaks: true,
        gfm: true,
    });
    const slugger = createSlugger();
    const headings: MarkdownHeading[] = [];

    marked.walkTokens(tokens, (token) => {
        if (token.type !== 'heading') return;
        const heading = token as Tokens.Heading;
        const depth = heading.depth ?? 0;
        if (depth < 1 || depth > 3) return;
        const text = heading.text?.trim();
        if (!text) return;
        headings.push({
            id: slugger(text),
            text,
            level: depth as MarkdownHeadingLevel,
        });
    });

    return headings;
};
