import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/parties', label: 'Parties' },
  { to: '/contracts', label: 'Contracts' },
  { to: '/ingestion', label: 'Ingestion' },
  { to: '/settlements', label: 'Settlements' },
  { to: '/reports', label: 'Reports' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/journal-entries', label: 'Journal' },
];

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white/90 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center h-14 gap-1">
            <div className="font-bold text-gray-900 mr-4 flex-shrink-0">
              🎵 Royalty Engine
            </div>
            <div className="flex items-center gap-0.5 overflow-x-auto">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-gray-900 text-white shadow-sm'
                        : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
