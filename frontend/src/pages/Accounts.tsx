import { useEffect, useState } from 'react';
import { getAccounts, getAccountBalance, createAccount } from '../api/client';
import type { Account, AccountBalance, AccountType } from '../types';
import { formatDollars } from '../types';

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [balances, setBalances] = useState<Record<string, AccountBalance>>({});
  const [filter, setFilter] = useState<AccountType | ''>('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    account_number: '',
    name: '',
    account_type: 'asset' as AccountType,
    description: '',
  });

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const accts = await getAccounts(filter || undefined);
      setAccounts(accts);

      // Load balances for each account
      const balancePromises = accts.map((a) =>
        getAccountBalance(a.id).then((b) => [a.id, b] as const)
      );
      const balanceResults = await Promise.all(balancePromises);
      setBalances(Object.fromEntries(balanceResults));
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, [filter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createAccount({
        ...formData,
        description: formData.description || undefined,
      });
      setShowForm(false);
      setFormData({ account_number: '', name: '', account_type: 'asset', description: '' });
      await loadAccounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create account');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Accounts</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          New Account
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Filter */}
      <div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as AccountType | '')}
          className="border rounded px-3 py-2"
        >
          <option value="">All Types</option>
          <option value="asset">Asset</option>
          <option value="liability">Liability</option>
          <option value="revenue">Revenue</option>
          <option value="expense">Expense</option>
        </select>
      </div>

      {/* Create Account Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create Account</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Account Number</label>
                <input
                  type="text"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Type</label>
                <select
                  value={formData.account_type}
                  onChange={(e) => setFormData({ ...formData, account_type: e.target.value as AccountType })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="asset">Asset</option>
                  <option value="liability">Liability</option>
                  <option value="revenue">Revenue</option>
                  <option value="expense">Expense</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 border rounded hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Account Table */}
      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Account
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Normal Balance
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Balance
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium">{account.account_number}</div>
                    <div className="text-sm text-gray-500">{account.name}</div>
                  </td>
                  <td className="px-6 py-4 capitalize">{account.account_type}</td>
                  <td className="px-6 py-4 capitalize">{account.normal_balance}</td>
                  <td className="px-6 py-4 text-right font-mono">
                    {balances[account.id]
                      ? formatDollars(balances[account.id].balance_micros)
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
