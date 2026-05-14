import random
import sympy as sp
from sympy import symbols, diff, integrate
from sympy import latex as _sympy_latex
from sympy.parsing.latex import parse_latex as _parse_latex


def latex(expr, **kwargs):
    """Wrapper that always uses \ln notation for natural log."""
    kwargs.setdefault("ln_notation", True)
    return _sympy_latex(expr, **kwargs)

x = symbols("x")

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_expr(latex_str: str) -> sp.Expr:
    try:
        expr = _parse_latex(latex_str)
        # Normalise symbols: x → our x, e → Euler's number, pi → π
        expr = expr.subs([
            (symbols("x"),  x),
            (symbols("e"),  sp.E),
            (symbols("pi"), sp.pi),
        ])
        return expr
    except Exception as exc:
        raise ValueError(f"Could not parse expression: {exc}") from exc


# ---------------------------------------------------------------------------
# Public solvers
# ---------------------------------------------------------------------------

def solve_derivative(latex_str: str) -> dict:
    expr = parse_expr(latex_str)
    expr_latex = latex(expr)
    problem = rf"\frac{{d}}{{dx}}\left[{expr_latex}\right]"
    steps = _deriv_steps(expr)
    result = diff(expr, x)
    result_latex = latex(result)
    steps.append(rf"**Final answer:** $\frac{{d}}{{dx}}\left[{expr_latex}\right] = {result_latex}$")
    return {
        "problem_latex": problem,
        "result_latex": result_latex,
        "steps": steps,
    }


def solve_integral(latex_str: str) -> dict:
    expr = parse_expr(latex_str)
    expr_latex = latex(expr)
    problem = rf"\int {expr_latex}\, dx"
    steps = _integral_steps(expr)
    result = integrate(expr, x)
    result_latex = latex(result) + " + C"
    steps.append(rf"**Final answer:** $\int {expr_latex}\, dx = {latex(result)} + C$")
    return {
        "problem_latex": problem,
        "result_latex": result_latex,
        "steps": steps,
    }


def solve_limit(latex_str: str, point_latex: str, direction: str) -> dict:
    expr = parse_expr(latex_str)
    point = parse_expr(point_latex)
    expr_latex = latex(expr)
    point_l = latex(point)

    dir_map = {"right": "+", "left": "-", "both": "+-"}
    sp_dir = dir_map.get(direction, "+-")
    dir_sup = {"right": "^+", "left": "^-", "both": ""}.get(direction, "")

    problem = rf"\lim_{{x \to {point_l}{dir_sup}}} {expr_latex}"
    steps = _limit_steps(expr, point, sp_dir, point_l, dir_sup)
    result = sp.limit(expr, x, point, sp_dir)
    result_latex = latex(result)
    steps.append(rf"**Final answer:** ${problem} = {result_latex}$")
    return {
        "problem_latex": problem,
        "result_latex": result_latex,
        "steps": steps,
    }


def generate_similar(latex_str: str, op_type: str) -> list:
    try:
        expr = parse_expr(latex_str)
    except Exception:
        return []
    return _build_variants(expr)


# ---------------------------------------------------------------------------
# Limit steps
# ---------------------------------------------------------------------------

