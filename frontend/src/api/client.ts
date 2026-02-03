import type {
  Account,
  AccountBalance,
  AccountType,
  CreateAccountRequest,
  CreateJournalEntryRequest,
  JournalEntry,
  JournalEntryList,
  JournalStatus,
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
