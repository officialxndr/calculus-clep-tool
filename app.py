from flask import Flask, request, jsonify, render_template
from db import init_db, add_entry, get_all, delete_entry, create_exam, save_exam_result, get_exam
from math_engine import solve_derivative, solve_integral, solve_limit, generate_similar
from problem_generator import choose_question, build_exam, VALID_TOPICS

app = Flask(__name__)

# Short-lived cache: {question_id: full_question_dict}  (for practice /check)
_question_cache: dict = {}


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


# ── Practice routes ────────────────────────────────────────────────────────

@app.route("/practice/question", methods=["GET"])
def practice_question():
    topic = request.args.get("topic", "all")
    if topic not in VALID_TOPICS:
        topic = "all"
    try:
        q = choose_question(topic)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    # Cache for check endpoint (keep cache bounded)
    if len(_question_cache) > 500:
        keys = list(_question_cache.keys())
        for k in keys[:200]:
            del _question_cache[k]
    _question_cache[q["id"]] = q

    # Strip correct_index before sending to client
    public = {k: v for k, v in q.items() if k != "correct_index"}
    return jsonify(public)


@app.route("/practice/check", methods=["POST"])
def practice_check():
    data = request.get_json(silent=True) or {}
    qid = data.get("question_id", "")
    chosen = data.get("chosen_index")

    q = _question_cache.get(qid)
    if q is None:
        return jsonify({"error": "Question not found (session may have expired)"}), 404

    correct = q["correct_index"]
    is_correct = (chosen == correct)
    correct_choice = q["choices"][correct]
    return jsonify({
        "correct": is_correct,
        "correct_index": correct,
        "correct_label": correct_choice["label"],
        "correct_latex": correct_choice["latex"],
        "explanation": q.get("explanation", ""),
        "steps": q.get("steps", []),
    })


# ── Exam routes ─────────────────────────────────────────────────────────────

@app.route("/exam/generate", methods=["POST"])
def exam_generate():
    try:
        questions = build_exam(45)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    exam_id = create_exam(questions)
    # Return questions without correct_index
    public_qs = []
    for q in questions:
        public_qs.append({k: v for k, v in q.items() if k != "correct_index"})
    return jsonify({"exam_id": exam_id, "questions": public_qs, "total": len(questions)})


@app.route("/exam/grade", methods=["POST"])
def exam_grade():
    data = request.get_json(silent=True) or {}
    exam_id = data.get("exam_id")
    answers = data.get("answers", [])   # list of ints or nulls

    exam = get_exam(exam_id)
    if exam is None:
        return jsonify({"error": "Exam not found"}), 404

    questions = exam["questions"]
    score = 0
    results = []
    topic_scores: dict = {}

    for i, q in enumerate(questions):
        chosen = answers[i] if i < len(answers) else None
        correct_idx = q["correct_index"]
        is_correct = (chosen == correct_idx)
        if is_correct:
            score += 1

        topic = q.get("topic", "other")
        if topic not in topic_scores:
            topic_scores[topic] = {"correct": 0, "total": 0}
        topic_scores[topic]["total"] += 1
        if is_correct:
            topic_scores[topic]["correct"] += 1

        results.append({
            "question_num": i + 1,
            "question_latex": q["question_latex"],
            "topic": topic,
            "chosen_index": chosen,
            "chosen_label": q["choices"][chosen]["label"] if chosen is not None else None,
            "chosen_latex": q["choices"][chosen]["latex"] if chosen is not None else None,
            "correct_index": correct_idx,
            "correct_label": q["choices"][correct_idx]["label"],
            "correct_latex": q["choices"][correct_idx]["latex"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "steps": q.get("steps", []),
        })

    save_exam_result(exam_id, answers, score)
    return jsonify({
        "exam_id": exam_id,
        "score": score,
        "total": len(questions),
        "percent": round(score / len(questions) * 100) if questions else 0,
        "topic_scores": topic_scores,
        "results": results,
    })


@app.route("/exam/<int:exam_id>", methods=["GET"])
def exam_detail(exam_id):
    exam = get_exam(exam_id)
    if exam is None:
        return jsonify({"error": "Exam not found"}), 404
    return jsonify(exam)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