def _limit_steps(expr, point, sp_dir, point_l, dir_sup):
    steps = []

    # 1. Try direct substitution
    try:
        direct = expr.subs(x, point)
        direct_s = sp.simplify(direct)
        is_bad = direct_s in (sp.nan, sp.zoo) or not direct_s.is_finite
        if not is_bad:
            steps.append(
                rf"**Direct substitution:** plug $x = {point_l}$ into the expression"
            )
            steps.append(rf"$= {latex(direct_s)}$")
            return steps
    except Exception:
        pass

    # 2. Check for 0/0 or ∞/∞ via fraction form → L'Hôpital's rule
    try:
        numer, denom = sp.fraction(sp.together(expr))
        if denom != sp.S.One:
            n_val = sp.limit(numer, x, point, sp_dir)
            d_val = sp.limit(denom, x, point, sp_dir)
            n_inf = n_val in (sp.oo, -sp.oo)
            d_inf = d_val in (sp.oo, -sp.oo)
            n_zero = (n_val == sp.S.Zero)
            d_zero = (d_val == sp.S.Zero)

            if (n_zero and d_zero) or (n_inf and d_inf):
                form = r"\frac{0}{0}" if (n_zero and d_zero) else r"\frac{\infty}{\infty}"
                steps.append(
                    rf"**Direct substitution** gives the indeterminate form ${form}$"
                )
                steps.append(
                    rf"**L'Hôpital's rule:** $\lim \frac{{f(x)}}{{g(x)}} = \lim \frac{{f'(x)}}{{g'(x)}}$ "
                    rf"when the form is $\frac{{0}}{{0}}$ or $\frac{{\infty}}{{\infty}}$"
                )
                dn = diff(numer, x)
                dd = diff(denom, x)
                steps.append(
                    rf"Differentiate numerator: $\frac{{d}}{{dx}}\left[{latex(numer)}\right] = {latex(dn)}$"
                )
                steps.append(
                    rf"Differentiate denominator: $\frac{{d}}{{dx}}\left[{latex(denom)}\right] = {latex(dd)}$"
                )
                new_expr = sp.simplify(dn / dd)
                steps.append(
                    rf"New limit: $\lim_{{x \to {point_l}{dir_sup}}} {latex(new_expr)}$"
                )
                # Substitute into the new expression
                try:
                    new_val = sp.simplify(new_expr.subs(x, point))
                    if new_val.is_finite:
                        steps.append(rf"Substitute $x = {point_l}$: $= {latex(new_val)}$")
                except Exception:
                    pass
                return steps
    except Exception:
        pass

    # 3. Detect sin(x)/x → 1 type special limits
    try:
        if point == sp.S.Zero:
            simplified = sp.simplify(expr)
            expr_str = str(simplified)
            if "sin" in expr_str and "x" in expr_str:
                result = sp.limit(expr, x, sp.S.Zero, sp_dir)
                if result == sp.S.One:
                    steps.append(
                        rf"**Special trig limit:** $\lim_{{x \to 0}} \frac{{\sin(x)}}{{x}} = 1$ "
                        rf"(a fundamental calculus identity)"
                    )
                    steps.append(rf"Applying this identity: limit $= 1$")
                    return steps
    except Exception:
        pass

    # 4. Generic fallback — describe the approach conceptually
    steps.append(
        rf"**Evaluate** $\lim_{{x \to {point_l}{dir_sup}}} {latex(expr)}$ "
        rf"by applying limit laws and simplification"
    )
    return steps


# ---------------------------------------------------------------------------
# Derivative steps
# ---------------------------------------------------------------------------

def _deriv_steps(expr: sp.Expr) -> list:
    steps = []
    _deriv_recurse(expr, steps, depth=0)
    return steps


