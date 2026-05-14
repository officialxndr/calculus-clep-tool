"""
CLEP-style calculus problem generator.
Each public generator returns a dict:
  {id, topic, question_latex, choices, correct_index, explanation}
"""
import random
import time
import sympy as sp
from sympy import (
    symbols, Rational, diff, integrate, limit, oo,
    sin, cos, tan, sec, csc, cot, exp, log, sqrt, pi, E,
    simplify, expand, factor, latex as _sympy_latex,
)

x, t = symbols("x t")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lx(expr, **kw):
    # SymPy to LaTeX with ln notation
    kw.setdefault("ln_notation", True)
    try:
        return _sympy_latex(expr, **kw)
    except Exception:
        return str(expr)


def _make_id(name: str) -> str:
    return f"{name}_{int(time.time()*1000) % 10_000_000}_{random.randint(0, 9999)}"


def _shuffle_choices(correct_lx: str, distractor_latexes: list):
    """
    Build a 5-option choice list from one correct answer + up to 4 distractors.
    Returns (choices, correct_index).
    choices = [{"label": "A", "latex": "..."}, ...]
    """
    seen = {correct_lx}
    pool = []
    for d in distractor_latexes:
        s = str(d)
        if s and s not in seen:
            seen.add(s)
            pool.append(s)

    # Pad with generic fallbacks if we don't have 4 distractors
    fallbacks = [r"0", r"1", r"-1", r"2x", r"\frac{1}{x}", r"x^{2}", r"-x"]
    for fb in fallbacks:
        if len(pool) >= 4:
            break
        if fb not in seen:
            pool.append(fb)
            seen.add(fb)

    all_opts = [correct_lx] + pool[:4]
    random.shuffle(all_opts)
    correct_index = all_opts.index(correct_lx)
    labels = "ABCDE"
    choices = [{"label": labels[i], "latex": all_opts[i]} for i in range(5)]
    return choices, correct_index


def _q(name, topic, question_latex, correct_lx, distractors, explanation, steps=None):
    choices, correct_index = _shuffle_choices(correct_lx, distractors)
    return {
        "id": _make_id(name),
        "topic": topic,
        "question_latex": question_latex,
        "choices": choices,
        "correct_index": correct_index,
        "explanation": explanation,
        "steps": steps or [],
    }


# ── Derivative templates ──────────────────────────────────────────────────────

def gen_deriv_power():
    """f(x) = a·xⁿ, find f′(x). Covers fractional & negative exponents."""
    a = random.choice([2, 3, 4, -1, -2, -3, 5])
    n = random.choice([
        Rational(1, 3), Rational(2, 3), Rational(1, 2),
        Rational(-1, 3), Rational(-2, 3), Rational(-1, 2),
        sp.Integer(2), sp.Integer(3), sp.Integer(4),
        sp.Integer(-1), sp.Integer(-2), sp.Integer(5),
    ])
    expr = a * x**n
    correct = simplify(diff(expr, x))
    c_lx = _lx(correct)

    d = [
        _lx(simplify(a * x**(n - 1))),            # forgot n factor
        _lx(simplify(n * x**(n - 1))),             # forgot a
        _lx(simplify(-correct)),                   # sign error
        _lx(simplify(a * n * x**n)),               # wrong exponent (n not n-1)
    ]
    if n != -1:
        d.append(_lx(simplify(a * x**(n + 1) / (n + 1))))  # integrated instead

    expl = (
        rf"**Power rule:** $\frac{{d}}{{dx}}[ax^n] = an\,x^{{n-1}}$. "
        rf"Here $a={a},\; n={_lx(n)}$, so $f'(x) = {_lx(a)}\cdot{_lx(n)}\cdot x^{{{_lx(n-1)}}} = {c_lx}$."
    )
    steps = [
        rf"Identify the form: $f(x) = a\,x^n$ with $a = {_lx(a)}$ and $n = {_lx(n)}$.",
        r"Apply the **power rule:** $\frac{d}{dx}[a\,x^n] = a\,n\,x^{n-1}$.",
        rf"Substitute the values: $f'(x) = ({_lx(a)})({_lx(n)})\,x^{{{_lx(n-1)}}} = {c_lx}$.",
    ]
    return _q("deriv_power", "derivatives",
              rf"If $f(x) = {_lx(expr)}$, then $f'(x) =$",
              c_lx, d, expl, steps)


def gen_deriv_product_quotient():
    """Randomly pick product rule or quotient rule."""
    if random.random() < 0.5:
        return _gen_product_rule()
    return _gen_quotient_rule()


def _gen_product_rule():
    n = random.randint(2, 4)
    trig_fn, trig_name, trig_deriv = random.choice([
        (sin(x), r"\sin", cos(x)),
        (cos(x), r"\cos", -sin(x)),
    ])
    expr = x**n * trig_fn
    correct = simplify(diff(expr, x))
    c_lx = _lx(correct)
    # Distractors: common product-rule errors
    wrong_no_prod = _lx(simplify(n * x**(n-1) * diff(trig_fn, x)))  # chain without product
    wrong_sign    = _lx(simplify(-correct))
    wrong_just_f  = _lx(simplify(n * x**(n-1) * trig_fn))           # didn't differentiate g
    wrong_just_g  = _lx(simplify(x**n * diff(trig_fn, x)))          # didn't differentiate f

    expl = (
        rf"**Product rule:** $\frac{{d}}{{dx}}[f\cdot g] = f'\cdot g + f\cdot g'$. "
        rf"With $f={_lx(x**n)}$ and $g={_lx(trig_fn)}$: "
        rf"$f'={_lx(diff(x**n,x))}$, $g'={_lx(diff(trig_fn,x))}$. "
        rf"Answer: ${c_lx}$."
    )
    steps = [
        rf"Identify the two factors: $f(x) = {_lx(x**n)}$ and $g(x) = {_lx(trig_fn)}$.",
        rf"Differentiate each: $f'(x) = {_lx(diff(x**n, x))}$ and $g'(x) = {_lx(diff(trig_fn, x))}$.",
        r"Apply the **product rule:** $\frac{d}{dx}[f\,g] = f'\,g + f\,g'$.",
        rf"Combine and simplify: ${c_lx}$.",
    ]
    return _q("deriv_product", "derivatives",
              rf"Find $\frac{{d}}{{dx}}\left[{_lx(expr)}\right]$",
              c_lx, [wrong_no_prod, wrong_sign, wrong_just_f, wrong_just_g], expl, steps)


