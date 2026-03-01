import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getTrialBalance,
  getAccounts,
  seedAccounts,
  getParties,
  getContracts,
  getIngestionJobs,
  getSettlementRuns,
} from '../api/client';
import type { TrialBalance, Account } from '../types';
import { formatDollars } from '../types';

interface QuickStats {
  parties: number;
  activeContracts: number;
  ingestionJobs: number;
  settlementRuns: number;
}

export default function Dashboard() {
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [tb, accts, parties, contracts, jobs, runs] = await Promise.all([
        getTrialBalance(),
        getAccounts(),
        getParties(1, 1).catch(() => ({ total: 0 })),
        getContracts(1, 1, 'active').catch(() => ({ total: 0 })),
        getIngestionJobs(1, 1).catch(() => ({ total: 0 })),
        getSettlementRuns(1, 1).catch(() => ({ total: 0 })),
      ]);
      setTrialBalance(tb);
      setAccounts(accts);
      setStats({
        parties: (parties as { total: number }).total,
        activeContracts: (contracts as { total: number }).total,
        ingestionJobs: (jobs as { total: number }).total,
        settlementRuns: (runs as { total: number }).total,
      });
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleSeedAccounts = async () => {
    try {
      await seedAccounts();
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to seed accounts');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="inline-block w-6 h-6 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mb-3" />
          <div className="text-sm text-gray-500">Loading…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Music Royalty Settlement Engine</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-8 text-center">
          <div className="text-3xl mb-3">⚙️</div>
          <p className="text-amber-900 font-semibold mb-1">Chart of Accounts not initialized</p>
          <p className="text-amber-700 text-sm mb-4">Seed the standard accounts to get started.</p>
          <button
            onClick={handleSeedAccounts}
            className="bg-gray-900 text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-gray-800 shadow-sm transition-all"
          >
            Seed Standard Accounts
          </button>
        </div>
      ) : (
        <>
          {/* Module Quick-Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <QuickStatCard label="Parties" value={stats?.parties ?? 0} icon="👤" to="/parties" color="bg-purple-50" />
            <QuickStatCard label="Active Contracts" value={stats?.activeContracts ?? 0} icon="📄" to="/contracts" color="bg-green-50" />
            <QuickStatCard label="Ingestion Jobs" value={stats?.ingestionJobs ?? 0} icon="📥" to="/ingestion" color="bg-blue-50" />
            <QuickStatCard label="Settlement Runs" value={stats?.settlementRuns ?? 0} icon="💰" to="/settlements" color="bg-gray-900" dark />
          </div>

          {/* Ledger Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Total Accounts</div>
              <div className="text-3xl font-bold text-gray-900">{accounts.length}</div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Total Debits</div>
              <div className="text-3xl font-bold text-gray-900 font-mono">
                {formatDollars(trialBalance?.total_debits_micros ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Total Credits</div>
              <div className="text-3xl font-bold text-gray-900 font-mono">
                {formatDollars(trialBalance?.total_credits_micros ?? 0)}
              </div>
            </div>
          </div>

          {/* Trial Balance */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
              <h2 className="text-base font-semibold text-gray-900">Trial Balance</h2>
              {trialBalance && (
                <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${trialBalance.is_balanced ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {trialBalance.is_balanced ? '✓ Balanced' : '✗ Unbalanced'}
                </span>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    {['Account', 'Type', 'Debit', 'Credit'].map((h, i) => (
                      <th key={h} className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${i >= 2 ? 'text-right' : 'text-left'}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {trialBalance?.line_items.map((item) => (
                    <tr key={item.account_number} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-3.5 whitespace-nowrap">
                        <span className="font-mono text-sm font-medium text-gray-700">{item.account_number}</span>
                        <span className="ml-2 text-sm text-gray-500">{item.account_name}</span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${typeColors[item.account_type]}`}>
                          {item.account_type.charAt(0).toUpperCase() + item.account_type.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono text-sm text-gray-700">
                        {item.debit_balance_micros > 0 ? formatDollars(item.debit_balance_micros) : '—'}
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono text-sm text-gray-700">
                        {item.credit_balance_micros > 0 ? formatDollars(item.credit_balance_micros) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50">
                  <tr className="font-semibold">
                    <td colSpan={2} className="px-6 py-3.5 text-sm text-gray-700">Total</td>
                    <td className="px-6 py-3.5 text-right font-mono text-sm text-gray-900">
                      {formatDollars(trialBalance?.total_debits_micros ?? 0)}
                    </td>
                    <td className="px-6 py-3.5 text-right font-mono text-sm text-gray-900">
                      {formatDollars(trialBalance?.total_credits_micros ?? 0)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function QuickStatCard({
  label, value, icon, to, color, dark,
}: {
  label: string; value: number; icon: string; to: string; color: string; dark?: boolean;
}) {
  return (
    <Link to={to} className={`rounded-xl p-5 ${color} hover:opacity-90 transition-opacity block`}>
      <div className="text-xl mb-2">{icon}</div>
      <div className={`text-3xl font-bold ${dark ? 'text-white' : 'text-gray-900'}`}>
        {value.toLocaleString()}
      </div>
      <div className={`text-xs font-medium mt-1 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
        {label}
      </div>
    </Link>
  );
}

const typeColors: Record<string, string> = {
  asset: 'bg-blue-100 text-blue-700',
  liability: 'bg-orange-100 text-orange-700',
  revenue: 'bg-green-100 text-green-700',
  expense: 'bg-red-100 text-red-700',
};