def _deriv_recurse(expr, steps, depth):
    pad = "&nbsp;" * (depth * 4)

    # --- Constant ---
    if not expr.has(x):
        steps.append(
            rf"{pad}**Constant rule:** $\frac{{d}}{{dx}}\left[{latex(expr)}\right] = 0$"
        )
        return

    # --- x itself ---
    if expr == x:
        steps.append(rf"{pad}**Power rule:** $\frac{{d}}{{dx}}[x] = 1$")
        return

    # --- Sum / Difference ---
    if isinstance(expr, sp.Add):
        steps.append(
            rf"{pad}**Sum/Difference rule:** differentiate each term of "
            rf"${latex(expr)}$ separately"
        )
        for term in expr.args:
            _deriv_recurse(term, steps, depth + 1)
        return

    # --- Mul: constant multiple or product rule ---
    if isinstance(expr, sp.Mul):
        coeff, rest = expr.as_coeff_Mul()
        if coeff != 1 and rest.has(x):
            steps.append(
                rf"{pad}**Constant multiple rule:** "
                rf"$\frac{{d}}{{dx}}\left[{latex(coeff)} \cdot {latex(rest)}\right]"
                rf" = {latex(coeff)} \cdot \frac{{d}}{{dx}}\left[{latex(rest)}\right]$"
            )
            _deriv_recurse(rest, steps, depth + 1)
            return
        var_factors = [f for f in expr.args if f.has(x)]
        if len(var_factors) >= 2:
            f = var_factors[0]
            g = sp.Mul(*var_factors[1:]) if len(var_factors) > 2 else var_factors[1]
            fp = diff(f, x)
            gp = diff(g, x)
            product_result = sp.expand(f * gp + g * fp)
            steps.append(
                rf"{pad}**Product rule:** "
                rf"$\frac{{d}}{{dx}}\left[{latex(f)} \cdot {latex(g)}\right] = "
                rf"{latex(f)} \cdot \frac{{d}}{{dx}}\left[{latex(g)}\right] + "
                rf"{latex(g)} \cdot \frac{{d}}{{dx}}\left[{latex(f)}\right]$"
            )
            steps.append(
                rf"{pad}$= {latex(f)} \cdot ({latex(gp)}) + {latex(g)} \cdot ({latex(fp)}) = {latex(product_result)}$"
            )
            return

    # --- Pow ---
    if isinstance(expr, sp.Pow):
        base, exp_val = expr.args
        if not exp_val.has(x):
            reduced = sp.simplify(base ** (exp_val - 1))
            if base == x:
                steps.append(
                    rf"{pad}**Power rule:** "
                    rf"$\frac{{d}}{{dx}}\left[x^{{{latex(exp_val)}}}\right] = "
                    rf"{latex(exp_val)} \cdot {latex(reduced)}$"
                )
            else:
                steps.append(
                    rf"{pad}**Chain rule + Power rule:** "
                    rf"$\frac{{d}}{{dx}}\left[\left({latex(base)}\right)^{{{latex(exp_val)}}}\right] = "
                    rf"{latex(exp_val)} \cdot {latex(reduced)} "
                    rf"\cdot \frac{{d}}{{dx}}\left[{latex(base)}\right]$"
                )
                _deriv_recurse(base, steps, depth + 1)
            return
        if not base.has(x):
            steps.append(
                rf"{pad}**Exponential rule (base {latex(base)}):** "
                rf"$\frac{{d}}{{dx}}\left[{latex(base)}^{{{latex(exp_val)}}}\right] = "
                rf"{latex(base)}^{{{latex(exp_val)}}} \cdot \ln({latex(base)}) \cdot "
                rf"\frac{{d}}{{dx}}\left[{latex(exp_val)}\right]$"
            )
            _deriv_recurse(exp_val, steps, depth + 1)
            return

    # Normalise E**f(x) → exp(f(x)) so the exp branch handles it cleanly
    if isinstance(expr, sp.Pow) and expr.base == sp.E:
        expr = sp.exp(expr.exp)

    # --- exp ---
    if isinstance(expr, sp.exp):
        inner = expr.args[0]
        inner_l = latex(inner)
        if inner == x:
            steps.append(
                rf"{pad}**Exponential rule:** $\frac{{d}}{{dx}}\left[e^x\right] = e^x$"
            )
        else:
            steps.append(
                rf"{pad}**Chain rule:** "
                rf"$\frac{{d}}{{dx}}\left[e^{{{inner_l}}}\right] = "
                rf"e^{{{inner_l}}} \cdot \frac{{d}}{{dx}}\left[{inner_l}\right]$"
            )
            _deriv_recurse(inner, steps, depth + 1)
        return

    # --- log ---
    if isinstance(expr, sp.log):
        inner = expr.args[0]
        inner_l = latex(inner)
        if inner == x:
            steps.append(
                rf"{pad}**Logarithm rule:** $\frac{{d}}{{dx}}\left[\ln(x)\right] = \frac{{1}}{{x}}$"
            )
        else:
            steps.append(
                rf"{pad}**Chain rule:** "
                rf"$\frac{{d}}{{dx}}\left[\ln({inner_l})\right] = "
                rf"\frac{{1}}{{{inner_l}}} \cdot \frac{{d}}{{dx}}\left[{inner_l}\right]$"
            )
            _deriv_recurse(inner, steps, depth + 1)
        return

    # --- Trig functions ---
    trig_rules = [
        (sp.sin,  r"\sin",    r"\cos({i})",                        r"-\sin({i})"),
        (sp.cos,  r"\cos",    r"-\sin({i})",                       r"\cos({i})"),
        (sp.tan,  r"\tan",    r"\sec^2({i})",                      None),
        (sp.cot,  r"\cot",    r"-\csc^2({i})",                     None),
        (sp.sec,  r"\sec",    r"\sec({i})\tan({i})",               None),
        (sp.csc,  r"\csc",    r"-\csc({i})\cot({i})",              None),
        (sp.asin, r"\arcsin", r"\frac{{1}}{{\sqrt{{1-({i})^2}}}}", None),
        (sp.acos, r"\arccos", r"-\frac{{1}}{{\sqrt{{1-({i})^2}}}}", None),
        (sp.atan, r"\arctan", r"\frac{{1}}{{1+({i})^2}}",          None),
    ]
    for fn_cls, fn_name, deriv_tmpl, _ in trig_rules:
        if isinstance(expr, fn_cls):
            inner = expr.args[0]
            inner_l = latex(inner)
            deriv_str = deriv_tmpl.replace("{i}", inner_l)
            if inner == x:
                steps.append(
                    rf"{pad}**Trig rule:** "
                    rf"$\frac{{d}}{{dx}}\left[{fn_name}(x)\right] = {deriv_str}$"
                )
            else:
                steps.append(
                    rf"{pad}**Chain rule:** "
                    rf"$\frac{{d}}{{dx}}\left[{fn_name}({inner_l})\right] = "
                    rf"{deriv_str} \cdot \frac{{d}}{{dx}}\left[{inner_l}\right]$"
                )
                _deriv_recurse(inner, steps, depth + 1)
            return

    # --- Quotient rule fallback (Mul with negative power) ---
    # --- Generic fallback ---
    result = diff(expr, x)
    steps.append(
        rf"{pad}**Differentiate:** $\frac{{d}}{{dx}}\left[{latex(expr)}\right] = {latex(result)}$"
    )


