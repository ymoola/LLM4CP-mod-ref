'use client';

import Link from 'next/link';

import { BrandLockup } from '../components/brand-lockup';
import { useAuth } from '../components/auth-provider';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';

const workflowStages = ['Parse', 'Clarify', 'Plan', 'Modify', 'Execute', 'Validate'];

export default function HomePage() {
  const { loading, isAuthed } = useAuth();

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
        <Card className="overflow-hidden rounded-[2rem] border-[var(--line-strong)] bg-[linear-gradient(145deg,rgba(255,255,255,0.95),rgba(247,243,236,0.86))] p-6 sm:p-8">
          <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <p className="eyebrow">Constraint programming modification</p>
                <h1 className="max-w-4xl text-4xl leading-[0.96] sm:text-5xl lg:text-6xl">
                  Upload a CPMpy model, describe the change in plain language, and ship a reviewable modified model.
                </h1>
              </div>
              <Badge tone="success">Audit-first</Badge>
            </div>

            <p className="max-w-3xl text-base text-[var(--muted)] sm:text-lg">
              ConstraintMod modifies constraint programming models in an audit-friendly way: structured model intake, clarification when needed, stage-separated code generation, and artifact-backed validation instead of opaque one-shot output.
            </p>

            <div className="grid gap-4 rounded-[1.6rem] border border-[var(--line)] bg-[rgba(255,255,255,0.68)] p-4 sm:grid-cols-[1.25fr_0.9fr] sm:p-5">
              <BrandLockup size="hero" priority />
              <div className="grid gap-3">
                <div>
                  <p className="eyebrow">Signature flow</p>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    The product differentiator is the visible workflow: every stage is inspectable, pausable, and reviewable by the user.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {workflowStages.map((stage) => (
                    <Badge key={stage} tone="default">
                      {stage}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {loading ? (
              <p className="text-sm text-[var(--muted)]">Checking session…</p>
            ) : isAuthed ? (
              <div className="flex flex-wrap gap-3">
                <Link href="/dashboard" className="no-underline">
                  <Button type="button">Go to dashboard</Button>
                </Link>
                <Link href="/projects" className="rounded-full border border-[var(--line)] px-4 py-2 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80">
                  Browse projects
                </Link>
              </div>
            ) : (
              <div className="flex flex-wrap gap-3">
                <Link href="/signup" className="no-underline">
                  <Button type="button">Create account</Button>
                </Link>
                <Link href="/login" className="rounded-full border border-[var(--line)] px-4 py-2 text-sm font-semibold uppercase tracking-[0.14em] no-underline transition hover:border-[var(--line-strong)] hover:bg-white/80">
                  Log in
                </Link>
              </div>
            )}
          </div>
        </Card>

        <div className="grid gap-6">
          <Card className="rounded-[2rem] bg-[linear-gradient(180deg,rgba(15,23,20,0.98),rgba(18,36,29,0.95))] p-6 text-white">
            <p className="eyebrow text-emerald-300">How the modifier works</p>
            <div className="mt-5 grid gap-4">
              <div>
                <p className="text-lg font-semibold">Stage-separated workflow</p>
                <p className="mt-1 text-sm text-slate-300">
                  Parsing, clarification, planning, modification, execution, and validation remain explicit so every run can be inspected step by step.
                </p>
              </div>
              <div>
                <p className="text-lg font-semibold">Human clarification when needed</p>
                <p className="mt-1 text-sm text-slate-300">
                  If a change request is ambiguous, the workflow can pause and ask for clarification rather than silently making assumptions.
                </p>
              </div>
              <div>
                <p className="text-lg font-semibold">Artifacts instead of hidden reasoning</p>
                <p className="mt-1 text-sm text-slate-300">
                  Each run produces concrete outputs such as generated code, execution logs, diffs, and review states so the modification process stays auditable.
                </p>
              </div>
            </div>
          </Card>

          <Card className="rounded-[2rem] p-6">
            <p className="eyebrow">Core outcomes</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-3xl font-semibold">1</p>
                <p className="mt-1 text-sm text-[var(--muted)]">validated base model package</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">1</p>
                <p className="mt-1 text-sm text-[var(--muted)]">effective runtime input source per run</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">3</p>
                <p className="mt-1 text-sm text-[var(--muted)]">terminal states: completed, needs review, failed</p>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
