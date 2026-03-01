import { useEffect, useState } from 'react';
import {
  getSettlementRuns,
  createSettlementRun,
  getIngestionJobs,
} from '../api/client';
import type { IngestionJob, SettlementRun, SettlementStatus } from '../types';
import { formatDollars, formatBps } from '../types';

const STATUS_COLORS: Record<SettlementStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function Settlements() {
  const [runs, setRuns] = useState<SettlementRun[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<SettlementStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [showRunModal, setShowRunModal] = useState(false);
  const [completedJobs, setCompletedJobs] = useState<IngestionJob[]>([]);

  const PAGE_SIZE = 20;

  const load = async () => {
    try {
      setLoading(true);
      const result = await getSettlementRuns(page, PAGE_SIZE, statusFilter || undefined);
      setRuns(result.items);
      setTotal(result.total);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settlement runs');
    } finally {
      setLoading(false);
    }
  };

  const loadCompletedJobs = async () => {
    try {
      const result = await getIngestionJobs(1, 100, 'completed');
      setCompletedJobs(result.items);
    } catch { /* ignore */ }
  };

  useEffect(() => { load(); }, [page, statusFilter]);

  const openRunModal = async () => {
    await loadCompletedJobs();
    setShowRunModal(true);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Summary stats
  const completedRuns = runs.filter((r) => r.status === 'completed');
  const totalGross = completedRuns.reduce((s, r) => s + r.total_gross_micros, 0);
  const totalFee = completedRuns.reduce((s, r) => s + r.total_platform_fee_micros, 0);
  const totalNet = completedRuns.reduce((s, r) => s + r.total_net_micros, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settlements</h1>
          <p className="text-sm text-gray-500 mt-0.5">Royalty distribution runs</p>
        </div>
        <button
          onClick={openRunModal}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
        >
          Run Settlement
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Stats strip */}
      {completedRuns.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Gross Revenue Settled" value={formatDollars(totalGross)} />
          <StatCard label="Platform Fees Collected" value={formatDollars(totalFee)} sub={`${formatBps(completedRuns[0]?.platform_fee_bps ?? 1500)} avg rate`} />
          <StatCard label="Net Distributed to Parties" value={formatDollars(totalNet)} highlight />
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as SettlementStatus | ''); setPage(1); }}
          className={inputCls}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <span className="text-sm text-gray-500 ml-auto">{total} runs</span>
      </div>

      {/* Runs table */}
      {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">Loading…</div>
      ) : runs.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No settlement runs yet.{' '}
          <button onClick={openRunModal} className="text-gray-900 font-semibold hover:underline">
            Run first settlement?
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Statement', 'Status', 'Tracks', 'Gross', 'Platform Fee', 'Net', 'Date', ''].map((h) => (
                  <th key={h} className={`px-5 py-3 text-${h === 'Gross' || h === 'Platform Fee' || h === 'Net' ? 'right' : 'left'} text-xs font-medium text-gray-500 uppercase tracking-wider`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {runs.map((run) => (
                <>
                  <tr
                    key={run.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                  >
                    <td className="px-5 py-4">
                      <div className="font-medium text-gray-900">{run.statement_id}</div>
                      <div className="text-xs text-gray-400 font-mono">{run.job_id.slice(0, 8)}…</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[run.status]}`}>
                        {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-700">
                      <div>{run.total_tracks} total</div>
                      {run.unmatched_tracks > 0 && (
                        <div className="text-xs text-amber-600">{run.unmatched_tracks} unmatched</div>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm">{formatDollars(run.total_gross_micros)}</td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-gray-500">
                      {formatDollars(run.total_platform_fee_micros)}
                      <div className="text-xs text-gray-400">{formatBps(run.platform_fee_bps)}</div>
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm font-semibold text-gray-900">
                      {formatDollars(run.total_net_micros)}
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500">
                      {new Date(run.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-4 text-gray-400 text-sm">
                      {expandedId === run.id ? '▲' : '▼'}
                    </td>
                  </tr>

                  {expandedId === run.id && (
                    <tr key={`${run.id}-lines`} className="bg-gray-50">
                      <td colSpan={8} className="px-6 py-4">
                        {run.status === 'failed' && run.error_message && (
                          <div className="mb-3 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                            <strong>Error:</strong> {run.error_message}
                          </div>
                        )}
                        {run.lines.length === 0 ? (
                          <p className="text-sm text-gray-500">No settlement lines.</p>
                        ) : (
                          <div className="space-y-3">
                            <p className="text-xs font-semibold text-gray-500 uppercase">
                              Settlement Lines ({run.lines.length} tracks)
                            </p>
                            {run.lines.map((line) => (
                              <div
                                key={line.id}
                                className={`rounded-lg border px-4 py-3 ${line.is_unmatched ? 'border-amber-200 bg-amber-50' : 'border-gray-100 bg-white'}`}
                              >
                                <div className="flex items-start justify-between">
                                  <div>
                                    <span className="font-medium text-gray-900">{line.track_name}</span>
                                    <span className="ml-2 font-mono text-xs text-gray-400">{line.track_id}</span>
                                    {line.is_unmatched && (
                                      <span className="ml-2 px-1.5 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">No contract</span>
                                    )}
                                  </div>
                                  <div className="text-right text-sm">
                                    <div className="text-gray-400">Gross: {formatDollars(line.gross_micros)}</div>
                                    <div className="text-gray-400">Fee: {formatDollars(line.platform_fee_micros)}</div>
                                    <div className="font-semibold text-gray-900">Net: {formatDollars(line.net_micros)}</div>
                                  </div>
                                </div>

                                {line.allocations.length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-gray-100 grid grid-cols-2 gap-1.5 md:grid-cols-3 lg:grid-cols-4">
                                    {line.allocations.map((alloc) => (
                                      <div key={alloc.id} className="flex justify-between text-xs bg-gray-50 rounded px-2 py-1">
                                        <span className="text-gray-500 truncate">{alloc.party_id.slice(0, 8)}…</span>
                                        <span className="font-mono text-gray-700 ml-2 flex-shrink-0">
                                          {formatDollars(alloc.amount_micros)}
                                          <span className="text-gray-400 ml-1">({formatBps(alloc.share_bps)})</span>
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
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

      {/* Run Settlement Modal */}
      {showRunModal && (
        <RunSettlementModal
          completedJobs={completedJobs}
          onClose={() => setShowRunModal(false)}
          onCreated={() => { setShowRunModal(false); setPage(1); load(); }}
          onError={setError}
        />
      )}
    </div>
  );
}

// ─── Stats Card ───────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, highlight }: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`rounded-lg p-5 ${highlight ? 'bg-gray-900 text-white' : 'bg-white shadow'}`}>
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 ${highlight ? 'text-gray-400' : 'text-gray-500'}`}>
        {label}
      </div>
      <div className={`text-2xl font-bold ${highlight ? 'text-white' : 'text-gray-900'}`}>{value}</div>
      {sub && <div className={`text-xs mt-0.5 ${highlight ? 'text-gray-500' : 'text-gray-400'}`}>{sub}</div>}
    </div>
  );
}

// ─── Run Settlement Modal ─────────────────────────────────────────────────────

function RunSettlementModal({
  completedJobs,
  onClose,
  onCreated,
  onError,
}: {
  completedJobs: IngestionJob[];
  onClose: () => void;
  onCreated: () => void;
  onError: (msg: string) => void;
}) {
  const [selectedJobId, setSelectedJobId] = useState('');
  const [manualJobId, setManualJobId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const jobId = selectedJobId || manualJobId;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobId.trim()) { onError('Please select or enter a Job ID'); return; }
    setSubmitting(true);
    try {
      await createSettlementRun({ job_id: jobId.trim() });
      onCreated();
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Settlement failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Run Settlement</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {completedJobs.length > 0 ? (
            <div>
              <label className={labelCls}>Select a completed ingestion job</label>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className={inputCls}
              >
                <option value="">— choose a job —</option>
                {completedJobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.statement_id} · {job.total_records} records · {new Date(job.statement_date).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
              No completed ingestion jobs found. Upload and process a CSV first.
            </p>
          )}

          <div>
            <label className={labelCls}>Or enter Job ID manually</label>
            <input
              type="text"
              value={manualJobId}
              onChange={(e) => { setManualJobId(e.target.value); setSelectedJobId(''); }}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className={inputCls + ' font-mono text-xs'}
            />
          </div>

          <div className="bg-gray-50 rounded-lg px-4 py-3 text-xs text-gray-600 space-y-1">
            <p className="font-semibold text-gray-700">What happens next</p>
            <p>• Each track's revenue is split by its active contract</p>
            <p>• Platform fee (15%) is deducted from gross revenue</p>
            <p>• A double-entry journal entry is written per track</p>
            <p>• Tracks without contracts go to Revenue Clearing</p>
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className={cancelBtnCls}>Cancel</button>
            <button
              type="submit"
              disabled={submitting || !jobId.trim()}
              className={primaryBtnCls}
            >
              {submitting ? 'Running…' : 'Run Settlement'}
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