# ---------------------------------------------------------------------------
# Integral steps
# ---------------------------------------------------------------------------

def _integral_steps(expr: sp.Expr) -> list:
    steps = []
    try:
        from sympy.integrals.manualintegrate import integral_steps
        rule = integral_steps(expr, x)
        _walk_rule(rule, steps, depth=0)
    except Exception:
        steps.append(
            rf"**Computing** $\int {latex(expr)}\, dx$ using standard integration techniques..."
        )
    return steps


def _walk_rule(rule, steps, depth):
    pad = "&nbsp;" * (depth * 4)
    rtype = type(rule).__name__

    try:
        if rtype == "PowerRule":
            n = getattr(rule, "exp", None)
            base = getattr(rule, "base", x)
            if n is not None and n != -1:
                steps.append(
                    rf"{pad}**Power rule:** "
                    rf"$\int {latex(base)}^{{{latex(n)}}}\, dx = "
                    rf"\frac{{{latex(base)}^{{{latex(n + 1)}}}}}{{{latex(n + 1)}}} + C$"
                )
            else:
                steps.append(rf"{pad}**Power rule** applied")

        elif rtype == "ConstantRule":
            c = getattr(rule, "constant", "c")
            steps.append(
                rf"{pad}**Constant rule:** $\int {latex(c)}\, dx = {latex(c)} x + C$"
            )

        elif rtype == "ConstantTimesRule":
            const = getattr(rule, "constant", None)
            other = getattr(rule, "other", None)
            substep = getattr(rule, "substep", None)
            if const is not None and other is not None:
                steps.append(
                    rf"{pad}**Constant multiple rule:** factor out ${latex(const)}$: "
                    rf"$\int {latex(const)} \cdot {latex(other)}\, dx = "
                    rf"{latex(const)} \int {latex(other)}\, dx$"
                )
            if substep is not None:
                _walk_rule(substep, steps, depth + 1)

        elif rtype == "AddRule":
            steps.append(rf"{pad}**Sum rule:** integrate term by term")
            for sub in getattr(rule, "substeps", []):
                _walk_rule(sub, steps, depth + 1)

        elif rtype == "SinRule":
            integrand = getattr(rule, "integrand", None)
            arg_l = latex(integrand.args[0]) if integrand is not None else "x"
            steps.append(
                rf"{pad}**Trig rule:** $\int \sin({arg_l})\, dx = -\cos({arg_l}) + C$"
            )

        elif rtype == "CosRule":
            integrand = getattr(rule, "integrand", None)
            arg_l = latex(integrand.args[0]) if integrand is not None else "x"
            steps.append(
                rf"{pad}**Trig rule:** $\int \cos({arg_l})\, dx = \sin({arg_l}) + C$"
            )

        elif rtype == "TrigRule":
            func = str(getattr(rule, "func", ""))
            arg = getattr(rule, "arg", x)
            arg_l = latex(arg)
            trig_map = {
                "sin":   rf"-\cos({arg_l})",
                "cos":   rf"\sin({arg_l})",
                "tan":   rf"-\ln|\cos({arg_l})|",
                "cot":   rf"\ln|\sin({arg_l})|",
                "sec":   rf"\ln|\sec({arg_l})+\tan({arg_l})|",
                "csc":   rf"-\ln|\csc({arg_l})+\cot({arg_l})|",
            }
            result_str = trig_map.get(func, r"\text{(trig result)}")
            steps.append(
                rf"{pad}**Trig rule:** $\int \{func}({arg_l})\, dx = {result_str} + C$"
            )

        elif rtype == "RewriteRule":
            rewritten = getattr(rule, "rewritten", None)
            substep = getattr(rule, "substep", None)
            if rewritten is not None:
                steps.append(
                    rf"{pad}**Rewrite:** express as $\int {latex(rewritten)}\, dx$"
                )
            if substep is not None:
                _walk_rule(substep, steps, depth + 1)

        elif rtype == "ExpRule":
            base = getattr(rule, "base", sp.E)
            exp_ = getattr(rule, "exp", x)
            exp_l = latex(exp_)
            if base == sp.E:
                steps.append(
                    rf"{pad}**Exponential rule:** "
                    rf"$\int e^{{{exp_l}}}\, dx = e^{{{exp_l}}} + C$"
                )
            else:
                base_l = latex(base)
                steps.append(
                    rf"{pad}**Exponential rule:** "
                    rf"$\int {base_l}^{{{exp_l}}}\, dx = \frac{{{base_l}^{{{exp_l}}}}}{{\ln {base_l}}} + C$"
                )

        elif rtype == "LogRule":
            steps.append(
                rf"{pad}**Log rule:** $\int \frac{{1}}{{x}}\, dx = \ln|x| + C$"
            )

        elif rtype == "ReciprocalRule":
            func = getattr(rule, "func", None)
            steps.append(
                rf"{pad}**Reciprocal rule:** $\int \frac{{1}}{{x}}\, dx = \ln|x| + C$"
            )

        elif rtype == "URule":
            u_func = getattr(rule, "u_func", None)
            substep = getattr(rule, "substep", None)
            if u_func is not None:
                du = diff(u_func, x)
                steps.append(
                    rf"{pad}**U-substitution:** let $u = {latex(u_func)}$, "
                    rf"so $du = {latex(du)}\, dx$"
                )
            if substep is not None:
                _walk_rule(substep, steps, depth + 1)

        elif rtype == "PartsRule":
            u = getattr(rule, "u", None)
            dv = getattr(rule, "dv", None)
            v_step = getattr(rule, "v_step", None)
            second_step = getattr(rule, "second_step", None)
            steps.append(
                rf"{pad}**Integration by parts:** $\int u\, dv = uv - \int v\, du$"
            )
            if u is not None and dv is not None:
                steps.append(
                    rf"{pad}Choose $u = {latex(u)}$,&ensp;$dv = {latex(dv)}\, dx$"
                )
            if v_step is not None:
                steps.append(rf"{pad}Find $v$ by integrating $dv$:")
                _walk_rule(v_step, steps, depth + 1)
            if second_step is not None:
                steps.append(rf"{pad}Now evaluate the remaining integral $\int v\, du$:")
                _walk_rule(second_step, steps, depth + 1)

        elif rtype == "AlternativeRule":
            alts = getattr(rule, "alternatives", [])
            if alts:
                _walk_rule(alts[0], steps, depth)

        elif rtype == "CyclicPartsRule":
            parts_steps = getattr(rule, "parts_rules", [])
            coeff = getattr(rule, "coefficient", None)
            steps.append(
                rf"{pad}**Integration by parts (cyclic):** apply parts repeatedly then solve for the integral"
            )
            for ps in parts_steps:
                _walk_rule(ps, steps, depth + 1)

        else:
            # Unknown rule — try to recurse into any substep attribute
            name = rtype.replace("Rule", "").lower()
            steps.append(rf"{pad}Apply **{name}** integration technique")
            for attr in ("substep", "substeps", "rule"):
                sub = getattr(rule, attr, None)
                if sub is not None:
                    if isinstance(sub, list):
                        for s in sub:
                            _walk_rule(s, steps, depth + 1)
                    else:
                        _walk_rule(sub, steps, depth + 1)
                    break

    except Exception:
        steps.append(rf"{pad}Integration step applied")


