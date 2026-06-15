import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';
import { cn } from '../../lib/cn';

const base =
  'w-full rounded-lg border border-line bg-elevated px-3 py-2 text-sm text-ink placeholder:text-muted/60 ' +
  'outline-none transition-colors focus:border-brand/60 focus:ring-2 focus:ring-brand/20 ' +
  'disabled:cursor-not-allowed disabled:opacity-60';

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cn(base, 'h-10', className)} {...rest} />;
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return <textarea ref={ref} className={cn(base, 'min-h-28 resize-y font-mono leading-relaxed', className)} {...rest} />;
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <select ref={ref} className={cn(base, 'h-10 cursor-pointer pr-8', className)} {...rest}>
        {children}
      </select>
    );
  },
);

interface FieldProps {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  htmlFor?: string;
  className?: string;
  children: ReactNode;
}

export function Field({ label, hint, error, htmlFor, className, children }: FieldProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label && (
        <label htmlFor={htmlFor} className="text-xs font-medium text-muted">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-bad">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted/80">{hint}</p>
      ) : null}
    </div>
  );
}
