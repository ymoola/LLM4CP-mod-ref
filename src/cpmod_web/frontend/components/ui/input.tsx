import { InputHTMLAttributes } from 'react';
import clsx from 'clsx';

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={clsx(
        'w-full rounded-[1rem] border border-[var(--line)] bg-[rgba(255,255,255,0.84)] px-4 py-3 text-sm text-[var(--ink)] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition placeholder:text-[color:var(--muted)] focus:border-[var(--accent)] focus:bg-white',
        className,
      )}
      {...props}
    />
  );
}