# ---------------------------------------------------------------------------
# Generate similar problems
# ---------------------------------------------------------------------------

def _build_variants(expr: sp.Expr) -> list:
    seen = set()
    variants = []

    def add(e):
        s = latex(e)
        if s not in seen:
            seen.add(s)
            variants.append(s)

    # Power term: x^n  or  c*x^n
    if isinstance(expr, (sp.Pow, sp.Mul)):
        coeff, rest = expr.as_coeff_Mul()
        if isinstance(rest, sp.Pow) and rest.base == x and not rest.exp.has(x):
            n = int(rest.exp) if rest.exp.is_integer else rest.exp
            for dn in [-1, 1, 2]:
                new_n = n + dn
                if new_n != 0 and new_n != n:
                    for c in [1, 2, 3]:
                        add(c * x ** new_n)
            for c in [2, 3, 4, 5]:
                if c != coeff:
                    add(c * x ** rest.exp)
        # Product: two x-containing factors
        var_factors = [f for f in expr.args if f.has(x)]
        if len(var_factors) == 2:
            add(sp.sin(x) * x ** 2)
            add(sp.cos(x) * x)
            add(sp.exp(x) * x ** 2)
            add(sp.ln(x) * x)

    # Pure power x^n
    elif isinstance(expr, sp.Pow) and expr.base == x:
        n = expr.exp
        for dn in [-1, 1, 2, 3]:
            new_n = n + dn
            if new_n != 0:
                add(x ** new_n)
        for c in [2, 3, 5]:
            add(c * x ** n)

    # Trig
    elif any(isinstance(expr, t) for t in (sp.sin, sp.cos, sp.tan)):
        inner = expr.args[0]
        for fn in (sp.sin, sp.cos, sp.tan):
            for c in (1, 2, 3):
                add(fn(c * x))
                add(c * fn(x))

    # Exponential
    elif isinstance(expr, sp.exp):
        for c in (1, 2, 3, -1):
            add(sp.exp(c * x))
        add(sp.exp(x) + x ** 2)
        add(x * sp.exp(x))

    # Log
    elif isinstance(expr, sp.log):
        add(sp.log(x ** 2))
        add(x * sp.log(x))
        add(sp.log(2 * x))
        add(sp.log(x) / x)
        add(sp.log(x + 1))

    # Sum / polynomial
    elif isinstance(expr, sp.Add):
        for _ in range(8):
            deg = random.randint(2, 5)
            terms = []
            for d in range(deg, -1, -1):
                c = random.randint(-4, 4)
                if c != 0:
                    terms.append(c * x ** d if d > 0 else sp.Integer(c))
            if terms:
                add(sum(terms))

    # Pad with generic polynomials if we don't have 5 yet
    fallbacks = [x ** 2, 3 * x ** 2, x ** 3 - x, 2 * x ** 4, x ** 5 + x]
    for fb in fallbacks:
        if len(variants) >= 5:
            break
        add(fb)

    return variants[:5]
