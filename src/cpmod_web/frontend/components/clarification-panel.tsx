'use client';

import { useState } from 'react';

import { api } from '../lib/api';
import type { WorkflowRun } from '../lib/types';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

export function ClarificationPanel({ run }: { run: WorkflowRun }) {
  const [answers, setAnswers] = useState<string[]>(run.clarification_questions.map(() => ''));
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-4 rounded-xl border border-amber-300 bg-amber-50 p-5">
      <h2 className="text-lg font-semibold">Clarification needed</h2>
      {run.clarification_questions.map((question, idx) => (
        <div key={idx} className="grid gap-2">
          <label className="text-sm font-medium">{question}</label>
          <Textarea
            value={answers[idx]}
            onChange={(event) => {
              const next = [...answers];
              next[idx] = event.target.value;
              setAnswers(next);
            }}
          />
        </div>
      ))}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <Button
        type="button"
        onClick={async () => {
          try {
            await api.submitClarification(run.id, answers);
            window.location.reload();
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to submit clarification.');
          }
        }}
      >
        Submit clarification
      </Button>
    </div>
  );
}
