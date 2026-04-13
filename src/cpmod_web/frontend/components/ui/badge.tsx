import clsx from 'clsx';
import { PropsWithChildren } from 'react';

export function Badge({ children, tone = 'default' }: PropsWithChildren<{ tone?: 'default' | 'success' | 'warning' | 'danger' }>) {
  return <span className={clsx('inline-flex rounded-full px-2.5 py-1 text-xs font-medium', {
    'bg-slate-200 text-slate-900': tone === 'default',
    'bg-emerald-100 text-emerald-900': tone === 'success',
    'bg-amber-100 text-amber-900': tone === 'warning',
    'bg-rose-100 text-rose-900': tone === 'danger',
  })}>{children}</span>;
}
