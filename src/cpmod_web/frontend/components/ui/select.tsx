import { SelectHTMLAttributes } from 'react';
import clsx from 'clsx';

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  wrapperClassName?: string;
};

export function Select({ className, wrapperClassName, children, ...props }: SelectProps) {
  return (
    <div className={clsx('relative', wrapperClassName)}>
      <select
        className={clsx(
          'w-full appearance-none rounded-[1rem] border border-[var(--line)] bg-[rgba(255,255,255,0.88)] px-4 py-3 pr-12 text-sm text-[var(--ink)] shadow-[inset_0_1px_0_rgba(255,255,255,0.72)] transition focus:border-[var(--accent)] focus:bg-white',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-[var(--muted)]"
      >
        <svg width="12" height="8" viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M1 1.25L6 6.25L11 1.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </div>
  );
}
