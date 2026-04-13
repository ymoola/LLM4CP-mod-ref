import { PropsWithChildren } from 'react';
import clsx from 'clsx';

export function Card({ children, className }: PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={clsx(
        'surface-cut rounded-[1.65rem] border border-[var(--line)] bg-[var(--panel)] p-5 shadow-[var(--shadow)] backdrop-blur-sm',
        className,
      )}
    >
      {children}
    </div>
  );
}
