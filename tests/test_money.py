"""Tests for Money and BasisPoints."""

from decimal import Decimal

import pytest

from src.common.money import (
    BasisPoints,
    Money,
    allocate_with_remainder,
    validate_splits_total,
)


class TestMoney:

    def test_from_dollars(self):
        assert Money.from_dollars("100").micros == 100_000_000
        assert Money.from_dollars("10.50").micros == 10_500_000
        assert Money.from_dollars("0.0034").micros == 3_400

    def test_from_cents(self):
        assert Money.from_cents(100).micros == 1_000_000

    def test_zero(self):
        assert Money.zero().micros == 0

    def test_conversions(self):
        m = Money(micros=1_234_567)
        assert m.to_dollars() == Decimal("1.234567")
        assert m.to_cents_rounded() == 123

        m2 = Money(micros=1_235_000)
        assert m2.to_cents_rounded() == 124

    def test_arithmetic(self):
        m1 = Money.from_dollars("10.00")
        m2 = Money.from_dollars("3.50")

        assert (m1 + m2).to_dollars() == Decimal("13.5")
        assert (m1 - m2).to_dollars() == Decimal("6.5")
        assert (m1 * 3).to_dollars() == Decimal("30.0")
        assert (-m1).micros == -10_000_000
        assert abs(Money(micros=-5_000_000)).micros == 5_000_000

    def test_comparisons(self):
        small = Money.from_dollars("5.00")
        large = Money.from_dollars("10.00")
        same = Money(micros=5_000_000)

        assert small < large
        assert large > small
        assert small == same

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            Money(micros=1.5)  # type: ignore


class TestBasisPoints:

    def test_creation(self):
        assert BasisPoints.from_percentage(50.0).value == 5000
        assert BasisPoints.from_percentage("33.33").value == 3333
        assert BasisPoints.from_decimal(0.5).value == 5000

    def test_conversions(self):
        bps = BasisPoints(value=5000)
        assert bps.to_percentage() == Decimal("50.00")
        assert bps.to_decimal() == Decimal("0.5")

    def test_apply_to_money(self):
        money = Money.from_dollars("100.00")
        assert BasisPoints(5000).apply_to(money).to_dollars() == Decimal("50.0")
        assert BasisPoints(1500).apply_to(money).to_dollars() == Decimal("15.0")

        stream = Money.from_dollars("0.0034")
        result = BasisPoints(5000).apply_to(stream)
        assert result.micros == 1700

    def test_validation(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            BasisPoints(value=-100)
        with pytest.raises(ValueError, match="cannot exceed"):
            BasisPoints(value=10001)
        assert BasisPoints(value=10000).value == 10000


class TestAllocateWithRemainder:

    def test_even_split(self):
        total = Money.from_dollars("100.00")
        splits = [("a", BasisPoints(5000)), ("b", BasisPoints(5000))]
        result = allocate_with_remainder(total, splits)

        assert result["a"].to_dollars() == Decimal("50.0")
        assert result["b"].to_dollars() == Decimal("50.0")
        assert sum(m.micros for m in result.values()) == total.micros

    def test_three_way_split(self):
        total = Money.from_dollars("100.00")
        splits = [
            ("artist", BasisPoints(5000)),
            ("label", BasisPoints(3500)),
            ("producer", BasisPoints(1500)),
        ]
        result = allocate_with_remainder(total, splits)

        assert result["artist"].to_dollars() == Decimal("50.0")
        assert result["label"].to_dollars() == Decimal("35.0")
        assert result["producer"].to_dollars() == Decimal("15.0")
        assert sum(m.micros for m in result.values()) == total.micros

    def test_uneven_split_no_lost_micros(self):
        total = Money.from_dollars("1.00")
        splits = [
            ("a", BasisPoints(3334)),
            ("b", BasisPoints(3333)),
            ("c", BasisPoints(3333)),
        ]
        result = allocate_with_remainder(total, splits)
        assert sum(m.micros for m in result.values()) == total.micros

    def test_validation(self):
        total = Money.from_dollars("100.00")

        with pytest.raises(ValueError, match="must total 10000 BPS"):
            allocate_with_remainder(total, [("a", BasisPoints(5000))])

        with pytest.raises(ValueError, match="At least one split"):
            allocate_with_remainder(total, [])


class TestValidateSplitsTotal:

    def test_validation(self):
        valid = [BasisPoints(5000), BasisPoints(3000), BasisPoints(2000)]
        assert validate_splits_total(valid) is True

        invalid = [BasisPoints(5000), BasisPoints(3000)]
        assert validate_splits_total(invalid) is False
