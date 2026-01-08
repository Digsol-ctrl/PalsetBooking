from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings


class PricingService:
    """PricingService calculates fare breakdown according to business rules.

    Rules summary (implemented):
    - Distances below 13km are charged at the 13-15km bracket ($25) as a minimum.
    - Distance brackets: 13-15 ($25), 16-20 ($30), 21-25 ($35), 26-35 ($40)
    - For distance >35km: price = $40 + 1.30 * (distance - 35)
    - Base fare covers up to 3 adults. Extra adults (>3) pay $10 each
    - Kids seated pay 50% of an adult share (see calculation)
    - Kids carried are free
    - Luggage is $5 per bag

    Note on kids calculation: we treat the "adult share" for a seated kid as
    50% of the per-adult share of the BASE distance price (distance price / 3).
    This keeps the logic deterministic and simple. Document any changes with
    business if this should instead be 50% of the full adult price.
    """

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate(cls, distance_km: float, num_adults: int = 1, num_kids_seated: int = 0, num_kids_carried: int = 0, luggage_count: int = 0) -> dict:
        if distance_km is None:
            raise ValueError("distance_km is required")
        if num_adults < 1:
            raise ValueError("At least one adult is required")
        if num_kids_seated < 0 or num_kids_carried < 0 or luggage_count < 0:
            raise ValueError("Counts cannot be negative")

        distance = Decimal(str(distance_km))
        pricing_cfg = settings.PRICING

        # Determine base distance price
        base_price = None
        # Enforce minimum distance bracket (13 km)
        effective_distance = max(distance, Decimal(str(pricing_cfg.get("MIN_DISTANCE_KM", 13.0))))

        # Check defined brackets
        for bracket in pricing_cfg.get("BRACKETS", []):
            if Decimal(bracket["min"]) <= effective_distance <= Decimal(bracket["max"]):
                base_price = Decimal(str(bracket["price"]))
                break

        if base_price is None:
            # If above 35, use special rule
            if effective_distance > Decimal("35"):
                base_35 = Decimal("40.0")
                per_km = Decimal(str(pricing_cfg.get("ABOVE_35_PER_KM", 1.3)))
                extra_km = effective_distance - Decimal("35")
                base_price = base_35 + (per_km * extra_km)
            else:
                # Fallback (shouldn't hit because of brackets): use lowest bracket
                base_price = Decimal(str(pricing_cfg.get("BRACKETS")[0]["price"]))

        # Extra adults
        extra_adults = max(0, num_adults - 3)
        extra_adults_fee = Decimal(str(pricing_cfg.get("EXTRA_ADULT_FEE", 10.0))) * extra_adults

        # Kids seated: 50% of adult share of base distance price (base_price / 3 * factor)
        adult_share = (base_price / Decimal("3")) if Decimal("3") > 0 else base_price
        kid_factor = Decimal(str(pricing_cfg.get("KID_SEATED_FACTOR", 0.5)))
        kids_seated_fee = adult_share * kid_factor * Decimal(num_kids_seated)

        # Luggage
        luggage_fee = Decimal(str(pricing_cfg.get("LUGGAGE_FEE", 5.0))) * Decimal(luggage_count)

        # Sum up
        subtotal = base_price + extra_adults_fee + kids_seated_fee + luggage_fee
        total = cls._round(subtotal)

        breakdown = {
            "distance_km": float(distance),
            "effective_distance_km": float(effective_distance),
            "base_distance_price": float(cls._round(base_price)),
            "extra_adults": int(extra_adults),
            "extra_adults_fee": float(cls._round(extra_adults_fee)),
            "kids_seated": int(num_kids_seated),
            "kids_seated_fee": float(cls._round(kids_seated_fee)),
            "kids_carried": int(num_kids_carried),
            "luggage_count": int(luggage_count),
            "luggage_fee": float(cls._round(luggage_fee)),
            "subtotal": float(cls._round(subtotal)),
            "total": float(total),
        }

        return breakdown
