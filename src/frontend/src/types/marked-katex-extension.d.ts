declare module 'marked-katex-extension' {
    import type { MarkedExtension } from 'marked';

    const markedKatex: (options?: Record<string, unknown>) => MarkedExtension;
    export default markedKatex;
}
