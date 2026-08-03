import Link from "next/link";

import { formatDemoRole, safeReturnTo } from "@/lib/demo-auth";
import { requireDemoSession } from "@/lib/session";

type ForbiddenPageProps = {
  searchParams?: Promise<{
    requestId?: string;
    returnTo?: string;
  }>;
};

export default async function ForbiddenPage({ searchParams }: ForbiddenPageProps) {
  const params = searchParams ? await searchParams : {};
  const returnTo = safeReturnTo(params.returnTo);
  const session = await requireDemoSession(returnTo);

  return (
    <main className="min-h-screen bg-[#f7f8fb] px-5 py-10 text-meter-ink">
      <section className="mx-auto w-full max-w-2xl rounded-md border border-meter-amber bg-white p-6 md:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-meter-amber">
          Server-enforced RBAC
        </p>
        <h1 className="mt-3 text-3xl font-semibold">Permission denied</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          FastAPI rejected this operation for the currently selected demo role. Your session remains
          active; no identity or audit data was changed.
        </p>

        <dl className="mt-5 rounded-md border border-meter-line bg-[#fbfcfe] p-4 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-slate-500">Current identity</dt>
            <dd className="font-semibold">{session.principal.display_name}</dd>
          </div>
          <div className="mt-2 flex items-center justify-between gap-4">
            <dt className="text-slate-500">Role</dt>
            <dd className="font-semibold">{formatDemoRole(session.principal.role)}</dd>
          </div>
          {params.requestId ? (
            <div className="mt-2 flex items-center justify-between gap-4">
              <dt className="text-slate-500">Request ID</dt>
              <dd className="font-mono text-xs font-semibold">{params.requestId}</dd>
            </div>
          ) : null}
        </dl>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            className="rounded-md bg-meter-blue px-4 py-2 text-sm font-semibold text-white"
            href={returnTo}
          >
            Return to MeterDesk
          </Link>
          <Link
            className="rounded-md border border-meter-line px-4 py-2 text-sm font-semibold text-meter-blue"
            href={`/login?mode=switch&returnTo=${encodeURIComponent(returnTo)}`}
          >
            Switch identity
          </Link>
        </div>
      </section>
    </main>
  );
}
