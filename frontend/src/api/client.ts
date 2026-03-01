import type {
  Account,
  AccountBalance,
  AccountType,
  Contract,
  ContractList,
  ContractStatus,
  CreateAccountRequest,
  CreateContractRequest,
  CreateIngestionJobRequest,
  CreateJournalEntryRequest,
  CreatePartyRequest,
  CreateSettlementRunRequest,
  IngestionJob,
  IngestionJobList,
  JobStatus,
  JournalEntry,
  JournalEntryList,
  JournalStatus,
  Party,
  PartyList,
  PartyStatus,
  PartyType,
  SettlementLineList,
  SettlementRun,
  SettlementRunList,
  SettlementStatus,
  StreamingRecord,
  StreamingRecordList,
  TrialBalance,
  UpdatePartyRequest,
} from '../types';

// ─── Base ─────────────────────────────────────────────────────────────────────

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

// ─── Ledger ───────────────────────────────────────────────────────────────────

const LEDGER = '/api/v1/ledger';

export async function getAccounts(type?: AccountType): Promise<Account[]> {
  const params = type ? `?account_type=${type}` : '';
  return request<Account[]>(`${LEDGER}/accounts${params}`);
}

export async function getAccount(id: string): Promise<Account> {
  return request<Account>(`${LEDGER}/accounts/${id}`);
}

export async function getAccountBalance(id: string): Promise<AccountBalance> {
  return request<AccountBalance>(`${LEDGER}/accounts/${id}/balance`);
}

export async function createAccount(data: CreateAccountRequest): Promise<Account> {
  return request<Account>(`${LEDGER}/accounts`, { method: 'POST', body: JSON.stringify(data) });
}

export async function seedAccounts(): Promise<Account[]> {
  return request<Account[]>(`${LEDGER}/accounts/seed`, { method: 'POST' });
}

export async function getJournalEntries(
  page = 1,
  pageSize = 20,
  status?: JournalStatus
): Promise<JournalEntryList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  return request<JournalEntryList>(`${LEDGER}/journal-entries?${params}`);
}

export async function getJournalEntry(id: string): Promise<JournalEntry> {
  return request<JournalEntry>(`${LEDGER}/journal-entries/${id}`);
}

export async function createJournalEntry(data: CreateJournalEntryRequest): Promise<JournalEntry> {
  return request<JournalEntry>(`${LEDGER}/journal-entries`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function reverseJournalEntry(id: string): Promise<JournalEntry> {
  return request<JournalEntry>(`${LEDGER}/journal-entries/${id}/reverse`, { method: 'POST' });
}

export async function getTrialBalance(): Promise<TrialBalance> {
  return request<TrialBalance>(`${LEDGER}/trial-balance`);
}

// ─── Parties ──────────────────────────────────────────────────────────────────

const PARTIES = '/api/v1/parties';

export async function getParties(
  page = 1,
  pageSize = 50,
  partyType?: PartyType,
  status?: PartyStatus,
  name?: string
): Promise<PartyList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (partyType) params.set('party_type', partyType);
  if (status) params.set('status', status);
  if (name) params.set('name', name);
  return request<PartyList>(`${PARTIES}?${params}`);
}

export async function getParty(id: string): Promise<Party> {
  return request<Party>(`${PARTIES}/${id}`);
}

export async function createParty(data: CreatePartyRequest): Promise<Party> {
  return request<Party>(PARTIES, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateParty(id: string, data: UpdatePartyRequest): Promise<Party> {
  return request<Party>(`${PARTIES}/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

// ─── Contracts ────────────────────────────────────────────────────────────────

const CONTRACTS = '/api/v1/contracts';

export async function getContracts(
  page = 1,
  pageSize = 50,
  status?: ContractStatus,
  trackId?: string
): Promise<ContractList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  if (trackId) params.set('track_id', trackId);
  return request<ContractList>(`${CONTRACTS}?${params}`);
}

export async function getContract(id: string): Promise<Contract> {
  return request<Contract>(`${CONTRACTS}/${id}`);
}

export async function createContract(data: CreateContractRequest): Promise<Contract> {
  return request<Contract>(CONTRACTS, { method: 'POST', body: JSON.stringify(data) });
}

export async function activateContract(id: string): Promise<Contract> {
  return request<Contract>(`${CONTRACTS}/${id}/activate`, { method: 'POST' });
}

export async function terminateContract(id: string): Promise<Contract> {
  return request<Contract>(`${CONTRACTS}/${id}/terminate`, { method: 'POST' });
}

// ─── Ingestion ────────────────────────────────────────────────────────────────

const INGESTION = '/api/v1/ingestion';

export async function getIngestionJobs(
  page = 1,
  pageSize = 20,
  status?: JobStatus
): Promise<IngestionJobList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  return request<IngestionJobList>(`${INGESTION}/jobs?${params}`);
}

export async function getIngestionJob(id: string): Promise<IngestionJob> {
  return request<IngestionJob>(`${INGESTION}/jobs/${id}`);
}

export async function createIngestionJob(data: CreateIngestionJobRequest): Promise<IngestionJob> {
  return request<IngestionJob>(`${INGESTION}/jobs`, {
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
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (jobId) params.set('job_id', jobId);
  if (trackId) params.set('track_id', trackId);
  return request<StreamingRecordList>(`${INGESTION}/records?${params}`);
}

export async function getStreamingRecord(id: string): Promise<StreamingRecord> {
  return request<StreamingRecord>(`${INGESTION}/records/${id}`);
}

// ─── Settlement ───────────────────────────────────────────────────────────────

const SETTLEMENTS = '/api/v1/settlements';

export async function getSettlementRuns(
  page = 1,
  pageSize = 20,
  status?: SettlementStatus
): Promise<SettlementRunList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  return request<SettlementRunList>(`${SETTLEMENTS}/runs?${params}`);
}

export async function getSettlementRun(id: string): Promise<SettlementRun> {
  return request<SettlementRun>(`${SETTLEMENTS}/runs/${id}`);
}

export async function createSettlementRun(
  data: CreateSettlementRunRequest
): Promise<SettlementRun> {
  return request<SettlementRun>(`${SETTLEMENTS}/runs`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getSettlementLines(
  runId: string,
  page = 1,
  pageSize = 50
): Promise<SettlementLineList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return request<SettlementLineList>(`${SETTLEMENTS}/runs/${runId}/lines?${params}`);
}
