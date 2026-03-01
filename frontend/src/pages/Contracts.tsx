import { useEffect, useState } from 'react';
import {
  getContracts,
  createContract,
  activateContract,
  terminateContract,
  getParties,
} from '../api/client';
import type { Contract, ContractStatus, ContractSplitRequest, Party } from '../types';
import { formatBps } from '../types';

const STATUS_COLORS: Record<ContractStatus, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  active: 'bg-green-100 text-green-800',
  expired: 'bg-gray-100 text-gray-500',
  terminated: 'bg-red-100 text-red-700',
};

export default function Contracts() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ContractStatus | ''>('');
  const [trackSearch, setTrackSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [allParties, setAllParties] = useState<Party[]>([]);

  const PAGE_SIZE = 20;

  const load = async () => {
    try {
      setLoading(true);
      const result = await getContracts(
        page,
        PAGE_SIZE,
        statusFilter || undefined,
        trackSearch || undefined
      );
      setContracts(result.items);
      setTotal(result.total);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load contracts');
    } finally {
      setLoading(false);
    }
  };

  const loadParties = async () => {
    try {
      const result = await getParties(1, 200);
      setAllParties(result.items);
    } catch { /* ignore */ }
  };

  useEffect(() => { load(); }, [page, statusFilter]);
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(); }, 300);
    return () => clearTimeout(t);
  }, [trackSearch]);

  const handleOpenCreate = async () => {
    await loadParties();
    setShowCreateModal(true);
  };

  const handleActivate = async (id: string) => {
    try {
      await activateContract(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to activate');
    }
  };

  const handleTerminate = async (id: string) => {
    if (!confirm('Terminate this contract?')) return;
    try {
      await terminateContract(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to terminate');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contracts</h1>
          <p className="text-sm text-gray-500 mt-0.5">Revenue split agreements per track</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
        >
          + New Contract
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Filter by track ID…"
          value={trackSearch}
          onChange={(e) => setTrackSearch(e.target.value)}
          className={inputCls + ' w-48'}
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as ContractStatus | ''); setPage(1); }}
          className={inputCls}
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="terminated">Terminated</option>
        </select>
        <span className="text-sm text-gray-500 ml-auto">{total} contracts</span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">Loading…</div>
      ) : contracts.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No contracts found.{' '}
          <button onClick={handleOpenCreate} className="text-gray-900 font-semibold hover:underline">
            Create one?
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Contract', 'Track ID', 'Status', 'Parties', 'Effective', 'Actions'].map((h) => (
                  <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {contracts.map((contract) => (
                <>
                  <tr
                    key={contract.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setExpandedId(expandedId === contract.id ? null : contract.id)}
                  >
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{contract.name}</div>
                      {contract.description && (
                        <div className="text-xs text-gray-400 truncate max-w-xs">{contract.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-gray-700">{contract.track_id}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[contract.status]}`}>
                        {contract.status.charAt(0).toUpperCase() + contract.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {contract.splits.length} {contract.splits.length === 1 ? 'party' : 'parties'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{contract.effective_date}</td>
                    <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-3">
                        {contract.status === 'draft' && (
                          <button
                            onClick={() => handleActivate(contract.id)}
                            className="text-sm text-green-600 hover:text-green-800 font-medium"
                          >
                            Activate
                          </button>
                        )}
                        {(contract.status === 'draft' || contract.status === 'active') && (
                          <button
                            onClick={() => handleTerminate(contract.id)}
                            className="text-sm text-red-500 hover:text-red-700 font-medium"
                          >
                            Terminate
                          </button>
                        )}
                        <button
                          onClick={() => setExpandedId(expandedId === contract.id ? null : contract.id)}
                          className="text-sm text-gray-500 hover:text-gray-700"
                        >
                          {expandedId === contract.id ? '▲' : '▼'}
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Expanded splits */}
                  {expandedId === contract.id && (
                    <tr key={`${contract.id}-splits`} className="bg-gray-50">
                      <td colSpan={6} className="px-8 py-4">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Revenue Splits</p>
                        <div className="space-y-1.5">
                          {contract.splits.map((split) => (
                            <div
                              key={split.id}
                              className="flex items-center gap-4 text-sm bg-white rounded-lg px-4 py-2 border border-gray-100"
                            >
                              <span className="font-mono text-xs text-gray-400">{split.party_id.slice(0, 8)}…</span>
                              {split.role && (
                                <span className="text-gray-500 italic text-xs">{split.role}</span>
                              )}
                              <div className="ml-auto flex items-center gap-3">
                                <div className="w-32 bg-gray-100 rounded-full h-1.5">
                                  <div
                                    className="bg-gray-800 h-1.5 rounded-full"
                                    style={{ width: `${split.share_bps / 100}%` }}
                                  />
                                </div>
                                <span className="font-semibold text-gray-900 w-16 text-right">
                                  {formatBps(split.share_bps)}
                                </span>
                              </div>
                            </div>
                          ))}
                          {/* BPS total check */}
                          <div className="flex items-center justify-end gap-3 text-xs text-gray-500 pt-1 pr-4">
                            <span>Total:</span>
                            <span className={`font-bold ${contract.splits.reduce((s, x) => s + x.share_bps, 0) === 10000 ? 'text-green-600' : 'text-red-600'}`}>
                              {formatBps(contract.splits.reduce((s, x) => s + x.share_bps, 0))}
                            </span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Create Contract Modal */}
      {showCreateModal && (
        <CreateContractModal
          parties={allParties}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); setPage(1); load(); }}
          onError={setError}
        />
      )}
    </div>
  );
}

// ─── Create Contract Modal ────────────────────────────────────────────────────

function CreateContractModal({
  parties,
  onClose,
  onCreated,
  onError,
}: {
  parties: Party[];
  onClose: () => void;
  onCreated: () => void;
  onError: (msg: string) => void;
}) {
  const [name, setName] = useState('');
  const [trackId, setTrackId] = useState('');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [description, setDescription] = useState('');
  const [splits, setSplits] = useState<ContractSplitRequest[]>([
    { party_id: '', share_bps: 5000, role: '' },
    { party_id: '', share_bps: 5000, role: '' },
  ]);
  const [submitting, setSubmitting] = useState(false);

  const totalBps = splits.reduce((s, x) => s + (x.share_bps || 0), 0);
  const isBalanced = totalBps === 10000;

  const addSplit = () => setSplits([...splits, { party_id: '', share_bps: 0, role: '' }]);
  const removeSplit = (i: number) => splits.length > 2 && setSplits(splits.filter((_, idx) => idx !== i));
  const updateSplit = (i: number, key: keyof ContractSplitRequest, value: string | number) => {
    const updated = [...splits];
    updated[i] = { ...updated[i], [key]: value };
    setSplits(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) { onError('Splits must total 10,000 BPS (100%)'); return; }
    setSubmitting(true);
    try {
      await createContract({
        name,
        track_id: trackId,
        effective_date: effectiveDate,
        expiry_date: expiryDate || undefined,
        description: description || undefined,
        splits: splits.map((s) => ({
          party_id: s.party_id,
          share_bps: s.share_bps,
          role: s.role || undefined,
        })),
      });
      onCreated();
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Failed to create contract');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">New Contract</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Basic fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={labelCls}>Contract Name <span className="text-red-500">*</span></label>
              <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Track ID <span className="text-red-500">*</span></label>
              <input value={trackId} onChange={(e) => setTrackId(e.target.value)} placeholder="TRACK-001" className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Effective Date <span className="text-red-500">*</span></label>
              <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Expiry Date</label>
              <input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} />
            </div>
          </div>

          {/* Splits */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-semibold text-gray-700">Revenue Splits</label>
              <button type="button" onClick={addSplit} className="text-xs text-gray-600 hover:text-gray-900 font-medium">
                + Add Party
              </button>
            </div>

            <div className="space-y-2">
              {splits.map((split, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <select
                    value={split.party_id}
                    onChange={(e) => updateSplit(i, 'party_id', e.target.value)}
                    className={inputCls + ' flex-1'}
                    required
                  >
                    <option value="">Select party…</option>
                    {parties.map((p) => (
                      <option key={p.id} value={p.id}>{p.name} ({p.party_type})</option>
                    ))}
                  </select>
                  <div className="relative w-28">
                    <input
                      type="number"
                      min={1}
                      max={10000}
                      value={split.share_bps}
                      onChange={(e) => updateSplit(i, 'share_bps', parseInt(e.target.value) || 0)}
                      className={inputCls + ' pr-8'}
                      required
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">BPS</span>
                  </div>
                  <input
                    type="text"
                    placeholder="Role"
                    value={split.role ?? ''}
                    onChange={(e) => updateSplit(i, 'role', e.target.value)}
                    className={inputCls + ' w-28'}
                  />
                  {splits.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removeSplit(i)}
                      className="text-gray-400 hover:text-red-500 text-lg leading-none flex-shrink-0"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* BPS total indicator */}
            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1 bg-gray-100 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${isBalanced ? 'bg-green-500' : totalBps > 10000 ? 'bg-red-500' : 'bg-yellow-400'}`}
                  style={{ width: `${Math.min(100, totalBps / 100)}%` }}
                />
              </div>
              <span className={`text-sm font-semibold w-20 text-right ${isBalanced ? 'text-green-600' : 'text-red-600'}`}>
                {formatBps(totalBps)} / 100%
              </span>
            </div>
            {!isBalanced && (
              <p className="text-xs text-red-500 mt-1">
                Splits must total exactly 10,000 BPS (100%). Currently: {totalBps.toLocaleString()} BPS.
              </p>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className={cancelBtnCls}>Cancel</button>
            <button
              type="submit"
              disabled={submitting || !isBalanced}
              className={primaryBtnCls}
            >
              {submitting ? 'Creating…' : 'Create Contract'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900';
const labelCls = 'block text-sm font-medium text-gray-700 mb-1';
const primaryBtnCls = 'px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors disabled:opacity-50';
const cancelBtnCls = 'px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors';
