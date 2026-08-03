"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";

type EvalRunAction = (formData: FormData) => Promise<void> | void;
type ButtonVariant = "primary" | "outline";

type HiddenField = {
  name: string;
  value: string;
};

type EvalRunControlsContextValue = {
  activeRunKey: string | null;
  setActiveRunKey: (runKey: string | null) => void;
};

type EvalRunFormProps = {
  action: EvalRunAction;
  ariaLabel?: string;
  defaultLabel: string;
  disabledReason?: string;
  formClassName?: string;
  hiddenFields?: HiddenField[];
  pendingLabel: string;
  runKey: string;
  variant: ButtonVariant;
};

const EvalRunControlsContext = createContext<EvalRunControlsContextValue | null>(null);

export function EvalRunControlsProvider({ children }: { children: ReactNode }) {
  const [activeRunKey, setActiveRunKey] = useState<string | null>(null);
  const value = useMemo(() => ({ activeRunKey, setActiveRunKey }), [activeRunKey]);

  return (
    <EvalRunControlsContext.Provider value={value}>{children}</EvalRunControlsContext.Provider>
  );
}

export function EvalRunForm({
  action,
  ariaLabel,
  defaultLabel,
  disabledReason,
  formClassName,
  hiddenFields = [],
  pendingLabel,
  runKey,
  variant,
}: EvalRunFormProps) {
  const { setActiveRunKey } = useEvalRunControls();

  async function submitEvalRun(formData: FormData) {
    setActiveRunKey(runKey);
    try {
      await action(formData);
    } finally {
      setActiveRunKey(null);
    }
  }

  return (
    <form action={submitEvalRun} className={formClassName} onSubmit={() => setActiveRunKey(runKey)}>
      {hiddenFields.map((field) => (
        <input key={field.name} name={field.name} type="hidden" value={field.value} />
      ))}
      <EvalRunSubmitButton
        ariaLabel={ariaLabel}
        defaultLabel={defaultLabel}
        disabledReason={disabledReason}
        pendingLabel={pendingLabel}
        runKey={runKey}
        variant={variant}
      />
    </form>
  );
}

function EvalRunSubmitButton({
  ariaLabel,
  defaultLabel,
  disabledReason,
  pendingLabel,
  runKey,
  variant,
}: Omit<EvalRunFormProps, "action" | "formClassName" | "hiddenFields">) {
  const { pending } = useFormStatus();
  const { activeRunKey } = useEvalRunControls();
  const isLocked = activeRunKey !== null;
  const isActiveRun = activeRunKey === runKey;
  const showPending = isActiveRun && (pending || isLocked);

  return (
    <button
      aria-label={showPending ? undefined : ariaLabel}
      className={buttonClass(variant)}
      disabled={Boolean(disabledReason) || isLocked || pending}
      title={disabledReason}
      type="submit"
    >
      {showPending ? (
        <span
          aria-hidden="true"
          className="h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent"
        />
      ) : null}
      {showPending ? pendingLabel : defaultLabel}
    </button>
  );
}

function useEvalRunControls() {
  const context = useContext(EvalRunControlsContext);
  if (!context) {
    throw new Error("EvalRunForm must be rendered inside EvalRunControlsProvider");
  }
  return context;
}

function buttonClass(variant: ButtonVariant) {
  if (variant === "primary") {
    return "inline-flex items-center gap-2 rounded-md bg-meter-blue px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400 disabled:text-white";
  }

  return "inline-flex items-center gap-2 rounded-md border border-meter-line px-3 py-2 text-xs font-semibold text-meter-blue disabled:cursor-not-allowed disabled:text-slate-400";
}
