"""
Money and BasisPoints utilities.

All amounts stored in MICROS (1e-6 USD) to handle fractional cents like $0.0034/stream.
BPS (basis points) only for ratios: 1 BPS = 0.01%, 10000 BPS = 100%.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self


@dataclass(frozen=True)
class Money:
    """Immutable money in micros. 1 dollar = 1,000,000 micros."""

    micros: int

    def __post_init__(self) -> None:
        if not isinstance(self.micros, int):
            raise TypeError(f"micros must be int, got {type(self.micros).__name__}")

    @classmethod
    def from_dollars(cls, dollars: Decimal | str | float) -> Self:
        d = Decimal(str(dollars))
        return cls(micros=int(d * 1_000_000))

    @classmethod
    def from_cents(cls, cents: int) -> Self:
        return cls(micros=cents * 10_000)

    @classmethod
    def zero(cls) -> Self:
        return cls(micros=0)

    def to_dollars(self) -> Decimal:
        return Decimal(self.micros) / Decimal(1_000_000)

    def to_cents_rounded(self) -> int:
        """Round to cents. Only use for final payout."""
        cents_decimal = Decimal(self.micros) / Decimal(10_000)
        return int(cents_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(micros=self.micros + other.micros)

    def __sub__(self, other: Self) -> Self:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(micros=self.micros - other.micros)

    def __mul__(self, factor: int) -> Self:
        if not isinstance(factor, int):
            return NotImplemented
        return Money(micros=self.micros * factor)

    def __neg__(self) -> Self:
        return Money(micros=-self.micros)

    def __abs__(self) -> Self:
        return Money(micros=abs(self.micros))

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.micros < other.micros

    def __le__(self, other: Self) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.micros <= other.micros

    def __gt__(self, other: Self) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.micros > other.micros

    def __ge__(self, other: Self) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.micros >= other.micros

    def __repr__(self) -> str:
        return f"Money(${self.to_dollars():.6f})"

    def __str__(self) -> str:
        return f"${self.to_dollars():.2f}"


@dataclass(frozen=True)
class BasisPoints:
    """Basis points for ratios. 5000 BPS = 50%, max 10000 BPS = 100%."""

    value: int
    MAX_BPS: int = 10000

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError(f"BPS value must be int, got {type(self.value).__name__}")
        if self.value < 0:
            raise ValueError(f"BPS cannot be negative: {self.value}")
        if self.value > self.MAX_BPS:
            raise ValueError(f"BPS cannot exceed {self.MAX_BPS}: {self.value}")

    @classmethod
    def from_percentage(cls, percentage: Decimal | str | float) -> Self:
        d = Decimal(str(percentage))
        bps = int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(value=bps)

    @classmethod
    def from_decimal(cls, decimal_ratio: Decimal | str | float) -> Self:
        d = Decimal(str(decimal_ratio))
        bps = int((d * 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(value=bps)

    def to_percentage(self) -> Decimal:
        return Decimal(self.value) / Decimal(100)

    def to_decimal(self) -> Decimal:
        return Decimal(self.value) / Decimal(10000)

    def apply_to(self, money: Money) -> Money:
        """Apply this percentage to a Money amount."""
        result_micros = (money.micros * self.value) // 10000
        return Money(micros=result_micros)

    def __repr__(self) -> str:
        return f"BasisPoints({self.value} = {self.to_percentage():.2f}%)"

    def __str__(self) -> str:
        return f"{self.to_percentage():.2f}%"


def allocate_with_remainder(
    total: Money, splits: list[tuple[str, BasisPoints]]
) -> dict[str, Money]:
    """
    Allocate money by BPS splits using largest remainder method.
    Ensures total allocation equals original amount exactly.
    """
    if not splits:
        raise ValueError("At least one split required")

    total_bps = sum(s[1].value for s in splits)
    if total_bps != 10000:
        raise ValueError(f"Splits must total 10000 BPS (100%), got {total_bps}")

    allocations: dict[str, int] = {}
    remainders: list[tuple[str, Decimal]] = []
    allocated_micros = 0

    for party_id, bps in splits:
        exact = Decimal(total.micros * bps.value) / Decimal(10000)
        floor_micros = int(exact)
        remainder = exact - floor_micros
        allocations[party_id] = floor_micros
        remainders.append((party_id, remainder))
        allocated_micros += floor_micros

    # Distribute remaining micros by largest remainder
    remaining_micros = total.micros - allocated_micros
    remainders.sort(key=lambda x: x[1], reverse=True)
    for i in range(remaining_micros):
        party_id = remainders[i % len(remainders)][0]
        allocations[party_id] += 1

    return {party_id: Money(micros=micros) for party_id, micros in allocations.items()}


def validate_splits_total(splits: list[BasisPoints]) -> bool:
    """Check that splits total exactly 10000 BPS (100%)."""
    return sum(s.value for s in splits) == 10000
