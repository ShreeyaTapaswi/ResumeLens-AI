# AIL Mini Project: Resume Parser by Shreeya S Tapaswi (31474)
from flask import Flask, request, jsonify, render_template
from resume_parser import extract_text, parse_resume

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/parse")
def api_parse():
    try:
        f = request.files.get("file")
        text = extract_text(f.read(), f.filename or "") if f else (request.form.get("text") or "")
        if len(text.strip()) < 40:
            return jsonify(error="No readable text found. If this is a scanned PDF, run OCR on it first."), 422
        return jsonify(parse_resume(text, request.form.get("jd") or ""))
    except ValueError as e:
        return jsonify(error=str(e)), 415
    except Exception as e:
        return jsonify(error=f"Could not read this file ({type(e).__name__}). Try a different PDF or DOCX."), 422

@app.errorhandler(413)
def too_big(_):
    return jsonify(error="File is larger than 8 MB."), 413

if __name__ == "__main__":
    app.run(debug=True, port=5000)
