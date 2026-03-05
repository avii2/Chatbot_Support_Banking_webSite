export default function Support() {
  return (
    <section className="animate-fadeUp rounded-3xl border border-slate-200 bg-white p-8 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
      <h2 className="font-display text-3xl text-brand-navy dark:text-blue-300">Support</h2>
      <p className="mt-3 max-w-2xl text-slate-700 dark:text-slate-300">
        Reach support by phone or email, then escalate to grievance and nodal teams if unresolved within
        defined timelines.
      </p>
      <div className="mt-6 space-y-4">
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="font-display text-lg text-slate-800 dark:text-slate-100">Level 1: Standard Support</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">+91-9783039318 | support@louie.example</p>
        </article>
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="font-display text-lg text-slate-800 dark:text-slate-100">Level 2: Grievance Officer</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">sunnychoudhary@louie.example (after 7 days)</p>
        </article>
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="font-display text-lg text-slate-800 dark:text-slate-100">Level 3: Nodal Officer</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">nodal.officer@louie.example</p>
        </article>
      </div>
    </section>
  )
}
