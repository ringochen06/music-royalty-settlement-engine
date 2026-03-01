import { useEffect, useState } from 'react';
import {
  getIngestionJobs,
  createIngestionJob,
  getStreamingRecords,
} from '../api/client';
import type {
  IngestionJob,
  StreamingRecord,
  JobStatus,
} from '../types';
import { formatDollars } from '../types';

export default function Ingestion() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [records, setRecords] = useState<StreamingRecord[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [filter, setFilter] = useState<JobStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);

  // Upload form state
  const [formData, setFormData] = useState({
    statement_id: '',
    statement_date: '',
    file: null as File | null,
  });

  const loadJobs = async () => {
    try {
      setLoading(true);
      const result = await getIngestionJobs(currentPage, 10, filter || undefined);
      setJobs(result.items);
      setTotalJobs(result.total);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const loadRecords = async (jobId?: string) => {
    try {
      const result = await getStreamingRecords(1, 100, jobId);
      setRecords(result.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load records');
    }
  };

  useEffect(() => {
    loadJobs();
  }, [filter, currentPage]);

  useEffect(() => {
    if (selectedJobId) {
      loadRecords(selectedJobId);
    } else {
      setRecords([]);
    }
  }, [selectedJobId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, file: e.target.files[0] });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.file) {
      setError('Please select a CSV file');
      return;
    }

    try {
      const fileContent = await formData.file.text();
      await createIngestionJob({
        statement_id: formData.statement_id,
        file_name: formData.file.name,
        statement_date: formData.statement_date,
        file_content: fileContent,
      });
      setShowUploadForm(false);
      setFormData({ statement_id: '', statement_date: '', file: null });
      await loadJobs();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upload file');
    }
  };

  const getStatusBadge = (status: JobStatus) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 text-xs rounded font-medium ${colors[status]}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const totalPages = Math.ceil(totalJobs / 10);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Data Ingestion</h1>
        <button
          onClick={() => setShowUploadForm(true)}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-800 shadow-sm hover:shadow-md transition-all"
        >
          Upload CSV
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Upload Form Modal */}
      {showUploadForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Upload Statement CSV</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Statement ID</label>
                <input
                  type="text"
                  value={formData.statement_id}
                  onChange={(e) => setFormData({ ...formData, statement_id: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="STMT-2026-01"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Statement Date</label>
                <input
                  type="date"
                  value={formData.statement_date}
                  onChange={(e) => setFormData({ ...formData, statement_date: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">CSV File</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="w-full border rounded px-3 py-2"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Required columns: track_id, track_name, artist_name, streams, revenue_dollars
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowUploadForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-100 hover:border-gray-400 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gray-900 text-white rounded-lg font-semibold hover:bg-gray-800 transition-colors"
                >
                  Upload
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Filter and Stats */}
      <div className="flex items-center justify-between">
        <div>
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value as JobStatus | '');
              setCurrentPage(1);
            }}
            className="border rounded px-3 py-2"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="text-sm text-gray-600">
          Total Jobs: {totalJobs}
        </div>
      </div>

      {/* Jobs Table */}
      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Statement
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    File
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Records
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Revenue
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium">{job.statement_id}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(job.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm">{job.file_name}</td>
                    <td className="px-6 py-4 text-sm">
                      {new Date(job.statement_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(job.status)}</td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {job.total_records.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {formatDollars(job.total_revenue_micros)}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() =>
                          setSelectedJobId(selectedJobId === job.id ? '' : job.id)
                        }
                        className="text-gray-700 hover:text-gray-900 text-sm font-medium hover:underline transition-all"
                      >
                        {selectedJobId === job.id ? 'Hide' : 'View'} Records
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center space-x-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-3 py-1">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Records Table */}
      {selectedJobId && records.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="font-semibold">Streaming Records ({records.length})</h3>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Track
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Artist
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Streams
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Revenue
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {records.map((record) => (
                <tr key={record.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium">{record.track_name}</div>
                    <div className="text-xs text-gray-500">{record.track_id}</div>
                  </td>
                  <td className="px-6 py-4 text-sm">{record.artist_name}</td>
                  <td className="px-6 py-4 text-right font-mono text-sm">
                    {record.streams.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm">
                    {formatDollars(record.revenue_micros)}
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