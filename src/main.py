"""Runs the full Opti-Money reproduction pipeline, start to finish:

  1. Make sure raw data, returns, benchmarks and forecasts exist
     (engine.ensure_data).
  2. Build the list of customer profiles (Loop A).
  3. For each profile, for each risk measure, build the efficient frontier
     (Loop B, via engine.solve_frontier) and round each portfolio to clean
     percentages.
  4. Save all results as CSVs, and plot risk-vs-return frontiers per profile.
"""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import customer_profiles
import engine
import frontier_builder


def run_all():
    engine.ensure_data()

    profiles = customer_profiles.build_profiles()

    all_frontiers = {}   # (profile_id, risk_measure) -> DataFrame

    start_time = time.time()
    total = len(profiles) * len(config.RISK_MEASURES)
    done = 0

    for profile in profiles:
        for risk_measure in config.RISK_MEASURES:
            frontier = engine.solve_frontier(
                risk_measure, profile["benchmark"], profile["equity_cap"],
                profile["liquidity_cap"], profile["currency_cap"],
                profile_id=profile["profile_id"],
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
