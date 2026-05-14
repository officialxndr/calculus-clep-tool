from flask import Flask, request, jsonify, render_template
from db import init_db, add_entry, get_all, delete_entry
from math_engine import solve_derivative, solve_integral, solve_limit, generate_similar

app = Flask(__name__)


@app.before_request
def _ensure_db():
    init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True) or {}
    expr_input = (data.get("expr") or "").strip()
    op_type = data.get("type", "derivative")

    if not expr_input:
        return jsonify({"error": "No expression provided"}), 400

    try:
        if op_type == "derivative":
            result = solve_derivative(expr_input)
        elif op_type == "integral":
            result = solve_integral(expr_input)
        elif op_type == "limit":
            point = (data.get("point") or "0").strip()
            direction = data.get("direction", "both")
            result = solve_limit(expr_input, point, direction)
        else:
            return jsonify({"error": f"Unknown type: {op_type}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Math engine error: {exc}"}), 500

    add_entry(
        op_type,
        expr_input,
        result["problem_latex"],
        result["result_latex"],
        result["steps"],
        limit_point=data.get("point") if op_type == "limit" else None,
        limit_direction=data.get("direction") if op_type == "limit" else None,
    )
    return jsonify(result)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    expr_input = (data.get("expr") or "").strip()
    op_type = data.get("type", "derivative")

    if not expr_input:
        return jsonify({"error": "No expression provided"}), 400

    try:
        problems = generate_similar(expr_input, op_type)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"problems": problems, "type": op_type})


@app.route("/history", methods=["GET"])
def history():
    return jsonify(get_all())


@app.route("/history/<int:entry_id>", methods=["DELETE"])
def delete_history(entry_id):
    delete_entry(entry_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