def _gen_quotient_rule():
    # f(x) = (ax^m) / (bx^n + c) style or tan(x)/(kx)
    use_trig = random.random() < 0.4
    if use_trig:
        k = random.choice([2, 3, 4])
        expr = tan(x) / (k * x)
        correct = simplify(diff(expr, x))
        c_lx = _lx(correct)
        wrong = [
            _lx(simplify(sec(x)**2 / k)),              # forgot quotient rule
            _lx(simplify(-correct)),                    # sign
            _lx(simplify(tan(x) / (k * x**2))),        # forgot numerator deriv
            _lx(simplify((sec(x)**2 * k * x) / (k * x)**2)),  # partial quotient
        ]
        expl = (
            rf"**Quotient rule:** $\frac{{d}}{{dx}}\left[\frac{{f}}{{g}}\right]=\frac{{f'g-fg'}}{{g^2}}$. "
            rf"With $f=\tan x$, $g={k}x$: $f'=\sec^2 x$, $g'={k}$. "
            rf"Answer: ${c_lx}$."
        )
        steps = [
            rf"Identify numerator $f = \tan x$ and denominator $g = {k}x$.",
            rf"Compute derivatives: $f' = \sec^2 x$ and $g' = {k}$.",
            r"Apply the **quotient rule:** $\dfrac{f'\,g - f\,g'}{g^2}$.",
            rf"Plug in and simplify: ${c_lx}$.",
        ]
        return _q("deriv_quotient", "derivatives",
                  rf"If $f(x)=\dfrac{{\tan x}}{{{k}x}}$, then $f'(x)=$",
                  c_lx, wrong, expl, steps)
    else:
        a, m = random.randint(1, 4), random.randint(2, 4)
        b, n_exp = random.randint(1, 3), random.randint(2, 3)
        numer = a * x**m
        denom = b * x**n_exp
        expr = numer / denom
        expr_s = simplify(expr)  # simplifies to power
        correct = simplify(diff(expr_s, x))
        c_lx = _lx(correct)
        wrong = [_lx(simplify(-correct)), _lx(simplify(diff(numer, x)/denom)),
                 _lx(simplify(a * m * x**(m-1))), _lx(simplify(expr_s))]
        expl = (
            rf"Simplify first: $\frac{{{_lx(numer)}}}{{{_lx(denom)}}} = {_lx(expr_s)}$, "
            rf"then apply power rule: ${c_lx}$."
        )
        steps = [
            rf"Simplify the quotient first: $\dfrac{{{_lx(numer)}}}{{{_lx(denom)}}} = {_lx(expr_s)}$.",
            r"Apply the **power rule** to the simplified expression.",
            rf"Result: ${c_lx}$.",
        ]
        return _q("deriv_quotient", "derivatives",
                  rf"Find $\frac{{d}}{{dx}}\left[\frac{{{_lx(numer)}}}{{{_lx(denom)}}}\right]$",
                  c_lx, wrong, expl, steps)


def gen_deriv_chain():
    """Chain rule: trig(g(x)), exp(g(x)), or power of function."""
    choice = random.randint(0, 3)
    if choice == 0:
        # sin(ax^n) or sin(x^n)
        a = random.choice([1, 2, 3])
        n = random.choice([2, 3])
        inner = a * x**n
        expr = sin(inner)
        correct = simplify(diff(expr, x))
        c_lx = _lx(correct)
        wrong = [
            _lx(cos(inner)),                         # forgot inner deriv
            _lx(simplify(-cos(inner) * diff(inner, x))),
            _lx(simplify(cos(inner) * a)),
            _lx(simplify(-cos(inner))),
        ]
        expl = (
            rf"**Chain rule:** $\frac{{d}}{{dx}}[\sin(u)] = \cos(u)\cdot u'$. "
            rf"Here $u={_lx(inner)}$, $u'={_lx(diff(inner,x))}$. "
            rf"Answer: $\cos({_lx(inner)})\cdot{_lx(diff(inner,x))} = {c_lx}$."
        )
        steps = [
            rf"Identify outer function $\sin(u)$ and inner $u = {_lx(inner)}$.",
            rf"Compute the inner derivative: $u' = {_lx(diff(inner, x))}$.",
            r"Apply the **chain rule:** $\frac{d}{dx}[\sin u] = \cos(u)\cdot u'$.",
            rf"Substitute: $\cos({_lx(inner)})\cdot {_lx(diff(inner, x))} = {c_lx}$.",
        ]
        return _q("deriv_chain_sin", "derivatives",
                  rf"Find $\frac{{d}}{{dx}}\left[\sin\!\left({_lx(inner)}\right)\right]$",
                  c_lx, wrong, expl, steps)
    elif choice == 1:
        # cos(ax)
        a = random.choice([2, 3, 4])
        inner = a * x
        expr = cos(inner)
        correct = simplify(diff(expr, x))
        c_lx = _lx(correct)
        wrong = [_lx(-sin(inner)), _lx(sin(inner)), _lx(a * sin(inner)), _lx(-a * cos(inner))]
        expl = (
            rf"**Chain rule:** $\frac{{d}}{{dx}}[\cos(u)] = -\sin(u)\cdot u'$. "
            rf"With $u={_lx(inner)}$, $u'={a}$. Answer: ${c_lx}$."
        )
        steps = [
            rf"Let $u = {_lx(inner)}$, so $u' = {a}$.",
            r"Apply the **chain rule:** $\frac{d}{dx}[\cos u] = -\sin(u)\cdot u'$.",
            rf"Substitute and simplify: ${c_lx}$.",
        ]
        return _q("deriv_chain_cos", "derivatives",
                  rf"Find $\frac{{d}}{{dx}}\left[\cos\!\left({_lx(inner)}\right)\right]$",
                  c_lx, wrong, expl, steps)
    elif choice == 2:
        # e^(ax^n)
        a = random.choice([1, 2, 3])
        n = random.choice([2, 3])
        inner = a * x**n
        expr = exp(inner)
        correct = simplify(diff(expr, x))
        c_lx = _lx(correct)
        wrong = [
            _lx(exp(inner)),
            _lx(simplify(inner * exp(inner))),
            _lx(simplify(a * exp(inner))),
            _lx(simplify(n * x**(n-1) * exp(inner))),
        ]
        expl = (
            rf"**Chain rule:** $\frac{{d}}{{dx}}[e^u] = e^u\cdot u'$. "
            rf"With $u={_lx(inner)}$, $u'={_lx(diff(inner,x))}$. Answer: ${c_lx}$."
        )
        steps = [
            rf"Let $u = {_lx(inner)}$, so $u' = {_lx(diff(inner, x))}$.",
            r"Apply the **chain rule:** $\frac{d}{dx}[e^u] = e^u \cdot u'$.",
            rf"Substitute: $e^{{{_lx(inner)}}} \cdot {_lx(diff(inner, x))} = {c_lx}$.",
        ]
        return _q("deriv_chain_exp", "derivatives",
                  rf"Find $\frac{{d}}{{dx}}\left[e^{{{_lx(inner)}}}\right]$",
                  c_lx, wrong, expl, steps)
    else:
        # tan(g(x)) composed
        n = random.choice([2, 3])
        inner = x**n
        expr = tan(inner)
        correct = simplify(diff(expr, x))
        c_lx = _lx(correct)
        wrong = [
            _lx(sec(inner)**2),
            _lx(simplify(-sec(inner)**2 * diff(inner, x))),
            _lx(simplify(sec(inner)**2 * x)),
            _lx(simplify(n * sec(inner)**2)),
        ]
        expl = (
            rf"**Chain rule:** $\frac{{d}}{{dx}}[\tan u] = \sec^2(u)\cdot u'$. "
            rf"With $u={_lx(inner)}$, $u'={_lx(diff(inner,x))}$. Answer: ${c_lx}$."
        )
        steps = [
            rf"Let $u = {_lx(inner)}$, so $u' = {_lx(diff(inner, x))}$.",
            r"Apply the **chain rule:** $\frac{d}{dx}[\tan u] = \sec^2(u)\cdot u'$.",
            rf"Substitute: $\sec^2({_lx(inner)}) \cdot {_lx(diff(inner, x))} = {c_lx}$.",
        ]
        return _q("deriv_chain_tan", "derivatives",
                  rf"Find $\frac{{d}}{{dx}}\left[\tan\!\left({_lx(inner)}\right)\right]$",
                  c_lx, wrong, expl, steps)


