export type AccountType = 'asset' | 'liability' | 'revenue' | 'expense';
export type NormalBalance = 'debit' | 'credit';
export type JournalStatus = 'pending' | 'posted' | 'reversed';

export interface Account {
  id: string;
  account_number: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  party_id: string | null;
  is_system_account: boolean;
  description: string | null;
  created_at: string;
}

export interface AccountBalance {
  account_id: string;
  account_number: string;
  account_name: string;
  balance_micros: number;
  balance_dollars: number;
  normal_balance: NormalBalance;
}

export interface PostingLine {
  id: string;
  account_id: string;
  amount_micros: number;
  is_debit: boolean;
  memo: string | null;
  sequence_number: number;
}

export interface JournalEntry {
  id: string;
  occurred_at: string;
  created_at: string;
  description: string;
  reference_type: string | null;
  reference_id: string | null;
  status: JournalStatus;
  posted_at: string | null;
  postings: PostingLine[];
}

export interface JournalEntryList {
  items: JournalEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TrialBalanceLineItem {
  account_number: string;
  account_name: string;
  account_type: AccountType;
  debit_balance_micros: number;
  credit_balance_micros: number;
}

export interface TrialBalance {
  as_of_date: string;
  line_items: TrialBalanceLineItem[];
  total_debits_micros: number;
  total_credits_micros: number;
  is_balanced: boolean;
}

// Request types
export interface CreateAccountRequest {
  account_number: string;
  name: string;
  account_type: AccountType;
  description?: string;
}

export interface CreatePostingRequest {
  account_id: string;
  amount_micros: number;
  is_debit: boolean;
  memo?: string;
}

export interface CreateJournalEntryRequest {
  occurred_at: string;
  description: string;
  postings: CreatePostingRequest[];
}

// Ingestion types
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface IngestionJob {
  id: string;
  statement_id: string;
  file_hash: string;
  file_name: string;
  statement_date: string;
  status: JobStatus;
  total_records: number;
  total_revenue_micros: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface StreamingRecord {
  id: string;
  job_id: string;
  track_id: string;
  track_name: string;
  artist_name: string;
  streams: number;
  revenue_micros: number;
  statement_date: string;
  created_at: string;
}

export interface IngestionJobList {
  items: IngestionJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StreamingRecordList {
  items: StreamingRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateIngestionJobRequest {
  statement_id: string;
  file_name: string;
  statement_date: string;
  file_content: string;
}

// Helpers
export const toDollars = (micros: number): number => micros / 1_000_000;
export const toMicros = (dollars: number): number => Math.round(dollars * 1_000_000);
export const formatDollars = (micros: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(toDollars(micros));
};
