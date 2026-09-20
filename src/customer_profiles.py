"""Generates the finite list of customer profiles we test ('Loop A'), and
translates each one into the concrete settings frontier_builder.py needs
(which benchmark to use, which constraint bounds apply).

This is a small, illustrative version of the bank's ~36,000-combination
batch: we vary risk level and benchmark choice (2 dimensions), which is
enough to demonstrate the whole pipeline and compare results across
customer types, without needing to enumerate every dimension the real
system offered (horizon, objective, liquidity level, etc. are held fixed
at reasonable defaults for this reproduction).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def build_profiles() -> list[dict]:
    profiles = []
    for risk_level in config.RISK_LEVEL_CHOICES:
        for benchmark in config.BENCHMARK_CHOICES:
            profiles.append({
                "profile_id": f"{risk_level}__{benchmark}",
                "risk_level": risk_level,
                "benchmark": benchmark,
                "equity_cap": config.RISK_CATEGORY_EQUITY_CAP[risk_level],
                "liquidity_cap": config.LIQUIDITY_CAP_DEFAULT,
                "currency_cap": config.CURRENCY_CAP_DEFAULT,
                "turnover_cap": config.TURNOVER_CAP_DEFAULT,
            })
    return profiles


if __name__ == "__main__":
    profiles = build_profiles()
    print(f"Built {len(profiles)} customer profiles:")
    for p in profiles:
        print(f"  {p['profile_id']:30s} equity_cap={p['equity_cap']:.2f}")
