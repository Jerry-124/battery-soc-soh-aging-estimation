from __future__ import annotations

from battery_estimation.models.ecm import ECMParameters


def capacity_soh(usable_capacity_ah: float, rated_capacity_ah: float) -> float:
    return 100.0 * usable_capacity_ah / rated_capacity_ah


def resistance_soh(estimated_r0: float, reference_r0: float) -> float:
    return 100.0 * reference_r0 / estimated_r0


def adapt_parameters(
    reference: ECMParameters,
    estimated_capacity_ah: float,
    estimated_resistance_factor: float,
) -> ECMParameters:
    """Bound slow health estimates before applying them to the fast observer."""
    capacity_factor = min(1.05, max(0.50, estimated_capacity_ah / reference.capacity_ah))
    resistance_factor = min(3.0, max(0.70, estimated_resistance_factor))
    return reference.aged(capacity_factor, resistance_factor)

