import Image from 'next/image';
import Link from 'next/link';
import clsx from 'clsx';

type BrandLockupProps = {
  href?: string;
  priority?: boolean;
  size?: 'compact' | 'hero';
  caption?: string;
  className?: string;
};

export function BrandLockup({
  href,
  priority = false,
  size = 'compact',
  caption,
  className,
}: BrandLockupProps) {
  const showCaption = Boolean(caption) && size !== 'compact';
  const content = (
    <div className={clsx('flex items-center gap-4', className)}>
      <div className={clsx('brand-stage', size === 'hero' ? 'px-1 py-1' : 'px-0 py-0')}>
        <Image
          src="/cpmod-logo.png"
          alt="ConstraintMod"
          width={size === 'hero' ? 720 : 420}
          height={size === 'hero' ? 202 : 118}
          priority={priority}
          className={clsx(
            'w-auto object-contain object-left mix-blend-multiply',
            size === 'hero' ? 'h-16 sm:h-20 md:h-24' : 'h-10 sm:h-11',
          )}
        />
      </div>
      {showCaption ? (
        <div className="hidden min-w-0 sm:block">
          <p className="eyebrow">ConstraintMod</p>
          <p className="text-sm text-[var(--muted)]">{caption}</p>
        </div>
      ) : null}
    </div>
  );

  if (!href) {
    return content;
  }

  return (
    <Link href={href} className="no-underline">
      {content}
    </Link>
  );
}
