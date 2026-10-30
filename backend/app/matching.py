from dataclasses import dataclass

from app.models.donation import Donation
from app.models.need import Need


CONDITION_RANK = {
    "new": 5,
    "like new": 5,
    "excellent": 4,
    "good": 3,
    "fair": 2,
    "usable": 1,
    "any": 0,
}


@dataclass(frozen=True)
class MatchEvaluation:
    score: int
    factors: dict[str, str | int | bool]
    explanation: str


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _condition_meets(donation: str, need: str) -> bool:
    donation_rank = CONDITION_RANK.get(_normalise(donation), 0)
    need_rank = CONDITION_RANK.get(_normalise(need), 0)
    return donation_rank >= need_rank


def evaluate_match(need: Need, donation: Donation) -> MatchEvaluation | None:
    remaining = donation.quantity_available - donation.quantity_reserved
    category_matches = _normalise(need.category) == _normalise(donation.category)
    condition_matches = _condition_meets(donation.condition, need.condition)
    same_city = _normalise(need.city) == _normalise(donation.city)
    same_region = _normalise(need.region) == _normalise(donation.region)
    location_compatible = same_region or donation.delivery_available or donation.pickup_available

    if not category_matches or not condition_matches or remaining <= 0 or not location_compatible:
        return None

    factors: dict[str, str | int | bool] = {
        "category_match": category_matches,
        "condition_match": condition_matches,
        "quantity_remaining": remaining,
        "same_city": same_city,
        "same_region": same_region,
        "delivery_available": donation.delivery_available,
        "pickup_available": donation.pickup_available,
    }
    score = 40
    reasons = ["same category", "condition meets the need"]
    if same_city:
        score += 25
        reasons.append("same city")
    elif same_region:
        score += 15
        reasons.append("same region")
    elif donation.delivery_available or donation.pickup_available:
        score += 5
        reasons.append("pickup or delivery is available")
    if remaining >= need.quantity_requested - need.quantity_fulfilled:
        score += 15
        reasons.append("enough inventory for the remaining request")
    else:
        score += 5
        reasons.append("partial inventory is available")
    if _normalise(need.urgency) in {"urgent", "high"}:
        score += 5
        reasons.append(f"{need.urgency} urgency")
    if _normalise(need.priority) in {"urgent", "high"}:
        score += 5
        reasons.append(f"{need.priority} priority")

    return MatchEvaluation(score=min(score, 100), factors=factors, explanation="; ".join(reasons) + ".")
