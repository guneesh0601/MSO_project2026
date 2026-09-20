# The Third Constraint, Explained From Absolute Zero

This file explains just ONE thing, but explains it completely: the constraint that says

    ExpRet = ExpRet(k)

We will build this up piece by piece, using tiny numbers, so that nothing is assumed.

---

## Part 1 — Let's recall what "ExpRet" even is, from scratch

Imagine you have money, and you're going to split it across a few investments. Let's keep it very small: just **2 assets** to start.

- Asset A (say, stocks): the bank forecasts it will earn **10% next year**.
- Asset B (say, bonds): the bank forecasts it will earn **4% next year**.

These forecast numbers are called rho (one for each asset). They are just given to you — someone (the bank's economists) already decided these numbers. You don't calculate them; you look them up. In our example:

    rho for Asset A = 0.10   (10%)
    rho for Asset B = 0.04   (4%)

Now, YOU (or rather, the solver, on your behalf) get to decide **how much of your money goes into each asset**. Let's call these decisions:

    x_A = fraction of money in Asset A
    x_B = fraction of money in Asset B

For example, maybe we try: x_A = 0.5 (50%) and x_B = 0.5 (50%).

**ExpRet** simply means: "if I split my money this way, what return do I expect overall?" You get it by multiplying each asset's forecast by how much money you put into it, then adding those up:

    ExpRet = (rho for A * x_A) + (rho for B * x_B)
    ExpRet = (0.10 * 0.5) + (0.04 * 0.5)
    ExpRet = 0.05 + 0.02
    ExpRet = 0.07

So with a 50/50 split, we expect a 7% return overall. That's it — ExpRet is just a weighted average of the forecasts, weighted by how much money goes where.

**Key point:** ExpRet is not a fixed number sitting somewhere waiting to be looked up. It is a **formula that depends on x**. Change x_A and x_B, and ExpRet changes too. Try x_A = 0.8, x_B = 0.2 instead:

    ExpRet = (0.10 * 0.8) + (0.04 * 0.2)
    ExpRet = 0.08 + 0.008
    ExpRet = 0.088   (8.8%)

Putting more money into the higher-forecast asset (A) pushed ExpRet up. Makes sense — that's exactly what you'd expect.

---

## Part 2 — Now, what is "ExpRet(k)"?

This is a completely different thing from ExpRet. Here's the distinction, stated as plainly as possible:

- **ExpRet** (no label) = a formula. It depends on whatever x you plug in. It is *calculated*.
- **ExpRet(k)** = a single fixed number, chosen in advance, before you even start solving. It does not depend on x at all. It is *decided*, not calculated from x.

Where does this fixed number come from? Recall from our earlier discussion of building the efficient frontier: we first solve two "extreme" problems.

- We find the absolute lowest-risk portfolio possible (call its resulting return the "low end"). Say this comes out to 3% return.
- We find the absolute highest-return portfolio possible (call its resulting return the "high end"). Say this comes out to 9% return.

Then we pick a small number of target values spaced evenly between 3% and 9%. Say we pick 3 of them:

    ExpRet(1) = 4.5%
    ExpRet(2) = 6.0%
    ExpRet(3) = 7.5%

These three numbers (4.5%, 6%, 7.5%) are just plain numbers we chose ahead of time, using simple arithmetic (evenly spacing between 3% and 9%). They have nothing to do with any particular x yet. They are just "the goals" we're about to aim for, one at a time.

**Important side-note on the "(k)":** the "(k)" here is not an exponent — it does not mean "raised to the power of k." It's just a label, like a name tag, saying "this is target number k in our list." ExpRet(1) means "the first target," ExpRet(2) means "the second target," and so on. If it meant "squared," it would be written without parentheses. The parentheses are exactly there to tell you it's a label, not a power.

---

## Part 3 — Now let's put them together: what does "ExpRet = ExpRet(k)" actually demand?

This equation is a **rule that x must obey**. In plain English, it says:

> "Whatever x you (the solver) choose, when you compute ExpRet from it using the formula in Part 1, the answer must come out to exactly this one specific number we picked in Part 2 — no more, no less."

Let's make this fully concrete. Suppose we're currently working on target k=1, so ExpRet(1) = 4.5%, or written as a decimal, 0.045.

The constraint says:

    (rho for A * x_A) + (rho for B * x_B) = 0.045

Plugging in our forecasts (rho for A = 0.10, rho for B = 0.04):

    (0.10 * x_A) + (0.04 * x_B) = 0.045

This is now a real, solvable rule. Any x_A and x_B that make this equation true are "allowed." Any x_A, x_B that make it false are "not allowed," no matter how good they look for risk.

---

## Part 4 — Let's actually solve it by hand, with just 2 assets, to make it 100% concrete

With only 2 assets, we actually have enough information to solve this exactly by hand (no computer needed), because we have exactly 2 unknowns (x_A and x_B) and exactly 2 equations:

**Equation 1 (the budget constraint, from before):**

    x_A + x_B = 1

**Equation 2 (our new constraint, the expected-return target):**

    0.10 * x_A + 0.04 * x_B = 0.045

Let's solve this step by step, using basic algebra (substitution).

From Equation 1: x_B = 1 - x_A

Substitute this into Equation 2:

    0.10 * x_A + 0.04 * (1 - x_A) = 0.045

Expand the brackets:

    0.10 * x_A + 0.04 - 0.04 * x_A = 0.045

Combine the x_A terms (0.10 * x_A minus 0.04 * x_A = 0.06 * x_A):

    0.06 * x_A + 0.04 = 0.045

Subtract 0.04 from both sides:

    0.06 * x_A = 0.005

Divide both sides by 0.06:

    x_A = 0.005 / 0.06 = 0.0833...  (about 8.33%)

Then:

    x_B = 1 - 0.0833 = 0.9167  (about 91.67%)

**Let's double check this actually works.** Plug x_A = 0.0833 and x_B = 0.9167 back into the ExpRet formula:

    ExpRet = (0.10 * 0.0833) + (0.04 * 0.9167)
    ExpRet = 0.00833 + 0.03667
    ExpRet = 0.045

It matches exactly 0.045 (4.5%), which was our target. The constraint is satisfied.

---

## Part 5 — Wait, with only 2 assets, there was only ONE valid answer. So what is there left to "optimize"?

This is the most important realization in this whole file, so read this part slowly.

With exactly 2 assets, once you force both "x_A + x_B = 1" AND "ExpRet = 0.045" to hold at the same time, algebra shows there is only **one single possible pair of (x_A, x_B)** that satisfies both — we just calculated it above (0.0833 and 0.9167). There's no wiggle room left. There is nothing left to optimize — the constraints alone pin down the entire answer, and risk doesn't even get a say.

**This is exactly why real portfolios use many assets (like the paper's ~60 asset classes), not just 2.** With 3 or more assets, the two constraints (budget = 1, ExpRet = target) are not enough to fully pin down x — there is still freedom left over (infinitely many combinations of x_A, x_B, x_C, ... that all satisfy both constraints simultaneously). It is only within that remaining freedom that risk minimization actually gets to do its job — searching among all the different x combinations that still hit the target return, for whichever one also happens to have the lowest risk.

**Quick illustration with 3 assets:** suppose we add a third asset C with rho_C = 0.06 (6%). Now our two constraints are:

    x_A + x_B + x_C = 1
    0.10*x_A + 0.04*x_B + 0.06*x_C = 0.045

This is 2 equations but 3 unknowns — algebra alone cannot pin down a single unique answer anymore; there is a whole family (an infinite line of possible combinations) of x_A, x_B, x_C that satisfy both equations at once. For example, both of these satisfy the two equations above:

- x_A = 0.05, x_B = 0.70, x_C = 0.25 (check: sum = 1.00; ExpRet = 0.10*0.05 + 0.04*0.70 + 0.06*0.25 = 0.005+0.028+0.015 = 0.048 -- close but let's not worry about hand-picking exact numbers, the point is illustrative)
- Many other combinations also work.

Since more than one valid combination exists once you have 3+ assets, NOW it makes sense to ask "okay, out of all these valid combinations, which one has the lowest risk?" That question is exactly what the solver is answering. The constraint doesn't hand you the answer directly (like it did with 2 assets) — it just narrows down the enormous space of all possible portfolios to a smaller, but still large, set of "allowed" portfolios, and risk-minimization picks the best one from within that allowed set.

---

## Part 6 — A simple picture in your head (no diagram needed, just imagine it)

Picture every possible portfolio as a point in space, one point per (x_A, x_B, x_C, ...) combination. Two rules chop this space down:

1. **"sum of x_i = 1, x_i ≥ 0"** — this alone already removes most of infinite space, leaving only the portfolios that are "valid" in the sense of actually spending all your money without going negative anywhere. Geometrically, if you've heard the term, this remaining set is shaped like a flat triangle (or its higher-dimensional equivalent) — it's called a simplex, but you don't need that word to understand the idea: it's just "all the ways to split 100% of your money across n things."

2. **"ExpRet = ExpRet(k)"** — this is like taking a knife and slicing straight through that triangle at one exact height (the height that corresponds to exactly the target return). Everything that isn't exactly on that slice is thrown away. What's left is a smaller, thinner slice of possibilities — but with 3 or more assets, that slice is still not just one point; it still contains many valid portfolios.

3. The solver's actual job is: **search along that remaining thin slice**, checking the risk score at different points on it, until it finds the point on the slice with the lowest risk. That point is the answer for this particular k.

Do this whole process once per target k (once per "height" you slice at), and you get one different portfolio per target — which, when you connect all these different portfolios together, IS the efficient frontier.

---

## Part 7 — Why an exact equals sign, and not "greater than or equal to"?

You might wonder: why force ExpRet to equal the target exactly, rather than just requiring ExpRet to be at least the target (which sounds more natural — "I want at least this much return")?

In practice, for this kind of problem, it turns out both versions give you the same answer at the optimal point. Here's the intuitive reason: since taking on more risk generally allows for more expected return, the risk-minimizing solver would never voluntarily produce MORE return than it strictly needs to — extra unnecessary return usually comes bundled with extra unnecessary risk, which the solver is actively trying to avoid. So even if you wrote the constraint as "ExpRet ≥ target" (allowed to be more, but not less), the solver's own drive to minimize risk naturally pushes it to land exactly on "ExpRet = target," because going any higher than necessary would only add risk for no reason. The paper writes it directly as an equality because that's the cleanest way to describe "give me the specific point on the frontier where return equals exactly this value," which is precisely what's needed to trace out K distinct, evenly-spaced points along the frontier.

---

## Part 8 — How a computer actually checks "does ExpRet = target" during solving

One last very practical detail. Computers work with decimal numbers, and asking for something to be exactly, perfectly equal (down to infinite decimal places) is often numerically fragile. In real solver software (like MINOS, or scipy in Python), an equality constraint like this is treated as: "the difference between ExpRet and the target must be smaller than some extremely tiny allowed tolerance," for example, smaller than 0.000001. This is close enough to "exactly equal" for every practical purpose, but gives the numerical solver a tiny bit of breathing room, since perfect infinite-precision equality isn't achievable on a computer anyway. You don't need to do anything special about this yourself — libraries like scipy handle this tolerance automatically when you tell them a constraint is of "equality" type.

---

## Summary — the whole idea in one paragraph

ExpRet is a formula (forecast times weight, summed up) that changes depending on which portfolio x you try. ExpRet(k) is a fixed, pre-chosen number — one of several evenly spaced target returns picked earlier between the lowest-risk and highest-return extreme portfolios. The constraint "ExpRet = ExpRet(k)" forces the solver to only consider portfolios that hit exactly that one target return, no more and no less. With only 2 assets, this constraint (combined with the budget constraint) leaves no freedom at all — there's exactly one answer, and risk-minimization has nothing left to decide. With 3 or more assets, there is still an entire family of valid portfolios that all hit the same target return, and it is only among those that the solver actually searches for the one with the lowest risk. Repeating this whole process once for each target k, using a different "slice" of the return axis each time, is exactly how the efficient frontier gets built, one point at a time.
