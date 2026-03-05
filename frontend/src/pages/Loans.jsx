export default function Loans() {
  return (
    <section className="animate-fadeUp rounded-3xl border border-slate-200 bg-white p-8 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
      <h2 className="font-display text-3xl text-brand-navy dark:text-blue-300">Loans</h2>
      <p className="mt-3 max-w-2xl text-slate-700 dark:text-slate-300">
        Personal and home loan products are available with eligibility based on income stability, age,
        credit profile, and repayment obligations.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="font-display text-lg text-slate-800 dark:text-slate-100">Personal Loan</p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Typical range: INR 50,000 to INR 20,00,000</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">Tenure: 12 to 60 months</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-5 transition-colors dark:bg-slate-800">
          <p className="font-display text-lg text-slate-800 dark:text-slate-100">Home Loan</p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">FOIR guidance: typically below 50%</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">Floating-rate prepayment: no penalty for individuals</p>
        </div>
      </div>
    </section>
  )
}
