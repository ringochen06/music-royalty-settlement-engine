"""Custom exceptions."""


class RoyaltyEngineError(Exception):
    """Base exception."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LedgerBalanceError(RoyaltyEngineError):
    """Journal entry doesn't balance (debits != credits)."""

    def __init__(self, message: str, debits: int = 0, credits: int = 0):
        details = {
            "debits_micros": debits,
            "credits_micros": credits,
            "difference_micros": abs(debits - credits),
        }
        super().__init__(message, details)
        self.debits = debits
        self.credits = credits


class InvalidSplitError(RoyaltyEngineError):
    """Revenue splits don't total 100%."""

    def __init__(self, message: str, total_bps: int = 0, expected_bps: int = 10000):
        details = {
            "total_bps": total_bps,
            "expected_bps": expected_bps,
            "difference_bps": abs(total_bps - expected_bps),
        }
        super().__init__(message, details)
        self.total_bps = total_bps
        self.expected_bps = expected_bps


class DuplicateIngestionError(RoyaltyEngineError):
    """Duplicate file or statement (idempotency check)."""

    def __init__(self, message: str, statement_id: str, existing_job_id: str | None = None):
        details = {"statement_id": statement_id, "existing_job_id": existing_job_id}
        super().__init__(message, details)
        self.statement_id = statement_id
        self.existing_job_id = existing_job_id


class DuplicateSettlementError(RoyaltyEngineError):
    """Duplicate settlement."""

    def __init__(self, message: str, statement_id: str, existing_run_id: str | None = None):
        details = {"statement_id": statement_id, "existing_run_id": existing_run_id}
        super().__init__(message, details)
        self.statement_id = statement_id
        self.existing_run_id = existing_run_id


class ContractNotFoundError(RoyaltyEngineError):
    def __init__(self, contract_id: str):
        super().__init__(f"Contract not found: {contract_id}", {"contract_id": contract_id})
        self.contract_id = contract_id


class PartyNotFoundError(RoyaltyEngineError):
    def __init__(self, party_id: str):
        super().__init__(f"Party not found: {party_id}", {"party_id": party_id})
        self.party_id = party_id


class AccountNotFoundError(RoyaltyEngineError):
    def __init__(self, account_id: str | None = None, account_number: str | None = None):
        if account_id:
            message = f"Account not found: {account_id}"
            details = {"account_id": account_id}
        elif account_number:
            message = f"Account not found: {account_number}"
            details = {"account_number": account_number}
        else:
            message = "Account not found"
            details = {}
        super().__init__(message, details)
        self.account_id = account_id
        self.account_number = account_number


class IngestionValidationError(RoyaltyEngineError):
    """CSV validation failed."""

    def __init__(self, message: str, errors: list[dict] | None = None):
        details = {"error_count": len(errors) if errors else 0, "errors": errors or []}
        super().__init__(message, details)
        self.errors = errors or []
