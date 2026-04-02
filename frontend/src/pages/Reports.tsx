import { useEffect, useState } from 'react';
import {
  getParties,
  getReportAccountBalances,
  getReportPartyStatement,
  getReportSettlementSummary,
  getReportTrialBalance,
  getSettlementRuns,
} from '../api/client';
import type {
  AccountBalancesReport,
  Party,
  PartyStatementReport,
  SettlementRun,
  SettlementSummaryReport,
  TrialBalance,
} from '../types';
import { formatBps, formatDollars } from '../types';

type Tab = 'trial-balance' | 'account-balances' | 'settlement-summary' | 'party-statement';

const TABS: { id: Tab; label: string }[] = [
  { id: 'trial-balance', label: 'Trial Balance' },
  { id: 'account-balances', label: 'Account Balances' },
  { id: 'settlement-summary', label: 'Settlement Summary' },
  { id: 'party-statement', label: 'Party Statement' },
];

const ACCOUNT_TYPE_COLORS: Record<string, string> = {
  asset: 'bg-blue-100 text-blue-800',
  liability: 'bg-orange-100 text-orange-800',
  revenue: 'bg-green-100 text-green-800',
  expense: 'bg-red-100 text-red-800',
};

export default function Reports() {
  const [activeTab, setActiveTab] = useState<Tab>('trial-balance');
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Reports</h1>

      {/* Tab Nav */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setError(null); }}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
              activeTab === tab.id
                ? 'bg-white border border-b-white border-gray-200 -mb-px text-gray-900'
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div>
        {activeTab === 'trial-balance' && <TrialBalanceTab onError={setError} />}
        {activeTab === 'account-balances' && <AccountBalancesTab onError={setError} />}
        {activeTab === 'settlement-summary' && <SettlementSummaryTab onError={setError} />}
        {activeTab === 'party-statement' && <PartyStatementTab onError={setError} />}
      </div>
    </div>
  );
}

// ─── Trial Balance ────────────────────────────────────────────────────────────

