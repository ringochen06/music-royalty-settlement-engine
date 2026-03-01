// ─── Ledger ──────────────────────────────────────────────────────────────────

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

// ─── Parties ─────────────────────────────────────────────────────────────────

export type PartyType =
  | 'artist'
  | 'label'
  | 'producer'
  | 'publisher'
  | 'distributor'
  | 'songwriter';

export type PartyStatus = 'active' | 'inactive' | 'suspended';

export interface Party {
  id: string;
  name: string;
  party_type: PartyType;
  status: PartyStatus;
  email: string | null;
  phone: string | null;
  external_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PartyList {
  items: Party[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreatePartyRequest {
  name: string;
  party_type: PartyType;
  email?: string;
  phone?: string;
  external_id?: string;
  notes?: string;
}

export interface UpdatePartyRequest {
  name?: string;
  status?: PartyStatus;
  email?: string;
  phone?: string;
  notes?: string;
}

// ─── Contracts ───────────────────────────────────────────────────────────────

export type ContractStatus = 'draft' | 'active' | 'expired' | 'terminated';

export interface ContractSplit {
  id: string;
  contract_id: string;
  party_id: string;
  share_bps: number;
  role: string | null;
  created_at: string;
}

export interface Contract {
  id: string;
  name: string;
  track_id: string;
  status: ContractStatus;
  effective_date: string;
  expiry_date: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  splits: ContractSplit[];
}

export interface ContractList {
  items: Contract[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ContractSplitRequest {
  party_id: string;
  share_bps: number;
  role?: string;
}

export interface CreateContractRequest {
  name: string;
  track_id: string;
  effective_date: string;
  expiry_date?: string;
  description?: string;
  splits: ContractSplitRequest[];
}

// ─── Ingestion ────────────────────────────────────────────────────────────────

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

// ─── Settlement ───────────────────────────────────────────────────────────────

export type SettlementStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface SettlementAllocation {
  id: string;
  line_id: string;
  party_id: string;
  share_bps: number;
  amount_micros: number;
}

export interface SettlementLine {
  id: string;
  run_id: string;
  track_id: string;
  track_name: string;
  contract_id: string | null;
  gross_micros: number;
  platform_fee_micros: number;
  net_micros: number;
  is_unmatched: boolean;
  journal_entry_id: string | null;
  created_at: string;
  allocations: SettlementAllocation[];
}

export interface SettlementRun {
  id: string;
  job_id: string;
  statement_id: string;
  status: SettlementStatus;
  platform_fee_bps: number;
  total_tracks: number;
  matched_tracks: number;
  unmatched_tracks: number;
  total_gross_micros: number;
  total_platform_fee_micros: number;
  total_net_micros: number;
  total_unmatched_micros: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  lines: SettlementLine[];
}

export interface SettlementRunList {
  items: SettlementRun[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SettlementLineList {
  items: SettlementLine[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateSettlementRunRequest {
  job_id: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

export const toDollars = (micros: number): number => micros / 1_000_000;
export const toMicros = (dollars: number): number => Math.round(dollars * 1_000_000);
export const formatDollars = (micros: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(
    toDollars(micros)
  );
export const formatBps = (bps: number): string => `${(bps / 100).toFixed(2)}%`;