def gen_deriv_tangent_line():
    """Equation of tangent line to f at a given x-value."""
    # f(x) = ax^3 + bx^2 + cx or similar
    a, b, c_coef = random.randint(1, 2), random.randint(-2, 2), random.randint(-3, 3)
    pt = random.choice([-2, -1, 1, 2])
    expr = a * x**3 + b * x**2 + c_coef * x
    y0 = int(expr.subs(x, pt))
    slope = int(diff(expr, x).subs(x, pt))

    # Tangent: y = slope*(x-pt) + y0  →  y = slope*x + (y0 - slope*pt)
    intercept = y0 - slope * pt
    if intercept >= 0:
        correct_lx = rf"y = {slope}x + {intercept}"
    else:
        correct_lx = rf"y = {slope}x - {abs(intercept)}"

    # Distractors: wrong slope, wrong y-intercept
    wrong_slope = slope + random.choice([-1, 1, 2])
    wrong_int1 = intercept + random.choice([-2, 2, 4, -4])
    wrong_int2 = intercept - random.choice([1, 3, 5])

    def _line(m, b_):
        if b_ >= 0:
            return rf"y = {m}x + {b_}"
        return rf"y = {m}x - {abs(b_)}"

    wrong = [
        _line(wrong_slope, intercept),
        _line(slope, wrong_int1),
        _line(wrong_slope, wrong_int2),
        _line(-slope, intercept),
    ]
    expl = (
        rf"At $x={pt}$: $f({pt})={y0}$ (y-value), $f'(x)={_lx(diff(expr,x))}$, "
        rf"slope $= f'({pt}) = {slope}$. "
        rf"Tangent line: $y - {y0} = {slope}(x - ({pt}))$ → ${correct_lx}$."
    )
    steps = [
        rf"Find the point on the curve: $f({pt}) = {y0}$, so the tangent passes through $({pt},\,{y0})$.",
        rf"Differentiate: $f'(x) = {_lx(diff(expr, x))}$.",
        rf"Slope at $x = {pt}$: $f'({pt}) = {slope}$.",
        rf"Point-slope form: $y - {y0} = {slope}\,(x - ({pt}))$, which simplifies to ${correct_lx}$.",
    ]
    return _q("deriv_tangent", "derivatives",
              rf"Which is an equation of the tangent line to $f(x)={_lx(expr)}$ at $x={pt}$?",
              correct_lx, wrong, expl, steps)


# ── Limit templates ───────────────────────────────────────────────────────────

def gen_limit_direct():
    """Direct substitution gives a finite value, OR limit is nonexistent (vertical asymptote)."""
    # 50% chance of DNE case (like CLEP Q1)
    if random.random() < 0.45:
        a = random.choice([-5, -3, 2, 4])
        k = random.choice([3, 5, 7, 2])
        # lim_{x→a} k/(x-a) → nonexistent
        denom_str = rf"x + {-a}" if -a >= 0 else rf"x - {abs(a)}"
        correct_lx = r"\text{Nonexistent}"
        wrong = [str(k), "0", str(-k), rf"\frac{{{k}}}{{{abs(a)}}}"]
        expl = (
            rf"As $x \to {a}^-$, $\frac{{{k}}}{{{denom_str}}} \to -\infty$ and "
            rf"as $x \to {a}^+$, it $\to +\infty$. Since the one-sided limits differ, "
            rf"the two-sided limit does not exist."
        )
        steps = [
            rf"Check substitution: at $x = {a}$ the denominator is $0$ and the numerator is ${k}$, so there is a vertical asymptote.",
            rf"As $x \to {a}^-$, the denominator $\to 0^-$, so the expression $\to -\infty$.",
            rf"As $x \to {a}^+$, the denominator $\to 0^+$, so the expression $\to +\infty$.",
            r"One-sided limits disagree, so the two-sided limit does **not exist**.",
        ]
        return _q("limit_dne", "limits",
                  rf"$\displaystyle\lim_{{x \to {a}}} \dfrac{{{k}}}{{{denom_str}}}$ is",
                  correct_lx, wrong, expl, steps)
    else:
        # Polynomial: lim_{x→a} p(x)
        a = random.choice([-3, -2, -1, 0, 1, 2, 3])
        n = random.randint(2, 4)
        coeffs = [random.randint(-3, 3) for _ in range(n + 1)]
        coeffs[0] = coeffs[0] or 1
        expr = sum(coeffs[i] * x**(n - i) for i in range(n + 1))
        val = int(expr.subs(x, a))
        correct_lx = str(val)
        wrong = [str(val + random.choice([-2, 2, 4, -4])) for _ in range(4)]
        expl = (
            rf"Since $p(x)$ is a polynomial, $\lim_{{x\to {a}}} p(x) = p({a}) = {val}$ "
            rf"by direct substitution."
        )
        steps = [
            r"Polynomials are continuous everywhere, so the limit equals the function value at the point.",
            rf"Substitute $x = {a}$ into $p(x) = {_lx(expr)}$.",
            rf"Evaluate: $p({a}) = {val}$.",
        ]
        return _q("limit_direct", "limits",
                  rf"$\displaystyle\lim_{{x \to {a}}} \left({_lx(expr)}\right)$",
                  correct_lx, wrong, expl, steps)


