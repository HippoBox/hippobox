type AuthHeaderProps = {
    size?: 'xs' | 'sm' | 'md';
    layout?: 'stacked' | 'inline';
    showLabel?: boolean;
    className?: string;
};

const sizeStyles = {
    xs: {
        icon: 'h-6 w-6 rounded-lg',
        label: 'text-[9px] tracking-[0.25em]',
    },
    sm: {
        icon: 'h-10 w-10 rounded-xl',
        label: 'text-[10px] tracking-[0.3em]',
    },
    md: {
        icon: 'h-16 w-16 rounded-2xl',
        label: 'text-[11px] tracking-[0.35em]',
    },
};

export function AuthHeader({
    size = 'md',
    layout = 'stacked',
    showLabel = true,
    className,
}: AuthHeaderProps) {
    const styles = sizeStyles[size];
    const wrapperClass =
        layout === 'inline'
            ? 'flex items-center gap-3 text-left'
            : 'flex flex-col items-center gap-3 text-center';

    return (
        <div className={`${wrapperClass} ${className ?? ''}`.trim()}>
            <div
                className={`auth-header-icon flex items-center justify-center border border-slate-200/80 shadow-sm dark:border-slate-700/60 ${styles.icon}`}
            >
                <img src="/hippobox.svg" alt="HippoBox" className="h-full w-full object-contain" />
            </div>
            {showLabel ? (
                <div className={`font-semibold uppercase text-muted ${styles.label}`}>HippoBox</div>
            ) : null}
        </div>
    );
}
