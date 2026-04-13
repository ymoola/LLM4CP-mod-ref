import clsx from 'clsx';
import { PropsWithChildren } from 'react';

export function Badge({ children, tone = 'default' }: PropsWithChildren<{ tone?: 'default' | 'success' | 'warning' | 'danger' }>) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em]',
        {
          'border-[var(--line)] bg-white/80 text-[var(--ink)]': tone === 'default',
          'border-[rgba(10,105,78,0.18)] bg-[var(--accent-soft)] text-[var(--accent-strong)]': tone === 'success',
          'border-[rgba(186,122,23,0.18)] bg-[var(--warning-soft)] text-[#8b5b0e]': tone === 'warning',
          'border-[rgba(191,56,68,0.18)] bg-[var(--danger-soft)] text-[#9b2836]': tone === 'danger',
        },
      )}
    >
      {children}
    </span>
  );
}