def gen_limit_zero_zero():
    """0/0 form resolved by factoring: lim_{x→a} (x²−a²)/(x−a) = 2a."""
    a = random.choice([-3, -2, -1, 1, 2, 3, 4])
    n = random.choice([2, 3])
    # lim_{x→a} (x^n - a^n)/(x - a) = n*a^(n-1)
    numer_sym = x**n - a**n
    denom_sym = x - a
    val = n * a**(n - 1)
    correct_lx = str(val)
    wrong_vals = [str(val + d) for d in [-1, 1, 2, -2] if val + d != val][:4]
    if n == 2:
        factor_step = rf"$x^2 - {a}^2 = (x-{a})(x+{a})$, cancel $(x-{a})$, substitute: ${a}+{a}={val}$."
    else:
        factor_step = (
            rf"Factor the numerator and cancel $(x-{a})$, "
            rf"then substitute $x={a}$: result $= {val}$."
        )
    expl = rf"Indeterminate form $\frac{{0}}{{0}}$. " + factor_step
    steps = [
        rf"Try direct substitution $x = {a}$: numerator and denominator both equal $0$, so the form is $\frac{{0}}{{0}}$ (indeterminate).",
        rf"Factor the numerator so that $(x - {a})$ appears, then cancel it with the denominator.",
        rf"Substitute $x = {a}$ into the simplified expression.",
        rf"Limit value: ${val}$.",
    ]
    return _q("limit_zero_zero", "limits",
              rf"$\displaystyle\lim_{{x \to {a}}} \dfrac{{{_lx(numer_sym)}}}{{{_lx(denom_sym)}}}$",
              correct_lx, wrong_vals, expl, steps)


def gen_limit_infinity():
    """lim_{x→∞} of rational function with equal degree in numerator and denominator."""
    # Leading coefficient ratio
    a, b = random.randint(1, 5), random.randint(1, 7)
    n = random.randint(3, 5)
    a2, b2 = random.randint(0, 4), random.randint(0, 4)
    c2, d2 = random.randint(0, 5), random.randint(0, 5)
    numer = a * x**n + a2 * x**(n-2) + c2
    denom = b * x**n + b2 * x**(n-2) + d2
    ratio = Rational(a, b)
    correct_lx = _lx(ratio)
    wrong = [_lx(Rational(a2 or 1, b2 or 1)), str(a + b), _lx(Rational(b, a)), "0"]
    expl = (
        rf"Divide every term by $x^{n}$ (the highest power). "
        rf"Lower-degree terms vanish as $x\to\infty$, leaving $\frac{{{a}}}{{{b}}} = {correct_lx}$."
    )
    steps = [
        rf"Identify the highest power in numerator and denominator: $x^{{{n}}}$.",
        rf"Divide every term in both numerator and denominator by $x^{{{n}}}$.",
        r"As $x \to \infty$, every term with a negative power of $x$ tends to $0$.",
        rf"The limit reduces to the ratio of leading coefficients: $\dfrac{{{a}}}{{{b}}} = {correct_lx}$.",
    ]
    return _q("limit_infinity", "limits",
              rf"$\displaystyle\lim_{{x \to \infty}} \dfrac{{{_lx(numer)}}}{{{_lx(denom)}}}$",
              correct_lx, wrong, expl, steps)


# ── Integral templates ────────────────────────────────────────────────────────

def gen_integral_power():
    """∫ axⁿ dx or ∫ trig dx or ∫ eˣ dx, indefinite."""
    choice = random.randint(0, 2)
    if choice == 0:
        a = random.choice([1, 2, 3, 4, -1])
        n = random.choice([Rational(1, 2), Rational(1, 3), 2, 3, 4, -2])
        expr = a * x**n
        correct = simplify(integrate(expr, x))
        c_lx = _lx(correct) + " + C"
        # Antiderivative wrong-exponent distractor
        d = [
            _lx(simplify(a * n * x**(n-1))) + " + C",
            _lx(simplify(a * x**(n+1))) + " + C",
            _lx(simplify(a / (n+1) * x**n)) + " + C",
            _lx(simplify(a * x**(n+2) / (n+2))) + " + C",
        ]
        expl = (
            rf"**Power rule for integrals:** $\int x^n\,dx = \frac{{x^{{n+1}}}}{{n+1}} + C$ $(n\neq -1)$. "
            rf"Here $n={_lx(n)}$, so $\int {_lx(expr)}\,dx = {c_lx}$."
        )
        steps = [
            r"Apply the **power rule for integrals:** $\int x^n\,dx = \dfrac{x^{n+1}}{n+1} + C$ (valid for $n \neq -1$).",
            rf"Here $n = {_lx(n)}$, so the new exponent is $n + 1 = {_lx(n+1)}$.",
            rf"Multiply by the coefficient ${_lx(a)}$ and divide by $n + 1$: ${c_lx}$.",
        ]
        return _q("integral_power", "integrals",
                  rf"$\displaystyle\int {_lx(expr)}\,dx =$",
                  c_lx, d, expl, steps)
    elif choice == 1:
        fn, fn_name, antideriv, sign = random.choice([
            (sin(x), r"\sin(x)", -cos(x), ""),
            (cos(x), r"\cos(x)", sin(x), ""),
        ])
        c_lx = _lx(antideriv) + " + C"
        d = [
            _lx(-antideriv) + " + C",
            _lx(fn) + " + C",
            _lx(-fn) + " + C",
            _lx(diff(fn, x)) + " + C",
        ]
        expl = (
            rf"**Trig integral rule.** "
            rf"$\int \sin x\,dx = -\cos x + C$; $\int \cos x\,dx = \sin x + C$. "
            rf"Answer: ${c_lx}$."
        )
        steps = [
            r"Recall the basic trig antiderivatives: $\int \sin x\,dx = -\cos x + C$ and $\int \cos x\,dx = \sin x + C$.",
            rf"Identify which rule applies to $\int {fn_name}\,dx$.",
            rf"Result: ${c_lx}$.",
        ]
        return _q("integral_trig", "integrals",
                  rf"$\displaystyle\int {fn_name}\,dx =$",
                  c_lx, d, expl, steps)
    else:
        c_lx = r"e^{x} + C"
        d = [r"e^{x-1} + C", r"\frac{e^{x+1}}{x+1} + C", r"xe^{x} + C", r"e^{x} \cdot x + C"]
        expl = r"**Exponential rule:** $\int e^x\,dx = e^x + C$."
        steps = [
            r"The exponential function is its own antiderivative.",
            r"Apply the rule: $\int e^x\,dx = e^x + C$.",
        ]
        return _q("integral_exp", "integrals",
                  r"$\displaystyle\int e^{x}\,dx =$",
                  c_lx, d, expl, steps)


