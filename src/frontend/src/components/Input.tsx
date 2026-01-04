import type { InputHTMLAttributes, ReactNode } from 'react';

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
    label?: string;
    id: string;
    hint?: string;
    leadingIcon?: ReactNode;
};

export function Input({
    label,
    id,
    hint,
    leadingIcon,
    className,
    placeholder,
    ...props
}: InputProps) {
    return (
        <div className="space-y-2">
            {label ? (
                <label
                    htmlFor={id}
                    className="text-xs font-semibold uppercase tracking-[0.25em] text-muted"
                >
                    {label}
                </label>
            ) : null}
            <div className="relative">
                {leadingIcon ? (
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">
                        {leadingIcon}
                    </span>
                ) : null}
                <input
                    id={id}
                    className={['input-field', leadingIcon ? 'pl-10' : '', className ?? '']
                        .filter(Boolean)
                        .join(' ')}
                    placeholder={placeholder ?? ''}
                    {...props}
                />
            </div>
            {hint ? <p className="text-xs text-muted">{hint}</p> : null}
        </div>
    );
}