function TrialBalanceTab({ onError }: { onError: (e: string) => void }) {
  const [data, setData] = useState<TrialBalance | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReportTrialBalance()
      .then(setData)
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
  }, [onError]);

  if (loading) return <LoadingSpinner />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">As of {new Date(data.as_of_date).toLocaleString()}</p>
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${
            data.is_balanced ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {data.is_balanced ? 'Balanced' : 'OUT OF BALANCE'}
        </span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Account</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Debit</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Credit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.line_items.map((item) => (
              <tr key={item.account_number} className="hover:bg-gray-50">
                <td className="px-4 py-2.5">
                  <span className="font-mono text-gray-500 mr-2">{item.account_number}</span>
                  {item.account_name}
                </td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ACCOUNT_TYPE_COLORS[item.account_type] ?? 'bg-gray-100 text-gray-600'}`}>
                    {item.account_type}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {item.debit_balance_micros > 0 ? formatDollars(item.debit_balance_micros) : '—'}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {item.credit_balance_micros > 0 ? formatDollars(item.credit_balance_micros) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-gray-50 border-t-2 border-gray-300 font-semibold">
              <td className="px-4 py-3" colSpan={2}>Totals</td>
              <td className="px-4 py-3 text-right font-mono">{formatDollars(data.total_debits_micros)}</td>
              <td className="px-4 py-3 text-right font-mono">{formatDollars(data.total_credits_micros)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

// ─── Account Balances ─────────────────────────────────────────────────────────

function AccountBalancesTab({ onError }: { onError: (e: string) => void }) {
  const [data, setData] = useState<AccountBalancesReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReportAccountBalances()
      .then(setData)
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
  }, [onError]);

  if (loading) return <LoadingSpinner />;
  if (!data) return null;

  const summaryCards = [
    { label: 'Total Assets', micros: data.total_assets_micros, color: 'text-blue-700' },
    { label: 'Total Liabilities', micros: data.total_liabilities_micros, color: 'text-orange-700' },
    { label: 'Total Revenue', micros: data.total_revenue_micros, color: 'text-green-700' },
    { label: 'Total Expenses', micros: data.total_expenses_micros, color: 'text-red-700' },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">{card.label}</p>
            <p className={`text-lg font-bold font-mono ${card.color}`}>{formatDollars(card.micros)}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Account</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Normal</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.accounts.map((acct) => (
              <tr key={acct.account_id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5">
                  <span className="font-mono text-gray-500 mr-2">{acct.account_number}</span>
                  {acct.account_name}
                </td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ACCOUNT_TYPE_COLORS[acct.account_type] ?? 'bg-gray-100 text-gray-600'}`}>
                    {acct.account_type}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-500 capitalize">{acct.normal_balance}</td>
                <td className={`px-4 py-2.5 text-right font-mono font-medium ${acct.balance_micros < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {formatDollars(acct.balance_micros)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Settlement Summary ───────────────────────────────────────────────────────

function SettlementSummaryTab({ onError }: { onError: (e: string) => void }) {
  const [runs, setRuns] = useState<SettlementRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [data, setData] = useState<SettlementSummaryReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(true);

  useEffect(() => {
    getSettlementRuns(1, 100, 'completed')
      .then((res) => setRuns(res.items))
      .catch((e) => onError(e.message))
      .finally(() => setLoadingRuns(false));
  }, [onError]);

  function load() {
    if (!selectedRunId) return;
    setLoading(true);
    setData(null);
    getReportSettlementSummary(selectedRunId)
      .then(setData)
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <select
          value={selectedRunId}
          onChange={(e) => { setSelectedRunId(e.target.value); setData(null); }}
          className={inputClass}
          disabled={loadingRuns}
        >
          <option value="">{loadingRuns ? 'Loading…' : 'Select a completed settlement run'}</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>{r.statement_id} — {new Date(r.created_at).toLocaleDateString()}</option>
          ))}
        </select>
        <button
          onClick={load}
          disabled={!selectedRunId || loading}
          className={primaryBtn}
        >
          {loading ? 'Loading…' : 'Generate'}
        </button>
      </div>

      {data && (
        <div className="space-y-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Gross Revenue', micros: data.total_gross_micros },
              { label: 'Platform Fee', micros: data.total_platform_fee_micros },
              { label: 'Net Distributed', micros: data.total_net_micros },
              { label: 'Unmatched', micros: data.total_unmatched_micros },
            ].map((c) => (
              <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-500 mb-1">{c.label}</p>
                <p className="text-lg font-bold font-mono text-gray-900">{formatDollars(c.micros)}</p>
              </div>
            ))}
          </div>

          <div className="flex gap-4 text-sm text-gray-600">
            <span>Tracks: <strong>{data.total_tracks}</strong></span>
            <span>Matched: <strong>{data.matched_tracks}</strong></span>
            <span>Unmatched: <strong>{data.unmatched_tracks}</strong></span>
            <span>Platform fee: <strong>{formatBps(data.platform_fee_bps)}</strong></span>
          </div>

          {/* Party breakdown */}
          {data.party_totals.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <h3 className="font-semibold text-gray-700">Party Breakdown</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left px-4 py-3 font-semibold text-gray-700">Party</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">Tracks</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">Amount</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">% of Net</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.party_totals.map((pt) => (
                    <tr key={pt.party_id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-medium">{pt.party_name}</td>
                      <td className="px-4 py-2.5 capitalize text-gray-500">{pt.party_type}</td>
                      <td className="px-4 py-2.5 text-right">{pt.track_count}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{formatDollars(pt.total_amount_micros)}</td>
                      <td className="px-4 py-2.5 text-right text-gray-500">
                        {data.total_net_micros > 0
                          ? `${((pt.total_amount_micros / data.total_net_micros) * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No party allocations — all tracks were unmatched.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Party Statement ─────────────────────────────────────────────────────────

function PartyStatementTab({ onError }: { onError: (e: string) => void }) {
  const [parties, setParties] = useState<Party[]>([]);
  const [selectedPartyId, setSelectedPartyId] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [data, setData] = useState<PartyStatementReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingParties, setLoadingParties] = useState(true);

  useEffect(() => {
    getParties(1, 200, undefined, 'active')
      .then((res) => setParties(res.items))
      .catch((e) => onError(e.message))
      .finally(() => setLoadingParties(false));
  }, [onError]);

  function load() {
    if (!selectedPartyId) return;
    setLoading(true);
    setData(null);
    getReportPartyStatement(
      selectedPartyId,
      fromDate ? new Date(fromDate).toISOString() : undefined,
      toDate ? new Date(toDate + 'T23:59:59').toISOString() : undefined,
    )
      .then(setData)
      .catch((e) => onError(e.message))
      .finally(() => setLoading(false));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium text-gray-600 mb-1">Party</label>
          <select
            value={selectedPartyId}
            onChange={(e) => { setSelectedPartyId(e.target.value); setData(null); }}
            className={inputClass}
            disabled={loadingParties}
          >
            <option value="">{loadingParties ? 'Loading…' : 'Select a party'}</option>
            {parties.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.party_type})</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">From date</label>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">To date</label>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className={inputClass} />
        </div>
        <button
          onClick={load}
          disabled={!selectedPartyId || loading}
          className={primaryBtn}
        >
          {loading ? 'Loading…' : 'Generate'}
        </button>
      </div>

      {data && (
        <div className="space-y-4">
          {/* Header */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-6">
            <div>
              <p className="text-xs text-gray-500">Party</p>
              <p className="font-semibold text-gray-900">{data.party_name}</p>
              <p className="text-xs text-gray-400 capitalize">{data.party_type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Earnings</p>
              <p className="text-xl font-bold font-mono text-green-700">{formatDollars(data.total_amount_micros)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Settlement Runs</p>
              <p className="font-semibold text-gray-900">{data.run_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Line Items</p>
              <p className="font-semibold text-gray-900">{data.line_items.length}</p>
            </div>
          </div>

          {data.line_items.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-semibold text-gray-700">Statement</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-700">Track</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">Share</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">Amount</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-700">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.line_items.map((item, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{item.statement_id}</td>
                      <td className="px-4 py-2.5">
                        <div className="font-medium">{item.track_name}</div>
                        <div className="text-xs text-gray-400 font-mono">{item.track_id}</div>
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-500">{formatBps(item.share_bps)}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-medium">{formatDollars(item.amount_micros)}</td>
                      <td className="px-4 py-2.5 text-right text-gray-500 text-xs">
                        {new Date(item.settlement_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-gray-50 border-t-2 border-gray-300 font-semibold">
                    <td className="px-4 py-3" colSpan={3}>Total</td>
                    <td className="px-4 py-3 text-right font-mono">{formatDollars(data.total_amount_micros)}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No settlement records found for this party{data.from_date || data.to_date ? ' in the selected date range' : ''}.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Shared ───────────────────────────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
      Loading…
    </div>
  );
}

const inputClass =
  'border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent';

const primaryBtn =
  'bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors';