def gen_integral_substitution():
    """u-substitution: ∫ f(g(x))·g′(x) dx."""
    choice = random.randint(0, 2)
    if choice == 0:
        # ∫ xⁿ·e^(x^(n+1)) dx   [like CLEP Q23]
        n = random.choice([2, 3])
        k = random.randint(1, 9)
        # ∫ x^n · e^(x^(n+1)+k) dx = e^(x^(n+1)+k)/(n+1) + C
        power = n + 1
        inner = x**power + k
        c_lx = rf"\frac{{1}}{{{power}}} e^{{{_lx(inner)}}} + C"
        d = [
            rf"e^{{{_lx(inner)}}} + C",
            rf"\frac{{x^{{{power}}}}}{{{power}}} e^{{{_lx(inner)}}} + C",
            rf"e^{{{_lx(x**power)}}} + C",
            rf"\frac{{1}}{{{n}}} e^{{{_lx(inner)}}} + C",
        ]
        expl = (
            rf"Let $u = {_lx(inner)}$, then $du = {power}x^{{{n}}}\,dx$, "
            rf"so $x^{{{n}}}\,dx = \frac{{1}}{{{power}}}du$. "
            rf"$\int e^u\cdot\frac{{1}}{{{power}}}\,du = \frac{{1}}{{{power}}}e^u + C = {c_lx}$."
        )
        steps = [
            rf"Pick the substitution $u = {_lx(inner)}$ since its derivative produces the $x^{{{n}}}$ factor.",
            rf"Differentiate: $du = {power}x^{{{n}}}\,dx$, so $x^{{{n}}}\,dx = \dfrac{{1}}{{{power}}}\,du$.",
            rf"Rewrite the integral in $u$: $\dfrac{{1}}{{{power}}}\int e^u\,du$.",
            rf"Integrate and substitute back: $\dfrac{{1}}{{{power}}}\,e^u + C = {c_lx}$.",
        ]
        expr_str = rf"x^{{{n}}} e^{{{_lx(inner)}}}"
        return _q("integral_sub_exp", "integrals",
                  rf"$\displaystyle\int {expr_str}\,dx =$",
                  c_lx, d, expl, steps)
    elif choice == 1:
        # ∫ cot²x csc²x dx = -cot³x/3 + C   [like CLEP Q30]
        c_lx = r"-\frac{\cot^{3} x}{3} + C"
        d = [
            r"-\frac{\csc^{3} x}{3} + C",
            r"\frac{\cot^{3} x}{3} + C",
            r"\frac{\csc^{3} x}{3} + C",
            r"\frac{\cot^{2} x}{2} + C",
        ]
        expl = (
            r"Let $u = \cot x$, $du = -\csc^2 x\,dx$. "
            r"$\int \cot^2 x \csc^2 x\,dx = -\int u^2\,du = -\frac{u^3}{3} + C = -\frac{\cot^3 x}{3} + C$."
        )
        steps = [
            r"Let $u = \cot x$. Then $du = -\csc^2 x\,dx$, so $\csc^2 x\,dx = -du$.",
            r"Rewrite the integral: $\int \cot^2 x \cdot \csc^2 x\,dx = -\int u^2\,du$.",
            r"Integrate in $u$: $-\dfrac{u^3}{3} + C$.",
            r"Substitute back: $-\dfrac{\cot^3 x}{3} + C$.",
        ]
        return _q("integral_sub_trig", "integrals",
                  r"$\displaystyle\int \cot^2 x \csc^2 x\,dx =$",
                  c_lx, d, expl, steps)
    else:
        # ∫ (ax+b)^n dx  simple linear substitution
        a_val = random.choice([2, 3])
        b_val = random.randint(-4, 4)
        n = random.randint(2, 4)
        inner_expr = a_val * x + b_val
        correct_sym = integrate((inner_expr)**n, x)
        c_lx = _lx(simplify(correct_sym)) + " + C"
        wrong_no_a = _lx(simplify((inner_expr)**(n+1) / (n+1))) + " + C"
        wrong_n    = _lx(simplify(a_val * n * (inner_expr)**(n-1))) + " + C"
        d = [wrong_no_a, wrong_n,
             _lx(simplify((inner_expr)**n / a_val)) + " + C",
             _lx(simplify((inner_expr)**(n+1))) + " + C"]
        expl = (
            rf"Let $u={_lx(inner_expr)}$, $du={a_val}\,dx$. "
            rf"$\frac{{1}}{{{a_val}}}\int u^{n}\,du = \frac{{u^{{{n+1}}}}}{{{a_val}({n+1})}} + C = {c_lx}$."
        )
        steps = [
            rf"Let $u = {_lx(inner_expr)}$.",
            rf"Then $du = {a_val}\,dx$, so $dx = \dfrac{{1}}{{{a_val}}}\,du$.",
            rf"Rewrite: $\dfrac{{1}}{{{a_val}}}\int u^{{{n}}}\,du = \dfrac{{u^{{{n+1}}}}}{{{a_val}({n+1})}} + C$.",
            rf"Substitute back: ${c_lx}$.",
        ]
        return _q("integral_sub_lin", "integrals",
                  rf"$\displaystyle\int ({_lx(inner_expr)})^{{{n}}}\,dx =$",
                  c_lx, d, expl, steps)


