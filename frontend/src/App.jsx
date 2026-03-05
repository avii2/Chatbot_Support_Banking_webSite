import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Accounts from './pages/Accounts'
import Loans from './pages/Loans'
import Cards from './pages/Cards'
import Fees from './pages/Fees'
import Support from './pages/Support'

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Accounts', to: '/accounts' },
  { label: 'Loans', to: '/loans' },
  { label: 'Cards', to: '/cards' },
  { label: 'Fees', to: '/fees' },
  { label: 'Support', to: '/support' }
]

const THEME_KEY = 'visioapps_theme'

export default function App() {
  const [theme, setTheme] = useState('light')

  useEffect(() => {
    const stored = window.localStorage.getItem(THEME_KEY)
    if (stored === 'light' || stored === 'dark') {
      setTheme(stored)
      return
    }

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    setTheme(prefersDark ? 'dark' : 'light')
  }, [])

  useEffect(() => {
    const isDark = theme === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
    window.localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  return (
    <div className="min-h-screen text-slate-900 transition-colors dark:text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur transition-colors dark:border-slate-800 dark:bg-slate-900/90">
        <div className="mx-auto flex h-16 max-w-7xl items-center px-6">
          <div className="shrink-0">
            <p className="font-display text-2xl tracking-tight text-brand-navy dark:text-blue-300">Visioapps Bank</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 xl:hidden">Modern banking experience powered by Visioapps Bank</p>
          </div>

          <div className="ml-auto flex min-w-0 flex-nowrap items-center gap-4">
            <nav className="hidden items-center gap-4 whitespace-nowrap xl:flex">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'rounded-full px-3 py-2 text-sm font-semibold whitespace-nowrap transition',
                      isActive
                        ? 'bg-brand-navy text-white shadow-soft dark:bg-blue-700'
                        : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="flex flex-nowrap items-center gap-2 whitespace-nowrap">
              <button
                type="button"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 whitespace-nowrap transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                Open Account
              </button>
              <a
                href="#"
                className="rounded-lg bg-brand-teal px-3 py-2 text-sm font-semibold text-white whitespace-nowrap transition hover:bg-emerald-600 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                visioapps.bank
              </a>
              <button
                type="button"
                onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                {theme === 'dark' ? (
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
                    <path d="M12 4a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V5a1 1 0 0 1 1-1Zm0 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm8-5a1 1 0 0 1-1 1h-1a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1ZM7 12a1 1 0 0 1-1 1H5a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1Zm9.657 5.243a1 1 0 0 1 1.414 1.414l-.707.707a1 1 0 1 1-1.414-1.414l.707-.707ZM8.05 8.636a1 1 0 0 1-1.414 0l-.707-.707A1 1 0 1 1 7.343 6.515l.707.707a1 1 0 0 1 0 1.414Zm9.314-2.121a1 1 0 0 1 0 1.414l-.707.707a1 1 0 0 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 0ZM8.05 15.364a1 1 0 0 1 0 1.414l-.707.707a1 1 0 1 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 0Z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3c.37 0 .74.02 1.1.07a1 1 0 0 1 .57 1.73A7 7 0 1 0 19.2 13.1a1 1 0 0 1 1.73.58c.05.36.07.73.07 1.1Z" />
                  </svg>
                )}
              </button>
              <span className="rounded-full bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-600 whitespace-nowrap dark:bg-slate-800 dark:text-slate-300">
                Helpline: +91-97830-39318
              </span>
            </div>
          </div>
        </div>
      </header>

      <main id="main-content" className="w-full">
        <div className="mx-auto max-w-7xl px-6 pb-12 pt-3">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/loans" element={<Loans />} />
            <Route path="/cards" element={<Cards />} />
            <Route path="/fees" element={<Fees />} />
            <Route path="/support" element={<Support />} />
          </Routes>
        </div>
      </main>

      <ChatWidget />
    </div>
  )
}
