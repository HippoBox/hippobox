import { useEffect, useState } from 'react';

import { marked } from 'marked';
import { markedHighlight } from 'marked-highlight';
import markedKatex from 'marked-katex-extension';
import hljs from 'highlight.js';
import DOMPurify from 'dompurify';

import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import { createSlugger, preprocessMarkdown } from '../utils/markdown';

marked.use(
    markedHighlight({
        langPrefix: 'hljs language-',
        highlight(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
    }),
);

marked.use(
    markedKatex({
        throwOnError: false,
        output: 'html',
        nonStandard: true,
    }),
);

const ALLOWED_IFRAME_HOSTS = new Set([
    'youtube.com',
    'www.youtube.com',
    'player.vimeo.com',
    'vimeo.com',
    'www.figma.com',
    'figma.com',
]);

let domPurifyConfigured = false;

const configureDomPurify = () => {
    if (domPurifyConfigured) return;
    domPurifyConfigured = true;

    DOMPurify.addHook('uponSanitizeElement', (node, data) => {
        if (data.tagName !== 'iframe') return;
        const element = node as Element;
        const src = element.getAttribute('src') ?? '';
        element.setAttribute(
            'sandbox',
            'allow-scripts allow-same-origin allow-presentation allow-popups',
        );
        element.setAttribute('referrerpolicy', 'no-referrer');
        try {
            const url = new URL(src);
            if (!ALLOWED_IFRAME_HOSTS.has(url.hostname)) {
                element.remove();
            }
        } catch {
            element.remove();
        }
    });

    DOMPurify.addHook('uponSanitizeAttribute', (node, data) => {
        if (data.attrName !== 'style') return;
        const element = node as Element;
        const isKatex = element.classList.contains('katex') || !!element.closest('.katex');
        if (!isKatex) {
            element.removeAttribute('style');
        }
    });
};

const sanitizeOptions = {
    ADD_TAGS: [
        'iframe',
        'span',
        'math',
        'annotation',
        'semantics',
        'mtext',
        'mn',
        'mo',
        'mi',
        'mspace',
        'mover',
        'munder',
        'munderover',
        'msup',
        'msub',
        'msubsup',
        'mfrac',
        'mroot',
        'msqrt',
        'mtable',
        'mtr',
        'mtd',
        'mlabeledtr',
        'mrow',
    ],
    ADD_ATTR: [
        'allow',
        'allowfullscreen',
        'frameborder',
        'scrolling',
        'class',
        'id',
        'style',
        'xmlns',
        'display',
        'role',
        'aria-hidden',
    ],
};

const createMarkdownRenderer = () => {
    const slugger = createSlugger();
    const renderer = new marked.Renderer();

    renderer.heading = (text, level, raw) => {
        const slug = slugger(raw ?? text);
        const tag = `h${level}`;
        return `<${tag} id="${slug}" class="markdown-heading">${text}</${tag}>`;
    };

    return renderer;
};
type MarkdownContentProps = {
    content: string;
};

export function MarkdownContent({ content }: MarkdownContentProps) {
    const [html, setHtml] = useState('');

    useEffect(() => {
        let cancelled = false;
        const rawMarkdown = content ?? '';
        const processed = preprocessMarkdown(rawMarkdown);

        const parseMarkdown = async () => {
            configureDomPurify();
            const renderer = createMarkdownRenderer();
            const parsed = await marked.parse(processed, {
                breaks: true,
                gfm: true,
                renderer,
            });
            const sanitized = DOMPurify.sanitize(parsed, sanitizeOptions);
            if (!cancelled) {
                setHtml(sanitized);
            }
        };

        parseMarkdown();
        return () => {
            cancelled = true;
        };
    }, [content]);

    return <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />;
}
