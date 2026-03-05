export default function Accounts() {
  return (
    <section className="animate-fadeUp rounded-3xl border border-slate-200 bg-white p-8 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
      <h2 className="font-display text-3xl text-brand-navy dark:text-blue-300">Accounts</h2>
      <p className="mt-3 max-w-2xl text-slate-700 dark:text-slate-300">
        Open savings accounts with eKYC, receive free e-statements, and manage account services from branch,
        app, or video verification. Minimum balance rules vary by branch category.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-4 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Urban</p>
          <p className="mt-1 text-2xl font-semibold text-brand-navy dark:text-blue-300">INR 5,000</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Semi-Urban</p>
          <p className="mt-1 text-2xl font-semibold text-brand-navy dark:text-blue-300">INR 2,500</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4 transition-colors dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Rural</p>
          <p className="mt-1 text-2xl font-semibold text-brand-navy dark:text-blue-300">INR 1,000</p>
        </div>
      </div>
    </section>
  )
}
