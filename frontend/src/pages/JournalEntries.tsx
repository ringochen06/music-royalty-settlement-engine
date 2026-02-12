import { useEffect, useState } from 'react';
import {
  getJournalEntries,
  getAccounts,
  createJournalEntry,
  reverseJournalEntry,
} from '../api/client';
import type { JournalEntry, Account, JournalStatus, CreatePostingRequest } from '../types';
import { formatDollars, toMicros } from '../types';

export default function JournalEntries() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<JournalStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [description, setDescription] = useState('');
  const [postings, setPostings] = useState<
    { account_id: string; amount: string; is_debit: boolean; memo: string }[]
  >([
    { account_id: '', amount: '', is_debit: true, memo: '' },
    { account_id: '', amount: '', is_debit: false, memo: '' },
  ]);

  const loadEntries = async () => {
    try {
      setLoading(true);
      const result = await getJournalEntries(page, 20, statusFilter || undefined);
      setEntries(result.items);
      setTotalPages(result.total_pages);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load entries');
    } finally {
      setLoading(false);
    }
  };

  const loadAccounts = async () => {
    try {
      const accts = await getAccounts();
      setAccounts(accts);
    } catch (e) {
      console.error('Failed to load accounts', e);
    }
  };

  useEffect(() => {
    loadEntries();
  }, [page, statusFilter]);

  useEffect(() => {
    loadAccounts();
  }, []);

  const handleAddPosting = () => {
    setPostings([...postings, { account_id: '', amount: '', is_debit: true, memo: '' }]);
  };

  const handleRemovePosting = (index: number) => {
    if (postings.length > 2) {
      setPostings(postings.filter((_, i) => i !== index));
    }
  };

  const handlePostingChange = (
    index: number,
    field: keyof (typeof postings)[0],
    value: string | boolean
  ) => {
    const updated = [...postings];
    updated[index] = { ...updated[index], [field]: value };
    setPostings(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const postingData: CreatePostingRequest[] = postings.map((p) => ({
        account_id: p.account_id,
        amount_micros: toMicros(parseFloat(p.amount) || 0),
        is_debit: p.is_debit,
        memo: p.memo || undefined,
      }));

      await createJournalEntry({
        occurred_at: new Date().toISOString(),
        description,
        postings: postingData,
      });

      setShowForm(false);
      setDescription('');
      setPostings([
        { account_id: '', amount: '', is_debit: true, memo: '' },
        { account_id: '', amount: '', is_debit: false, memo: '' },
      ]);
      await loadEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create entry');
    }
  };

  const handleReverse = async (id: string) => {
    if (!confirm('Reverse this entry?')) return;
    try {
      await reverseJournalEntry(id);
      await loadEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reverse entry');
    }
  };

  const totalDebit = postings
    .filter((p) => p.is_debit)
    .reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
  const totalCredit = postings
    .filter((p) => !p.is_debit)
    .reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Journal Entries</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
        >
          New Entry
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
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as JournalStatus | '');
            setPage(1);
          }}
          className="border rounded px-3 py-2"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="posted">Posted</option>
          <option value="reversed">Reversed</option>
        </select>
      </div>

      {/* Create Entry Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-auto py-8">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4">
            <h2 className="text-xl font-bold mb-4">Create Journal Entry</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-medium">Postings</label>
                  <button
                    type="button"
                    onClick={handleAddPosting}
                    className="text-gray-700 hover:text-gray-900 text-sm font-medium hover:underline transition-all"
                  >
                    + Add Line
                  </button>
                </div>

                {postings.map((posting, index) => (
                  <div key={index} className="flex gap-2 items-start">
                    <select
                      value={posting.account_id}
                      onChange={(e) => handlePostingChange(index, 'account_id', e.target.value)}
                      className="flex-1 border rounded px-2 py-1.5 text-sm"
                      required
                    >
                      <option value="">Select Account</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.account_number} - {a.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Amount"
                      value={posting.amount}
                      onChange={(e) => handlePostingChange(index, 'amount', e.target.value)}
                      className="w-28 border rounded px-2 py-1.5 text-sm"
                      required
                    />
                    <select
                      value={posting.is_debit ? 'debit' : 'credit'}
                      onChange={(e) =>
                        handlePostingChange(index, 'is_debit', e.target.value === 'debit')
                      }
                      className="w-24 border rounded px-2 py-1.5 text-sm"
                    >
                      <option value="debit">Debit</option>
                      <option value="credit">Credit</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Memo"
                      value={posting.memo}
                      onChange={(e) => handlePostingChange(index, 'memo', e.target.value)}
                      className="w-32 border rounded px-2 py-1.5 text-sm"
                    />
                    {postings.length > 2 && (
                      <button
                        type="button"
                        onClick={() => handleRemovePosting(index)}
                        className="text-red-500 hover:text-red-700 px-2"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}

                <div className="flex justify-between text-sm pt-2 border-t">
                  <span>Total Debits: ${totalDebit.toFixed(2)}</span>
                  <span>Total Credits: ${totalCredit.toFixed(2)}</span>
                  <span className={isBalanced ? 'text-green-600' : 'text-red-600'}>
                    {isBalanced ? 'Balanced' : 'Not Balanced'}
                  </span>
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-100 hover:border-gray-400 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!isBalanced}
                  className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Entries List */}
      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <div className="space-y-4">
          {entries.map((entry) => (
            <div key={entry.id} className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="font-medium">{entry.description}</div>
                  <div className="text-sm text-gray-500">
                    {new Date(entry.occurred_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      entry.status === 'posted'
                        ? 'bg-green-100 text-green-800'
                        : entry.status === 'reversed'
                        ? 'bg-gray-100 text-gray-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {entry.status}
                  </span>
                  {entry.status === 'posted' && (
                    <button
                      onClick={() => handleReverse(entry.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Reverse
                    </button>
                  )}
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b">
                    <th className="text-left py-1">Account</th>
                    <th className="text-right py-1">Debit</th>
                    <th className="text-right py-1">Credit</th>
                    <th className="text-left py-1 pl-4">Memo</th>
                  </tr>
                </thead>
                <tbody>
                  {entry.postings.map((p) => {
                    const account = accounts.find((a) => a.id === p.account_id);
                    return (
                      <tr key={p.id}>
                        <td className="py-1">
                          {account ? `${account.account_number} - ${account.name}` : p.account_id}
                        </td>
                        <td className="text-right py-1">
                          {p.is_debit ? formatDollars(p.amount_micros) : '-'}
                        </td>
                        <td className="text-right py-1">
                          {!p.is_debit ? formatDollars(p.amount_micros) : '-'}
                        </td>
                        <td className="text-left py-1 pl-4 text-gray-500">{p.memo || '-'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Prev
          </button>
          <span className="px-3 py-1">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
