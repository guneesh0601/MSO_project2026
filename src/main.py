"""Runs the full Opti-Money reproduction pipeline, start to finish:

  1. Download raw data (skipped if already downloaded).
  2. Build the r-table and benchmark returns.
  3. Build the forecast vector (rho).
  4. Build the list of customer profiles (Loop A).
  5. For each profile, for each risk measure, build the efficient frontier
     (Loop B, which calls the optimizer / Loop C repeatedly).
  6. Round every resulting portfolio to clean percentages.
  7. Save all results as CSVs, and plot risk-vs-return frontiers per profile.
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import data_loader
import returns_calculator
import forecasts
import risk_measures as rm
import customer_profiles
import frontier_builder
import rounding


def ensure_data():
    raw_files_present = all(
        os.path.exists(os.path.join(config.DATA_RAW_DIR, f"{name}.csv"))
        for name in list(config.ASSETS.keys())
    )
    if not raw_files_present:
        data_loader.download_all_raw_data()

    processed_present = os.path.exists(
        os.path.join(config.DATA_PROCESSED_DIR, "asset_returns.csv")
    )
    if not processed_present:
        returns_calculator.build_and_save()

    forecasts_present = os.path.exists(
        os.path.join(config.DATA_PROCESSED_DIR, "forecasts.csv")
    )
    if not forecasts_present:
        r_table, _ = returns_calculator.load_processed()
        forecasts.build_and_save(r_table)


def run_all():
    ensure_data()

    r_table, bch_table = returns_calculator.load_processed()
    r_table = r_table[config.ASSET_NAMES]
    returns_np = r_table.values

    rho_series = forecasts.load_forecasts()
    rho = rho_series[config.ASSET_NAMES].values  # annual scale, matches forecasts.py

    weights = rm.decaying_weights(config.LAMBDA_DECAY, config.T_MONTHS)
    market_w = np.array([config.MARKET_PORTFOLIO[n] for n in config.ASSET_NAMES])

    profiles = customer_profiles.build_profiles()

    all_frontiers = {}   # (profile_id, risk_measure) -> DataFrame

    start_time = time.time()
    total = len(profiles) * len(config.RISK_MEASURES)
    done = 0

    for profile in profiles:
        bch_series = bch_table[profile["benchmark"]].values

        for risk_measure in config.RISK_MEASURES:
            frontier = frontier_builder.build_frontier(
                risk_measure, profile, returns_np, bch_series, weights,
                market_w, rho,
            )

            frontier["rounded_x"] = frontier["x"].apply(
                lambda x: rounding.largest_remainder_round(np.array(x), grid=0.01)
            )

            all_frontiers[(profile["profile_id"], risk_measure)] = frontier

            out_name = f"{profile['profile_id']}__{risk_measure}.csv"
            out_path = os.path.join(config.OUTPUTS_FRONTIERS_DIR, out_name)
            weight_table = frontier_builder.frontier_to_weight_table(frontier)
            weight_table.to_csv(out_path, index=False)

            done += 1
            if not frontier["success"].all():
                print(f"  WARNING: some points did not converge for "
                      f"{profile['profile_id']} / {risk_measure}")

        elapsed = time.time() - start_time
        print(f"[{done}/{total} risk-measure runs done, "
              f"{elapsed:.1f}s elapsed] finished profile '{profile['profile_id']}'")

    plot_frontiers(all_frontiers, profiles)
    print(f"\nDone. {len(profiles)} profiles x {len(config.RISK_MEASURES)} risk "
          f"measures = {total} frontiers built and saved to "
          f"{config.OUTPUTS_FRONTIERS_DIR}")
    return all_frontiers


def plot_frontiers(all_frontiers: dict, profiles: list[dict]):
    colors = {"symmetric": "tab:blue", "asymmetric": "tab:orange", "markowitz": "tab:green"}

    for profile in profiles:
        pid = profile["profile_id"]
        fig, ax = plt.subplots(figsize=(6, 4.5))
        for risk_measure in config.RISK_MEASURES:
            frontier = all_frontiers[(pid, risk_measure)]
            f_sorted = frontier.sort_values("achieved_return")
            ax.plot(f_sorted["risk"], f_sorted["achieved_return"],
                    marker="o", label=risk_measure, color=colors[risk_measure])

        ax.set_xlabel("Risk")
        ax.set_ylabel("Expected annual return")
        ax.set_title(f"Efficient frontier: {pid}")
        ax.legend()
        fig.tight_layout()

        out_path = os.path.join(config.OUTPUTS_PLOTS_DIR, f"{pid}.png")
        fig.savefig(out_path, dpi=120)
        plt.close(fig)

    print(f"Saved {len(profiles)} frontier plots to {config.OUTPUTS_PLOTS_DIR}")


if __name__ == "__main__":
    run_all()
