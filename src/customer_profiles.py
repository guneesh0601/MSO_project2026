"""Generates the finite list of customer profiles we test ('Loop A'), and
translates each one into the concrete settings frontier_builder.py needs
(which benchmark to use, which limits apply).

One profile per benchmark. The paper (p. 49) builds a frontier for each
combination of customer parameters (horizon, benchmark, liquidity level, ...);
the risk level is not one of them. It picks WHICH point of a frontier to
recommend (engine.frontier_position), so it does not multiply the profiles.
Horizon, objective and the liquidity/currency levels are held at reasonable
defaults for this reproduction.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def build_profiles() -> list[dict]:
    return [
        {
            "profile_id": benchmark,
            "benchmark": benchmark,
            "equity_cap": None,          # no equity limit: the risk level does not constrain
            "liquidity_cap": config.LIQUIDITY_CAP_DEFAULT,
            "currency_cap": config.CURRENCY_CAP_DEFAULT,
            "turnover_cap": config.TURNOVER_CAP_DEFAULT,
        }
        for benchmark in config.BENCHMARK_CHOICES
    ]


if __name__ == "__main__":
    profiles = build_profiles()
    print(f"Built {len(profiles)} customer profiles:")
    for p in profiles:
        print(f"  {p['profile_id']:12s} liquidity_cap={p['liquidity_cap']:.2f} "
              f"currency_cap={p['currency_cap']:.2f}")