def gen_integral_definite():
    """Evaluate a definite integral numerically."""
    # Pick a simple function with clean answer
    choice = random.randint(0, 3)
    if choice == 0:
        a_val, b_val = random.choice([(0, 1), (1, 3), (-1, 2), (0, 2)])
        n = random.choice([2, 3])
        expr = x**n
        val = int(integrate(expr, (x, a_val, b_val)))
        c_lx = str(val)
        d = [str(val + d_) for d_ in [-1, 1, 2, -2]]
        expl = (
            rf"$\int_{{{a_val}}}^{{{b_val}}} x^{{{n}}}\,dx = "
            rf"\left[\frac{{x^{{{n+1}}}}}{{{n+1}}}\right]_{{{a_val}}}^{{{b_val}}} "
            rf"= \frac{{{b_val}^{{{n+1}}}}}{{{n+1}}} - \frac{{{a_val}^{{{n+1}}}}}{{{n+1}}} = {val}$."
        )
        steps = [
            rf"Find the antiderivative: $\int x^{{{n}}}\,dx = \dfrac{{x^{{{n+1}}}}}{{{n+1}}}$.",
            rf"Evaluate at the upper limit $x = {b_val}$: $\dfrac{{{b_val}^{{{n+1}}}}}{{{n+1}}}$.",
            rf"Subtract value at lower limit $x = {a_val}$: $\dfrac{{{a_val}^{{{n+1}}}}}{{{n+1}}}$.",
            rf"Simplify: ${val}$.",
        ]
        return _q("integral_def_power", "integrals",
                  rf"$\displaystyle\int_{{{a_val}}}^{{{b_val}}} x^{{{n}}}\,dx =$",
                  c_lx, d, expl, steps)
    elif choice == 1:
        # ∫_a^b 1/(x+1) dx  [like CLEP Q15]
        a_val, b_val = random.choice([(-4, -2), (0, 2), (1, 4)])
        val_sym = integrate(1 / (x + 1), (x, a_val, b_val))
        # Express as ln difference
        top = abs(b_val + 1)
        bot = abs(a_val + 1)
        if top > bot:
            c_lx = rf"\ln {top} - \ln {bot}"
        else:
            c_lx = rf"-\ln {bot} + \ln {top}"
        num_val = float(val_sym)
        d = [rf"\ln {top+1} - \ln {bot}", rf"-\ln {bot}", rf"\ln {top}", str(round(num_val, 1))]
        expl = (
            rf"$\int\frac{{1}}{{x+1}}\,dx = \ln|x+1| + C$. "
            rf"Evaluate from ${a_val}$ to ${b_val}$: $\ln|{b_val}+1| - \ln|{a_val}+1| = {c_lx}$."
        )
        steps = [
            r"Antiderivative: $\int \dfrac{1}{x+1}\,dx = \ln|x+1| + C$.",
            rf"Evaluate at upper limit $x = {b_val}$: $\ln|{b_val}+1|$.",
            rf"Subtract value at lower limit $x = {a_val}$: $\ln|{a_val}+1|$.",
            rf"Combine: ${c_lx}$.",
        ]
        return _q("integral_def_log", "integrals",
                  rf"$\displaystyle\int_{{{a_val}}}^{{{b_val}}} \dfrac{{1}}{{x+1}}\,dx =$",
                  c_lx, d, expl, steps)
    elif choice == 2:
        a_val, b_val = 0, random.choice([1, 2, 3])
        # ∫ e^x dx = e^b - 1
        val_sym = sp.nsimplify(integrate(exp(x), (x, a_val, b_val)))
        c_lx = _lx(val_sym)
        d = [_lx(exp(sp.Integer(b_val))), "1", _lx(exp(sp.Integer(b_val)) + 1),
             _lx(exp(sp.Integer(b_val)) - sp.E)]
        expl = (
            rf"$\int e^x\,dx = e^x + C$. "
            rf"$\left[e^x\right]_0^{{{b_val}}} = e^{{{b_val}}} - e^0 = {c_lx}$."
        )
        steps = [
            r"Antiderivative: $\int e^x\,dx = e^x + C$.",
            rf"Evaluate at $x = {b_val}$: $e^{{{b_val}}}$.",
            rf"Subtract value at $x = 0$: $e^0 = 1$.",
            rf"Result: $e^{{{b_val}}} - 1 = {c_lx}$.",
        ]
        return _q("integral_def_exp", "integrals",
                  rf"$\displaystyle\int_0^{{{b_val}}} e^x\,dx =$",
                  c_lx, d, expl, steps)
    else:
        # ∫_a^b polynomial
        a_val, b_val = random.choice([(0, 2), (-1, 1), (0, 3), (1, 4)])
        coef = random.randint(1, 4)
        expr = coef * x**2
        val = int(integrate(expr, (x, a_val, b_val)))
        c_lx = str(val)
        d = [str(val + d_) for d_ in [-2, 2, 3, -3]]
        expl = (
            rf"$\int_{{{a_val}}}^{{{b_val}}} {_lx(expr)}\,dx = "
            rf"\left[{_lx(coef * x**3 / 3)}\right]_{{{a_val}}}^{{{b_val}}} = {val}$."
        )
        steps = [
            rf"Find the antiderivative of ${_lx(expr)}$ using the power rule: ${_lx(coef * x**3 / 3)}$.",
            rf"Evaluate at upper limit $x = {b_val}$ and subtract the value at $x = {a_val}$.",
            rf"Result: ${val}$.",
        ]
        return _q("integral_def_poly", "integrals",
                  rf"$\displaystyle\int_{{{a_val}}}^{{{b_val}}} {_lx(expr)}\,dx =$",
                  c_lx, d, expl, steps)


# ── Application templates ─────────────────────────────────────────────────────

