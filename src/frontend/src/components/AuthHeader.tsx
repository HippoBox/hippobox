export function AuthHeader() {
    return (
        <div className="flex flex-col items-center gap-3 text-center">
            <div className="auth-header-icon flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200/80 shadow-sm dark:border-slate-700/60">
                <img src="/hippobox.svg" alt="HippoBox" className="h-full w-full object-contain" />
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.35em] text-muted">
                HippoBox
            </div>
        </div>
    );
}
