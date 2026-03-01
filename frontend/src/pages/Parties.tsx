import { useEffect, useState } from 'react';
import { getParties, createParty, updateParty } from '../api/client';
import type { Party, PartyType, PartyStatus, CreatePartyRequest } from '../types';

const PARTY_TYPE_LABELS: Record<PartyType, string> = {
  artist: 'Artist',
  label: 'Label',
  producer: 'Producer',
  publisher: 'Publisher',
  distributor: 'Distributor',
  songwriter: 'Songwriter',
};

const PARTY_TYPE_COLORS: Record<PartyType, string> = {
  artist: 'bg-purple-100 text-purple-800',
  label: 'bg-blue-100 text-blue-800',
  producer: 'bg-indigo-100 text-indigo-800',
  publisher: 'bg-cyan-100 text-cyan-800',
  distributor: 'bg-teal-100 text-teal-800',
  songwriter: 'bg-violet-100 text-violet-800',
};

const STATUS_COLORS: Record<PartyStatus, string> = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-600',
  suspended: 'bg-red-100 text-red-800',
};

const EMPTY_FORM: CreatePartyRequest = {
  name: '',
  party_type: 'artist',
  email: '',
  phone: '',
  external_id: '',
  notes: '',
};

export default function Parties() {
  const [parties, setParties] = useState<Party[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<PartyType | ''>('');
  const [statusFilter, setStatusFilter] = useState<PartyStatus | ''>('');
  const [nameSearch, setNameSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingParty, setEditingParty] = useState<Party | null>(null);
  const [formData, setFormData] = useState<CreatePartyRequest>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const PAGE_SIZE = 20;

  const load = async () => {
    try {
      setLoading(true);
      const result = await getParties(
        page,
        PAGE_SIZE,
        typeFilter || undefined,
        statusFilter || undefined,
        nameSearch || undefined
      );
      setParties(result.items);
      setTotal(result.total);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load parties');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, typeFilter, statusFilter]);

  // Debounce name search
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(); }, 300);
    return () => clearTimeout(t);
  }, [nameSearch]);

  const openCreate = () => {
    setFormData(EMPTY_FORM);
    setShowCreateModal(true);
  };

  const openEdit = (party: Party) => {
    setEditingParty(party);
    setFormData({
      name: party.name,
      party_type: party.party_type,
      email: party.email ?? '',
      phone: party.phone ?? '',
      external_id: party.external_id ?? '',
      notes: party.notes ?? '',
    });
    setShowEditModal(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createParty({
        ...formData,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        external_id: formData.external_id || undefined,
        notes: formData.notes || undefined,
      });
      setShowCreateModal(false);
      setPage(1);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create party');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingParty) return;
    setSubmitting(true);
    try {
      await updateParty(editingParty.id, {
        name: formData.name,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        notes: formData.notes || undefined,
      });
      setShowEditModal(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update party');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (party: Party, status: PartyStatus) => {
    try {
      await updateParty(party.id, { status });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update status');
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Parties</h1>
          <p className="text-sm text-gray-500 mt-0.5">Music industry participants</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
        >
          + New Party
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
          placeholder="Search by name…"
          value={nameSearch}
          onChange={(e) => setNameSearch(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value as PartyType | ''); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          <option value="">All Types</option>
          {Object.entries(PARTY_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as PartyStatus | ''); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
        <span className="text-sm text-gray-500 ml-auto">{total} parties</span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">Loading…</div>
      ) : parties.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No parties found.{' '}
          <button onClick={openCreate} className="text-gray-900 font-semibold hover:underline">
            Add one?
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Name', 'Type', 'Status', 'Email', 'External ID', 'Actions'].map((h) => (
                  <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {parties.map((party) => (
                <tr key={party.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{party.name}</div>
                    {party.notes && (
                      <div className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">{party.notes}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${PARTY_TYPE_COLORS[party.party_type]}`}>
                      {PARTY_TYPE_LABELS[party.party_type]}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[party.status]}`}>
                      {party.status.charAt(0).toUpperCase() + party.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{party.email ?? '—'}</td>
                  <td className="px-6 py-4 text-sm font-mono text-gray-500">{party.external_id ?? '—'}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => openEdit(party)}
                        className="text-sm text-gray-600 hover:text-gray-900 font-medium"
                      >
                        Edit
                      </button>
                      {party.status === 'active' && (
                        <button
                          onClick={() => handleStatusChange(party, 'suspended')}
                          className="text-sm text-red-500 hover:text-red-700 font-medium"
                        >
                          Suspend
                        </button>
                      )}
                      {party.status === 'suspended' && (
                        <button
                          onClick={() => handleStatusChange(party, 'active')}
                          className="text-sm text-green-600 hover:text-green-800 font-medium"
                        >
                          Reactivate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
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
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <Modal title="New Party" onClose={() => setShowCreateModal(false)}>
          <PartyForm
            data={formData}
            onChange={setFormData}
            onSubmit={handleCreate}
            onCancel={() => setShowCreateModal(false)}
            submitLabel="Create Party"
            submitting={submitting}
            showTypeField
          />
        </Modal>
      )}

      {/* Edit Modal */}
      {showEditModal && editingParty && (
        <Modal title={`Edit — ${editingParty.name}`} onClose={() => setShowEditModal(false)}>
          <PartyForm
            data={formData}
            onChange={setFormData}
            onSubmit={handleUpdate}
            onCancel={() => setShowEditModal(false)}
            submitLabel="Save Changes"
            submitting={submitting}
            showTypeField={false}
          />
        </Modal>
      )}
    </div>
  );
}

// ─── Shared sub-components ────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function PartyForm({
  data,
  onChange,
  onSubmit,
  onCancel,
  submitLabel,
  submitting,
  showTypeField,
}: {
  data: CreatePartyRequest;
  onChange: (d: CreatePartyRequest) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  submitLabel: string;
  submitting: boolean;
  showTypeField: boolean;
}) {
  const field = (key: keyof CreatePartyRequest) => ({
    value: (data[key] as string) ?? '',
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      onChange({ ...data, [key]: e.target.value }),
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="Name" required>
        <input type="text" {...field('name')} className={inputCls} required />
      </Field>

      {showTypeField && (
        <Field label="Type" required>
          <select {...field('party_type')} className={inputCls}>
            {Object.entries(PARTY_TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </Field>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Field label="Email">
          <input type="email" {...field('email')} className={inputCls} />
        </Field>
        <Field label="Phone">
          <input type="tel" {...field('phone')} className={inputCls} />
        </Field>
      </div>

      <Field label="External ID">
        <input type="text" {...field('external_id')} placeholder="Third-party system ID" className={inputCls} />
      </Field>

      <Field label="Notes">
        <textarea
          value={(data.notes as string) ?? ''}
          onChange={(e) => onChange({ ...data, notes: e.target.value })}
          rows={2}
          className={inputCls}
        />
      </Field>

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className={cancelBtnCls}>Cancel</button>
        <button type="submit" disabled={submitting} className={primaryBtnCls}>
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900';
const primaryBtnCls = 'px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors disabled:opacity-50';
const cancelBtnCls = 'px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors';