def gen_app_velocity():
    """Position/velocity/acceleration problems. Like CLEP Q8, Q26."""
    choice = random.randint(0, 1)
    if choice == 0:
        # Projectile: s(t) = -16t² + v0*t + s0; find height when v=0
        v0 = random.choice([64, 128, 256])
        s0 = random.choice([10, 50, 100])
        expr = -16 * t**2 + v0 * t + s0
        vel = diff(expr, t)
        t_star = int((-v0) / (-32))   # = v0/32
        height = int(expr.subs(t, t_star))
        c_lx = str(height)
        wrong = [str(height + d_) for d_ in [-100, 100, 200, -200]]
        expl = (
            rf"$v(t) = s'(t) = {_lx(vel)}$. Set $v=0$: $t = {t_star}$ sec. "
            rf"Height: $s({t_star}) = -16({t_star})^2 + {v0}({t_star}) + {s0} = {height}$ ft."
        )
        steps = [
            rf"Velocity is the derivative of position: $v(t) = s'(t) = {_lx(vel)}$.",
            rf"Set $v(t) = 0$ and solve for $t$: $t = {t_star}$ seconds.",
            rf"Substitute $t = {t_star}$ into $s(t)$ to find the height.",
            rf"Result: $s({t_star}) = {height}$ ft.",
        ]
        return _q("app_velocity", "applications",
                  rf"The height (ft) of a ball is $s(t)={_lx(expr)}$ where $t$ is in seconds. "
                  rf"What is the height when the velocity is zero?",
                  c_lx, wrong, expl, steps)
    else:
        # Given acceleration, find position at t=1 with ICs
        n = random.randint(2, 3)
        a_val = random.randint(1, 4)
        acc_expr = a_val * t**n
        vel_expr = integrate(acc_expr, t)           # no constant since v(0)=0
        pos_expr = integrate(vel_expr, t) + sp.Integer(12)  # s(0)=12
        val = pos_expr.subs(t, 1)
        val_num = float(val)
        c_lx = str(round(val_num, 1))
        wrong = [str(round(val_num + d_, 1)) for d_ in [-1, 0.5, 1.5, -0.5]]
        expl = (
            rf"Integrate $a(t)={_lx(acc_expr)}$ to get $v(t)={_lx(vel_expr)}$ (since $v(0)=0$). "
            rf"Integrate again: $s(t)={_lx(pos_expr)}$. "
            rf"At $t=1$: $s(1)\approx{c_lx}$."
        )
        steps = [
            rf"Integrate acceleration to find velocity: $v(t) = \int {_lx(acc_expr)}\,dt = {_lx(vel_expr)}$. (Constant is $0$ because $v(0) = 0$.)",
            rf"Integrate velocity to find position: $s(t) = \int v(t)\,dt + 12 = {_lx(pos_expr)}$. (Constant is $12$ because $s(0) = 12$.)",
            rf"Evaluate at $t = 1$: $s(1) \approx {c_lx}$.",
        ]
        return _q("app_accel", "applications",
                  rf"A particle's acceleration is $a(t)={_lx(acc_expr)}$. "
                  rf"At $t=0$, velocity is 0 and position is 12. What is the position at $t=1$?",
                  c_lx, wrong, expl, steps)


def gen_app_ftc():
    """Fundamental Theorem of Calculus, variable upper limit. Like CLEP Q32."""
    fn, fn_name, antideriv = random.choice([
        (sin(x), r"\sin t", -cos(x)),
        (cos(x), r"\cos t", sin(x)),
        (exp(x), r"e^t",    exp(x)),
        (t**2,   r"t^2",    x**2),
    ])
    pt = random.choice([
        (sp.pi / 6,   r"\pi/6"),
        (sp.pi / 4,   r"\pi/4"),
        (sp.pi / 3,   r"\pi/3"),
        (sp.pi / 2,   r"\pi/2"),
        (sp.Integer(1), r"1"),
        (sp.Integer(2), r"2"),
    ])
    pt_val, pt_str = pt
    val_sym = simplify(fn.subs(x, pt_val))
    c_lx = _lx(val_sym)

    d = [
        _lx(simplify(-val_sym)),
        _lx(simplify(antideriv.subs(x, pt_val))),
        c_lx + r" + C",
        _lx(simplify(diff(fn.subs(x, pt_val), pt_val))) if hasattr(pt_val, 'free_symbols') else "0",
    ]
    expl = (
        rf"By the **Fundamental Theorem:** $F'(x) = f(x)$, so "
        rf"$F'({pt_str}) = {fn_name.replace('t', pt_str)} = {c_lx}$."
    )
    steps = [
        r"By the **Fundamental Theorem of Calculus:** if $F(x) = \int_0^x f(t)\,dt$, then $F'(x) = f(x)$.",
        rf"So $F'(x) = {fn_name.replace('t', 'x')}$.",
        rf"Substitute $x = {pt_str}$: $F'({pt_str}) = {c_lx}$.",
    ]
    return _q("app_ftc", "applications",
              rf"If $F(x) = \displaystyle\int_0^x {fn_name}\,dt$, then $F'\!\left({pt_str}\right) =$",
              c_lx, d, expl, steps)


def gen_app_average_value():
    """Average value of function on [a,b]: (1/(b-a))∫_a^b f dx. Like CLEP Q12, Q35."""
    choice = random.randint(0, 1)
    if choice == 0:
        a_val, b_val = -1, 2
        coef = random.choice([4, 8])
        expr = coef * x**3 + random.randint(1, 3) * x + 1
        avg = simplify(integrate(expr, (x, a_val, b_val)) / (b_val - a_val))
        c_lx = _lx(avg)
        d = [str(int(avg) + d_) for d_ in [-3, 3, 6, -6]]
        expl = (
            rf"**Average value** $= \frac{{1}}{{{b_val}-({a_val})}}\int_{{{a_val}}}^{{{b_val}}} f(x)\,dx$. "
            rf"Compute the integral, divide by ${b_val - a_val}$: ${c_lx}$."
        )
        steps = [
            r"Use the **average value** formula: $\bar f = \dfrac{1}{b - a}\int_a^b f(x)\,dx$.",
            rf"Here $b - a = {b_val} - ({a_val}) = {b_val - a_val}$.",
            rf"Compute $\int_{{{a_val}}}^{{{b_val}}} \left({_lx(expr)}\right)\,dx$.",
            rf"Divide the integral by ${b_val - a_val}$: ${c_lx}$.",
        ]
        return _q("app_avg_val", "applications",
                  rf"What is the average value of $f(x)={_lx(expr)}$ on $[{a_val},{b_val}]$?",
                  c_lx, d, expl, steps)
    else:
        # Average rate of change: (f(b)-f(a))/(b-a)  like CLEP Q35
        fn, fn_name = random.choice([(cos(x), r"\cos x"), (sin(x), r"\sin x")])
        a_val, b_val_sym, b_str = 0, sp.pi, r"\pi"
        val = simplify((fn.subs(x, b_val_sym) - fn.subs(x, a_val)) / (b_val_sym - a_val))
        c_lx = _lx(val)
        d = [_lx(-val), _lx(sp.pi), _lx(Rational(2, 1) / sp.pi), _lx(Rational(-1, 2))]
        expl = (
            rf"**Average rate of change** $= \frac{{f({b_str})-f(0)}}{{{b_str}-0}} = "
            rf"\frac{{{_lx(fn.subs(x,sp.pi))}-{_lx(fn.subs(x,0))}}}{{\pi}} = {c_lx}$."
        )
        steps = [
            r"Use the **average rate of change** formula: $\dfrac{f(b) - f(a)}{b - a}$.",
            rf"Compute $f({b_str}) = {_lx(fn.subs(x, sp.pi))}$ and $f(0) = {_lx(fn.subs(x, 0))}$.",
            rf"Divide the difference by $\pi - 0 = \pi$: ${c_lx}$.",
        ]
        return _q("app_avg_rate", "applications",
                  rf"What is the average rate of change of $f(x) = {fn_name}$ on $[0,\pi]$?",
                  c_lx, d, expl, steps)


