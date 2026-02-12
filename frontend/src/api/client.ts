import type {
  Account,
  AccountBalance,
  AccountType,
  CreateAccountRequest,
  CreateIngestionJobRequest,
  CreateJournalEntryRequest,
  IngestionJob,
  IngestionJobList,
  JobStatus,
  JournalEntry,
  JournalEntryList,
  JournalStatus,
  StreamingRecord,
  StreamingRecordList,
  TrialBalance,
} from '../types';

const API_BASE = '/api/v1/ledger';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return res.json();
}

// Accounts
export async function getAccounts(type?: AccountType): Promise<Account[]> {
  const params = type ? `?account_type=${type}` : '';
  return request<Account[]>(`${API_BASE}/accounts${params}`);
}

export async function getAccount(id: string): Promise<Account> {
  return request<Account>(`${API_BASE}/accounts/${id}`);
}

export async function getAccountBalance(id: string): Promise<AccountBalance> {
  return request<AccountBalance>(`${API_BASE}/accounts/${id}/balance`);
}

export async function createAccount(data: CreateAccountRequest): Promise<Account> {
  return request<Account>(`${API_BASE}/accounts`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function seedAccounts(): Promise<Account[]> {
  return request<Account[]>(`${API_BASE}/accounts/seed`, { method: 'POST' });
}

// Journal Entries
export async function getJournalEntries(
  page = 1,
  pageSize = 20,
  status?: JournalStatus
): Promise<JournalEntryList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.set('status', status);
  return request<JournalEntryList>(`${API_BASE}/journal-entries?${params}`);
}

export async function getJournalEntry(id: string): Promise<JournalEntry> {
  return request<JournalEntry>(`${API_BASE}/journal-entries/${id}`);
}

export async function createJournalEntry(data: CreateJournalEntryRequest): Promise<JournalEntry> {
  return request<JournalEntry>(`${API_BASE}/journal-entries`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function reverseJournalEntry(id: string): Promise<JournalEntry> {
  return request<JournalEntry>(`${API_BASE}/journal-entries/${id}/reverse`, {
    method: 'POST',
  });
}

// Reports
export async function getTrialBalance(): Promise<TrialBalance> {
  return request<TrialBalance>(`${API_BASE}/trial-balance`);
}

// Ingestion
const INGESTION_API_BASE = '/api/v1/ingestion';

export async function getIngestionJobs(
  page = 1,
  pageSize = 20,
  status?: JobStatus
): Promise<IngestionJobList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.set('status', status);
  return request<IngestionJobList>(`${INGESTION_API_BASE}/jobs?${params}`);
}

export async function getIngestionJob(id: string): Promise<IngestionJob> {
  return request<IngestionJob>(`${INGESTION_API_BASE}/jobs/${id}`);
}

export async function getIngestionJobByStatementId(statementId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`${INGESTION_API_BASE}/jobs/statement/${statementId}`);
}

export async function createIngestionJob(data: CreateIngestionJobRequest): Promise<IngestionJob> {
  return request<IngestionJob>(`${INGESTION_API_BASE}/jobs`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getStreamingRecords(
  page = 1,
  pageSize = 20,
  jobId?: string,
  trackId?: string
): Promise<StreamingRecordList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (jobId) params.set('job_id', jobId);
  if (trackId) params.set('track_id', trackId);
  return request<StreamingRecordList>(`${INGESTION_API_BASE}/records?${params}`);
}

export async function getStreamingRecord(id: string): Promise<StreamingRecord> {
  return request<StreamingRecord>(`${INGESTION_API_BASE}/records/${id}`);
}
