const highlights = [
  {
    title: 'Simple Everyday Accounts',
    text: 'Transparent minimum balance and fee policies with instant statement access.'
  },
  {
    title: 'Loan Decisions with Clarity',
    text: 'Clear eligibility guidance for personal and home loans with predictable timelines.'
  },
  {
    title: 'Support That Escalates Properly',
    text: 'Ticket-based complaint tracking with defined grievance and nodal escalation.'
  }
]

const quickActions = [
  { label: 'Open Savings Account', value: 'Start in under 7 minutes' },
  { label: 'Card Fee Checker', value: 'See joining and annual fee rules' },
  { label: 'KYC Checklist', value: 'Verify accepted ID and address proof' },
  { label: 'Dispute Process', value: 'Raise unauthorized transaction cases' }
]

export default function Home() {
  return (
    <section className="w-full space-y-3 animate-fadeUp">
      <article className="overflow-hidden rounded-3xl bg-gradient-to-br from-[#0b2d84] via-[#123a9a] to-[#1c58c9] px-6 py-5 text-white shadow-soft md:px-7 md:py-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-100">Welcome to Visioapps Bank</p>
        <h1 className="mt-2 max-w-2xl font-display text-4xl leading-tight md:text-[2.6rem]">
          Banking made simple, secure, and human.
        </h1>
        <p className="mt-2.5 max-w-2xl text-sm text-blue-100 md:text-base">
          Manage your money confidently with a clean digital experience built on Visioapps Bank rails for
          secure onboarding, payments, and support.
        </p>

        <div className="mt-3.5 flex flex-wrap gap-3">
          <button className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-brand-navy transition hover:bg-slate-100">
            Get Started
          </button>
          <button className="rounded-lg border border-white/40 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20">
            Explore visioapps.bank
          </button>
        </div>
      </article>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {highlights.map((item) => (
          <article key={item.title} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
            <p className="font-display text-xl text-brand-navy dark:text-blue-300">{item.title}</p>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.text}</p>
          </article>
        ))}
      </div>

      <article className="rounded-3xl border border-slate-200 bg-white p-4 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
        <p className="font-display text-2xl text-brand-navy dark:text-blue-300">Quick Actions</p>
        <div className="mt-2.5 grid gap-3 sm:grid-cols-2">
          {quickActions.map((item) => (
            <div key={item.label} className="rounded-xl bg-slate-50 p-3 transition-colors dark:bg-slate-800">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{item.label}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{item.value}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}
