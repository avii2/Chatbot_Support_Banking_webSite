export default function Fees() {
  return (
    <section className="animate-fadeUp rounded-3xl border border-slate-200 bg-white p-8 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
      <h2 className="font-display text-3xl text-brand-navy dark:text-blue-300">Fees</h2>
      <p className="mt-3 max-w-2xl text-slate-700 dark:text-slate-300">
        View common service fees. The assistant can answer detailed charge rules from the knowledge base.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Cash Advance</p>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">2.5% or INR 500 (higher applies)</p>
        </article>
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Card Replacement</p>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">INR 250 + taxes</p>
        </article>
        <article className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Statement Copy</p>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">INR 75 per extra physical statement</p>
        </article>
      </div>
    </section>
  )
}
