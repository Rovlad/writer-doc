"""
Словарь Писателя — Flask application.

Routes
------
GET  /                  → upload page
POST /analyze           → run analysis, redirect to results
GET  /results           → results dashboard (reads from session)
GET  /api/search?noun=  → JSON: adjectives for a given noun
GET  /api/export        → download full analysis as JSON
POST /api/save           → save to Supabase
GET  /history           → list of saved analyses (Supabase)
GET  /history/<id>      → load saved analysis
DELETE /api/history/<id> → delete analysis from Supabase
"""

from __future__ import annotations

import json
import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    Response,
    flash,
)

from config import Config
from analyzer import analyze_text
from analyzer.collocations import search_adjectives_for_noun
from storage.json_export import export_json

# ── App factory ───────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


# ── In-memory cache for last analysis (avoids huge session cookies) ─
# In production, replace with Redis or DB-backed sessions.
_analysis_cache: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════════
#  PAGES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Upload page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Accept file upload or pasted text, run analysis, store in cache, redirect."""
    text = None
    filename = "вставленный_текст.txt"

    # Prefer pasted text if present
    pasted = request.form.get("pasted_text", "").strip()
    if pasted:
        text = pasted
    else:
        # Fall back to file upload
        if "file" not in request.files:
            flash("Загрузите файл или вставьте текст", "error")
            return redirect(url_for("index"))

        file = request.files["file"]
        if file.filename == "" or not _allowed_file(file.filename):
            flash("Пожалуйста, загрузите файл .txt или вставьте текст", "error")
            return redirect(url_for("index"))

        filename = file.filename
        raw_bytes = file.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("cp1251")
            except UnicodeDecodeError:
                text = raw_bytes.decode("latin-1")

    if not text or not text.strip():
        flash("Текст пуст. Загрузите файл или вставьте текст.", "error")
        return redirect(url_for("index"))

    # Run analysis
    result = analyze_text(text)

    # Store in cache
    analysis_id = str(uuid.uuid4())
    _analysis_cache[analysis_id] = {
        "filename": filename,
        "result": result,
    }
    session["analysis_id"] = analysis_id
    session["filename"] = filename

    return redirect(url_for("results"))


@app.route("/results")
def results():
    """Results dashboard."""
    analysis_id = session.get("analysis_id")
    if not analysis_id or analysis_id not in _analysis_cache:
        flash("Нет результатов анализа. Загрузите текст.", "info")
        return redirect(url_for("index"))

    cached = _analysis_cache[analysis_id]
    return render_template(
        "results.html",
        filename=cached["filename"],
        result=cached["result"],
        analysis_id=analysis_id,
    )


# ══════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.route("/api/search")
def api_search():
    """Search adjectives for a noun.  ?noun=слово&limit=20"""
    analysis_id = session.get("analysis_id")
    if not analysis_id or analysis_id not in _analysis_cache:
        return jsonify({"error": "No analysis in session"}), 400

    noun = request.args.get("noun", "").strip()
    if not noun:
        return jsonify({"error": "Parameter 'noun' is required"}), 400

    limit = int(request.args.get("limit", 20))
    index = _analysis_cache[analysis_id]["result"]["collocations"]["noun_adj_index"]
    matches = search_adjectives_for_noun(index, noun, limit=limit)

    return jsonify({"noun": noun, "adjectives": matches})


@app.route("/api/export")
def api_export():
    """Download full analysis as JSON."""
    analysis_id = session.get("analysis_id")
    if not analysis_id or analysis_id not in _analysis_cache:
        return jsonify({"error": "No analysis in session"}), 400

    cached = _analysis_cache[analysis_id]
    json_str = export_json(cached["result"])
    filename = cached["filename"].rsplit(".", 1)[0] + "_analysis.json"

    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/save", methods=["POST"])
def api_save():
    """Save current analysis to Supabase."""
    analysis_id = session.get("analysis_id")
    if not analysis_id or analysis_id not in _analysis_cache:
        return jsonify({"error": "No analysis in session"}), 400

    try:
        from storage.supabase_client import save_to_supabase

        cached = _analysis_cache[analysis_id]
        record = save_to_supabase(cached["result"], cached["filename"])
        return jsonify({"success": True, "record": record})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history")
def history():
    """List saved analyses from Supabase."""
    try:
        from storage.supabase_client import list_saved_analyses

        analyses = list_saved_analyses()
        return render_template("history.html", analyses=analyses)
    except Exception as e:
        flash(f"Ошибка подключения к Supabase: {e}", "error")
        return render_template("history.html", analyses=[])


@app.route("/history/<analysis_id>")
def load_from_history(analysis_id):
    """Load a saved analysis from Supabase."""
    try:
        from storage.supabase_client import load_analysis

        data = load_analysis(analysis_id)
        if not data:
            flash("Анализ не найден", "error")
            return redirect(url_for("history"))

        # Reconstruct result format
        result = {
            "meta": {
                "char_count": data.get("char_count", 0),
                "processing_time_sec": data.get("processing_time", 0),
            },
            "dictionary": data.get("dictionary", []),
            "statistics": data.get("statistics", {}),
            "collocations": data.get("collocations", {}),
        }
        cache_id = str(uuid.uuid4())
        _analysis_cache[cache_id] = {
            "filename": data.get("filename", "saved"),
            "result": result,
        }
        session["analysis_id"] = cache_id
        session["filename"] = data.get("filename", "saved")

        return redirect(url_for("results"))
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
        return redirect(url_for("history"))


@app.route("/api/history/<analysis_id>", methods=["DELETE"])
def api_delete_analysis(analysis_id):
    """Delete an analysis from Supabase."""
    try:
        from storage.supabase_client import delete_analysis

        delete_analysis(analysis_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
