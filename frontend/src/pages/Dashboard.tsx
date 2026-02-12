import { useEffect, useState } from 'react';
import { getTrialBalance, getAccounts, seedAccounts } from '../api/client';
import type { TrialBalance, Account } from '../types';
import { formatDollars } from '../types';

export default function Dashboard() {
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [tb, accts] = await Promise.all([getTrialBalance(), getAccounts()]);
      setTrialBalance(tb);
      setAccounts(accts);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSeedAccounts = async () => {
    try {
      await seedAccounts();
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to seed accounts');
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800 mb-4">No accounts found. Initialize the chart of accounts?</p>
          <button
            onClick={handleSeedAccounts}
            className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
          >
            Seed Standard Accounts
          </button>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500">Total Accounts</div>
              <div className="text-3xl font-bold">{accounts.length}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500">Total Debits</div>
              <div className="text-3xl font-bold">
                {formatDollars(trialBalance?.total_debits_micros || 0)}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500">Total Credits</div>
              <div className="text-3xl font-bold">
                {formatDollars(trialBalance?.total_credits_micros || 0)}
              </div>
            </div>
          </div>

          {/* Trial Balance */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Trial Balance</h2>
              <span
                className={`px-2 py-1 text-xs rounded ${
                  trialBalance?.is_balanced
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {trialBalance?.is_balanced ? 'Balanced' : 'Unbalanced'}
              </span>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Account
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Type
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Debit
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Credit
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {trialBalance?.line_items.map((item) => (
                  <tr key={item.account_number}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium">{item.account_number}</div>
                      <div className="text-sm text-gray-500">{item.account_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap capitalize">{item.account_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      {item.debit_balance_micros > 0 ? formatDollars(item.debit_balance_micros) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      {item.credit_balance_micros > 0 ? formatDollars(item.credit_balance_micros) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50 font-bold">
                <tr>
                  <td colSpan={2} className="px-6 py-3">
                    Total
                  </td>
                  <td className="px-6 py-3 text-right">
                    {formatDollars(trialBalance?.total_debits_micros || 0)}
                  </td>
                  <td className="px-6 py-3 text-right">
                    {formatDollars(trialBalance?.total_credits_micros || 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
