import { loginAction, switchIdentityAction } from "@/lib/auth-actions";
import { formatDemoRole, safeReturnTo, type DemoRole } from "@/lib/demo-auth";
import { getDemoIdentities } from "@/lib/meterdesk-api";

type LoginPageProps = {
  searchParams?: Promise<{
    mode?: string;
    reason?: string;
    returnTo?: string;
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = searchParams ? await searchParams : {};
  const isSwitch = params.mode === "switch";
  const returnTo = safeReturnTo(params.returnTo);

  try {
    const identities = await getDemoIdentities();
    const action = isSwitch ? switchIdentityAction : loginAction;

    return (
      <main className="min-h-screen bg-[#f7f8fb] px-5 py-10 text-meter-ink">
        <section className="mx-auto w-full max-w-4xl">
          <div className="rounded-md border border-meter-line bg-white p-6 md:p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-meter-blue">
              MeterDesk
            </p>
            <h1 className="mt-3 text-3xl font-semibold">
              {isSwitch ? "Switch demo identity" : "Choose a demo identity"}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              Pick one fixed principal to exercise the server-enforced role boundaries. All tabs in
              this browser share the selected identity for up to eight hours.
            </p>
            {params.reason === "session-expired" ? (
              <p
                className="mt-4 rounded-md border border-meter-amber bg-[#fffaf0] p-3 text-sm text-slate-700"
                role="status"
              >
                Your demo session expired. Choose an identity to continue.
              </p>
            ) : null}

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {identities.map((identity) => (
                <article
                  className="flex flex-col rounded-md border border-meter-line bg-[#fbfcfe] p-4"
                  key={identity.subject}
                >
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    {formatDemoRole(identity.role)}
                  </p>
                  <h2 className="mt-2 text-lg font-semibold">{identity.display_name}</h2>
                  <p className="mt-1 text-xs text-slate-500">{identity.subject}</p>
                  <p className="mt-3 flex-1 text-sm leading-6 text-slate-600">
                    {roleDescription(identity.role)}
                  </p>
                  <form action={action} className="mt-4">
                    <input name="returnTo" type="hidden" value={returnTo} />
                    <input name="subject" type="hidden" value={identity.subject} />
                    <button
                      className="h-10 w-full rounded-md bg-meter-blue px-3 text-sm font-semibold text-white"
                      type="submit"
                    >
                      Continue as {identity.display_name}
                    </button>
                  </form>
                </article>
              ))}
            </div>

            <p className="mt-6 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Local demo authentication only
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              No passwords, user records, external identity provider, refresh token, or server-side
              session store are used.
            </p>
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return (
      <main className="min-h-screen bg-[#f7f8fb] px-5 py-10 text-meter-ink">
        <section className="mx-auto w-full max-w-2xl rounded-md border border-meter-amber bg-white p-6">
          <h1 className="text-2xl font-semibold">Demo identities unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {error instanceof Error ? error.message : "FastAPI authentication is unavailable."}
          </p>
        </section>
      </main>
    );
  }
}

function roleDescription(role: DemoRole): string {
  if (role === "support_operator") {
    return "Read support resources and start governed Agent investigations.";
  }
  if (role === "approver") {
    return "Read support resources and approve or reject financial actions.";
  }
  return "Run Agent investigations, decide approvals, and execute offline Evals.";
}