def gen_app_optimization():
    """Max/min of polynomial. Like CLEP Q37, Q40."""
    choice = random.randint(0, 1)
    if choice == 0:
        # Fencing: maximize area A = x*(L - 2x)
        L = random.choice([100, 120, 80])
        # A = Lx - 2x² → A' = L - 4x = 0 → x = L/4; parallel side = L - 2*(L/4) = L/2
        x_opt = L // 4
        parallel = L - 2 * x_opt
        c_lx = str(parallel)
        d = [str(parallel + d_) for d_ in [-10, 10, 25, -25]]
        expl = (
            rf"Let $x$ = perpendicular side. Parallel side $= {L} - 2x$. "
            rf"$A = x({L}-2x) = {L}x - 2x^2$. $A' = {L}-4x = 0 \Rightarrow x = {x_opt}$. "
            rf"Parallel side $= {L} - 2({x_opt}) = {parallel}$ yards."
        )
        steps = [
            rf"Let $x$ be the perpendicular side. The parallel side uses the rest of the fence: ${L} - 2x$.",
            rf"Area as a function of $x$: $A(x) = x({L} - 2x) = {L}x - 2x^2$.",
            rf"Maximize: set $A'(x) = {L} - 4x = 0$, giving $x = {x_opt}$.",
            rf"Parallel side $= {L} - 2({x_opt}) = {parallel}$ yards.",
        ]
        return _q("app_optimize_fence", "applications",
                  rf"A rectangular field borders a river (no fence needed on that side). "
                  rf"With {L} yards of fencing for 3 sides, what length parallel to the river "
                  rf"maximizes the area?",
                  c_lx, d, expl, steps)
    else:
        # Find critical point of cubic
        a_c = random.choice([3, 4])
        b_c = random.choice([-3, -4])
        expr = a_c * x**4 + b_c * x**3
        deriv_expr = diff(expr, x)
        critical = [pt for pt in sp.solve(deriv_expr, x) if pt != 0]
        if not critical:
            return gen_app_optimization()
        pt_crit = critical[0]
        second_d = diff(deriv_expr, x).subs(x, pt_crit)
        verdict = "relative minimum" if second_d > 0 else "relative maximum"
        c_lx = rf"\text{{one {verdict} and two inflection points}}"
        wrong = [
            r"\text{no relative extrema and no inflection points}",
            r"\text{one relative maximum, one minimum, one inflection point}",
            r"\text{one relative maximum and two inflection points}",
            r"\text{three inflection points}",
        ]
        expl = (
            rf"$f'(x) = {_lx(deriv_expr)}$. Critical numbers: $x=0$ and $x={_lx(pt_crit)}$. "
            rf"$f''(x) = {_lx(diff(deriv_expr,x))}$. "
            rf"$f''({_lx(pt_crit)}) {'>0' if second_d > 0 else '<0'} \Rightarrow$ {verdict} there. "
            rf"Two inflection points exist."
        )
        steps = [
            rf"Compute $f'(x) = {_lx(deriv_expr)}$.",
            rf"Find critical numbers by solving $f'(x) = 0$: $x = 0$ and $x = {_lx(pt_crit)}$.",
            rf"Apply the second derivative test: $f''(x) = {_lx(diff(deriv_expr, x))}$, and $f''({_lx(pt_crit)}) {'> 0' if second_d > 0 else '< 0'}$, so there is a {verdict}.",
            r"Inflection points occur where $f''(x) = 0$ and concavity changes — two such points exist.",
        ]
        return _q("app_optimize_crit", "applications",
                  rf"Which is true about $f(x)={_lx(expr)}$?",
                  c_lx, wrong, expl, steps)


# ── Registry ──────────────────────────────────────────────────────────────────

# Each entry: (generator_fn, count_in_45_question_exam)
_REGISTRY = [
    (gen_deriv_power,            5),
    (gen_deriv_product_quotient, 4),
    (gen_deriv_chain,            3),
    (gen_deriv_tangent_line,     2),
    (gen_limit_direct,           3),
    (gen_limit_zero_zero,        3),
    (gen_limit_infinity,         2),
    (gen_integral_power,         5),
    (gen_integral_substitution,  4),
    (gen_integral_definite,      4),
    (gen_app_velocity,           3),
    (gen_app_ftc,                3),
    (gen_app_average_value,      2),
    (gen_app_optimization,       2),
]
# Total = 45 ✓

_TOPIC_MAP = {
    "derivatives":   [gen_deriv_power, gen_deriv_product_quotient, gen_deriv_chain, gen_deriv_tangent_line],
    "limits":        [gen_limit_direct, gen_limit_zero_zero, gen_limit_infinity],
    "integrals":     [gen_integral_power, gen_integral_substitution, gen_integral_definite],
    "applications":  [gen_app_velocity, gen_app_ftc, gen_app_average_value, gen_app_optimization],
}

VALID_TOPICS = ["all"] + list(_TOPIC_MAP.keys())


def choose_question(topic: str = "all") -> dict:
    """Return one random CLEP-style question."""
    if topic and topic != "all" and topic in _TOPIC_MAP:
        fn = random.choice(_TOPIC_MAP[topic])
    else:
        fn = random.choice([g for g, _ in _REGISTRY])
    for _ in range(5):   # retry on rare exceptions
        try:
            return fn()
        except Exception:
            fn = random.choice([g for g, _ in _REGISTRY])
    return gen_deriv_power()   # safe fallback


def build_exam(n: int = 45) -> list:
    """Return n questions sampled proportionally across CLEP topics."""
    questions = []
    for fn, count in _REGISTRY:
        added = 0
        for attempt in range(count * 8):   # extra retries
            if added >= count:
                break
            try:
                questions.append(fn())
                added += 1
            except Exception:
                pass
    # Fill any gap with random questions
    while len(questions) < n:
        try:
            questions.append(choose_question())
        except Exception:
            pass
    random.shuffle(questions)
    return questions[:n]
