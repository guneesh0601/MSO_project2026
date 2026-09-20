# The Search Loop(s) in Opti-Money — Explained Simply

Your question was sharp: since x_i are fractions (continuous numbers between 0 and 1), aren't there literally infinite possible portfolios? How can any loop check all of them?

The short answer: there are actually **three separate, nested loops** in this system, and only ONE of them deals with the "infinite" continuous x values — and that one does NOT check them one by one. It uses calculus to jump straight toward the answer. The other two loops deal with a small, FINITE list of things (customer choices), and those genuinely are checked one by one. Let's go through all three, from the outside in.

---

## The big picture: three nested loops

```
LOOP A (outermost) — loop over every possible CUSTOMER PROFILE combination
  for each profile (risk level, benchmark, horizon, etc.):
  
      LOOP B (middle) — build one efficient frontier for this profile
      for k = 1 to K+2 (a small number, e.g. 12 points):

          LOOP C (innermost) — solve ONE optimization problem
          (this is where the continuous x is actually searched, using calculus,
           not brute-force checking)
```

Loop A and Loop B are things WE design and control (the bank's workflow, and our reproduction of it). Loop C is handled automatically by the solver software (MINOS in the original paper; scipy or Pyomo/IPOPT in our reproduction) — we don't write it ourselves, we just call it.

---

## Loop A — the customer-profile loop (finite, and yes, brute-forced)

This is the "batch mode" the paper talks about on page 41-42. The customer's answers to the four screens only come from a **small, finite set of categories** — nobody types in an arbitrary continuous number here. For example:

- Risk level: 5 choices (low, low-medium, medium, risk-oriented, high)
- Benchmark: 4 choices (CPI, Bank of Israel rate, USD, Euro)
- Horizon: 4 choices (1, 2, 5, 10 years)
- Objective: a handful of choices (retirement, house, kids, no specific goal)
- Liquidity/currency preference: a few discrete levels

If you multiply all these small finite lists together, you get a large number of combinations — the paper says about 36,000 — but it is still a **finite, countable list**. So Loop A really is: "for each of these ~36,000 combinations, do the following." That is genuine brute-force enumeration, but over a small finite menu of choices, not over continuous numbers. This is why the bank could run it overnight and just store the results in a lookup table.

**What is calculated in Loop A:** nothing new here directly — Loop A's only job is to hand off one specific profile (which fixes the benchmark, the risk bounds, the forecast to use, the liquidity/currency limits) into Loop B, and then store whatever Loop B returns (a full efficient frontier of portfolios) against that profile's ID, so a CRM can look it up instantly later.

---

## Loop B — building one efficient frontier for one fixed profile

This is the 4-step procedure from the paper's Appendix (page 49), and it is also just a short, finite loop — not infinite.

1. **Point 1:** Solve one optimization: minimize risk, ignore expected return entirely. Get the lowest-risk portfolio.
2. **Point 2:** Solve another optimization: maximize expected return, ignore risk entirely. Get the highest-return portfolio.
3. **Pick K target returns:** Take the expected returns from Point 1 and Point 2, and choose K evenly spaced values in between them (say K = 10).
4. **Points 3 through K+2:** For each of those K target returns, solve one more optimization: minimize risk, but force the expected return to equal that specific target.

So Loop B runs a total of K+2 individual optimizations (for K=10, that's 12 optimizations) — a small, fixed, finite number we choose ourselves. Each of those 12 optimizations is one call into Loop C.

**What is calculated in Loop B:** the 12 resulting portfolios (each one a full vector of x values), plus their risk and return numbers, which together trace out the efficient frontier curve. **What is "seen":** this is literally what gets displayed to the CRM/customer as the frontier — the picture with risk on one axis and return on the other.

---

## Loop C — the actual numerical solve (this is where your "infinite" worry lives, and gets resolved)

Here we're solving ONE specific problem: "find the x vector (fractions across all n assets) that minimizes risk, subject to sum of x = 1, x ≥ 0, and (for most points) expected return = some fixed target." This is where x really is continuous, and technically there are infinitely many candidate x vectors you COULD try.

**The key idea: we never check them one by one.** Instead the solver uses calculus — specifically, it uses the *gradient* (the slope of the objective function at the current point) to figure out, without guessing randomly, exactly which direction would make risk go down. This is the same idea as walking downhill in thick fog: you can't see the whole mountain, but you can feel which way the ground slopes under your feet right now, and you take a step in that direction. You don't need to visit every point on the mountain to find the valley — you just keep following the downhill slope until the ground feels flat.

Here is what actually happens, step by step, inside Loop C:

**Step 0 — Start:** Pick one starting guess for x. A common simple choice is equal weights across all assets (e.g., if there are 10 assets, start at 10% each), or the customer's existing portfolio if we need to respect a turnover limit.

**Step 1 — Evaluate:** At the current x, calculate two things:
- The objective value: the current risk score (using the risk formula, which itself needs PortfRet for all 36 months, computed from the current x and the historical data).
- Whether the constraints are satisfied: does x sum to 1? Are all x values non-negative? Does the expected return hit the target for this frontier point?

**Step 2 — Compute the gradient:** Work out, mathematically, how the risk score would change if you nudged each x_i up or down slightly. This tells you the "slope" in every direction at once — which assets, if increased a little, would reduce risk, and which would increase it.

**Step 3 — Decide a direction and a step size:** Using that slope information (and making sure not to break the constraints — this is like sliding along a fence instead of walking through it, when the straight downhill direction would take you outside the allowed region), pick a new, slightly different x that should be a bit better than the current one.

**Step 4 — Update:** Move to this new x. This new x replaces the old one as "the current candidate."

**Step 5 — Check for convergence:** Ask: did the risk score improve by a meaningful amount, or has it basically stopped changing? Are the constraints satisfied to a tight tolerance? If things have stopped improving and constraints are met, STOP — this x is the answer for this one optimization. If not, go back to Step 1 and repeat with the new x.

**How many times does this loop actually run?** Not infinitely, and not anywhere close to "all possible combinations." Because each step uses real slope information (not guessing), this loop typically converges in somewhere between about 10 and a few hundred iterations, even when there are dozens of x variables. That is the entire trick that makes this feasible: calculus-based search replaces brute-force enumeration.

**What is calculated at each iteration of Loop C:** the risk score, the constraint check, and the gradient. **What is "seen"/kept:** only the final converged x when the loop stops — all the intermediate guesses during the search are thrown away; only the final answer for that one frontier point gets passed back up to Loop B.

---

## Directly answering: "aren't there infinite combinations?"

Yes and no, depending on which loop you mean:

- **For the customer profile (Loop A):** No — it's a large but strictly finite list (about 36,000 combinations in the paper), and yes, that finite list really is brute-force enumerated, one profile at a time, in an overnight batch.
- **For the portfolio weights x (Loop C):** Yes, technically there are infinitely many possible x vectors (they're continuous fractions) — but the solver never checks them one at a time. It uses the gradient (calculus) to walk directly toward the best one, the same way you don't need to test every spot on a hill to find the bottom of the valley — you just follow the slope down. This is why the whole system, despite having "infinite" possible portfolios in theory, can still solve everything overnight for 36,000 customer profiles: each individual solve converges quickly (Loop C), there are only a small fixed number of frontier points per profile (Loop B, e.g. 12), and only a finite list of profiles (Loop A, ~36,000).

---

## Where this maps to our reproduction

- Loop A: a simple Python loop (a `for` loop) over a small list of profile combinations we define ourselves (fewer than the bank's, since we're using a smaller demo asset set).
- Loop B: a simple Python loop (another `for` loop) that calls the optimizer 12 times (or however many K+2 we choose) per profile.
- Loop C: not something we write by hand at all — we just call `scipy.optimize.minimize(...)` (or a similar library) once per frontier point, hand it the objective function, the constraints, and one starting guess, and it internally performs the gradient-based steps described above and hands us back the converged x.
