export default function Cards() {
  return (
    <section className="animate-fadeUp rounded-3xl border border-slate-200 bg-white p-8 shadow-soft transition-colors dark:border-slate-700 dark:bg-slate-900">
      <h2 className="font-display text-3xl text-brand-navy dark:text-blue-300">Cards</h2>
      <p className="mt-3 max-w-2xl text-slate-700 dark:text-slate-300">
        Choose between Platinum and Signature credit cards with annual fee waivers linked to yearly spend.
      </p>
      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 transition-colors dark:border-slate-700">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
          <thead className="bg-slate-100 text-left text-slate-700 dark:bg-slate-800 dark:text-slate-200">
            <tr>
              <th className="px-4 py-3">Card Type</th>
              <th className="px-4 py-3">Joining Fee</th>
              <th className="px-4 py-3">Annual Fee</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-slate-800 dark:divide-slate-800 dark:bg-slate-900 dark:text-slate-200">
            <tr>
              <td className="px-4 py-3">Platinum</td>
              <td className="px-4 py-3">INR 999 + taxes</td>
              <td className="px-4 py-3">INR 999 + taxes</td>
            </tr>
            <tr>
              <td className="px-4 py-3">Signature</td>
              <td className="px-4 py-3">INR 2,999 + taxes</td>
              <td className="px-4 py-3">INR 2,999 + taxes</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}
