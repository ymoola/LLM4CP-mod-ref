import { ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-[1rem] border border-[rgba(7,53,40,0.18)] bg-[var(--accent-strong)] px-4 py-2.5 text-sm font-semibold uppercase tracking-[0.12em] text-white shadow-[0_14px_30px_rgba(10,105,78,0.18)] transition hover:-translate-y-[1px] hover:bg-[var(--accent)] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
      {...props}
    />
  );
}
