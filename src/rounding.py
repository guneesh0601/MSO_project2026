"""Postoptimal rounding: takes a raw solved x (messy decimals) and rounds
it to a clean grid (e.g. nearest 1%), while guaranteeing the rounded
values still sum to exactly 1.0.

Uses the 'largest remainder' method (the same family as the Balinski-Young
apportionment method the paper references) -- NOT the bank's own
undisclosed rounding algorithm (Avriel 2003), which was never published.
This is a clearly documented, standard substitute (see Reproduction_Plan.md,
Section 8).
"""

import numpy as np


def largest_remainder_round(x: np.ndarray, grid: float = 0.01) -> np.ndarray:
    """Round each x_i to the nearest multiple of `grid`, adjusting the
    largest remainders so the total still sums to exactly 1.0.
    """
    n_units_total = round(1.0 / grid)
    scaled = x / grid
    floor_units = np.floor(scaled).astype(int)
    remainders = scaled - floor_units

    shortfall = n_units_total - floor_units.sum()
    order = np.argsort(-remainders)  # largest remainder first

    result_units = floor_units.copy()
    for i in range(shortfall):
        result_units[order[i]] += 1

    rounded = result_units * grid
    assert abs(rounded.sum() - 1.0) < 1e-9, "rounded weights must sum to 1"
    return rounded
