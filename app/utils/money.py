from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    """Normalise any numeric input to a 2-dp Decimal (consistent financial calculations)."""
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def pct(part, whole) -> float:
    whole = Decimal(str(whole or 0))
    if whole <= 0:
        return 0.0
    return float((Decimal(str(part or 0)) / whole * 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))
