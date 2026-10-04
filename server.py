"""Local educational diagnosis demo backed by the supplied diagnose.py models."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
MAX_BODY = 16_384
MAX_SYMPTOMS = 20


def load_engine(project_dir: Path):
    source = project_dir / "diagnose.py"
    if not source.is_file():
        raise RuntimeError(f"Could not find diagnose.py in {project_dir}")
    spec = importlib.util.spec_from_file_location("project_diagnose", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the supplied diagnosis module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.xgb_model is None or module.label_encoder is None:
        raise RuntimeError("M2 (XGBoost) did not load. Install the supplied model dependencies and restart.")
    if module.rf_model is None or not module.all_symptoms:
        raise RuntimeError("M1 or the supplied symptom list did not load.")
    if int(module.rf_model.n_features_in_) != len(module.all_symptoms):
        raise RuntimeError("M1 feature count does not match the supplied symptom list.")
    if int(module.xgb_model.n_features_in_) != len(module.all_symptoms):
        raise RuntimeError("M2 feature count does not match the supplied symptom list.")
    return module


def make_handler(engine):
    class Handler(BaseHTTPRequestHandler):
        server_version = "DiagnosisDemo/1.0"

        def log_message(self, fmt, *args):
            # Suppress URL/body logging so symptom selections stay out of logs.
            return

        def send_json(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/options":
                self.send_json(200, {"symptoms": engine.all_symptoms})
                return
            if path == "/api/health":
                self.send_json(200, {"ready": True, "models": ["M1", "M2"]})
                return
            if path == "/" or path == "/index.html":
                self.serve_file(HERE / "index.html", "text/html; charset=utf-8")
                return
            if path in ("/styles.css", "/app.js"):
                name = path.removeprefix("/")
                media = "text/css; charset=utf-8" if name.endswith(".css") else "text/javascript; charset=utf-8"
                self.serve_file(HERE / name, media)
                return
            self.send_json(404, {"error": "Page not found."})

        def serve_file(self, file_path, content_type):
            try:
                body = file_path.read_bytes()
            except OSError:
                self.send_json(404, {"error": "Page not found."})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if urlparse(self.path).path != "/api/diagnose":
                self.send_json(404, {"error": "Page not found."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY:
                    self.send_json(413, {"error": "Request is too large or empty."})
                    return
                if "application/json" not in self.headers.get("Content-Type", ""):
                    self.send_json(415, {"error": "Submit symptoms as JSON."})
                    return
                payload = json.loads(self.rfile.read(length))
                raw = payload.get("symptoms") if isinstance(payload, dict) else None
                if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_SYMPTOMS:
                    self.send_json(400, {"error": f"Choose between 1 and {MAX_SYMPTOMS} symptoms."})
                    return
                canonical = set(engine.all_symptoms)
                symptoms = []
                for item in raw:
                    if not isinstance(item, str) or len(item) > 100:
                        self.send_json(400, {"error": "One of the selected symptoms is invalid."})
                        return
                    name = re.sub(r"\s+", "_", item.strip().lower())
                    if name not in canonical:
                        self.send_json(400, {"error": "One of the selected symptoms is not in the supplied symptom list."})
                        return
                    if name not in symptoms:
                        symptoms.append(name)
                if not symptoms:
                    self.send_json(400, {"error": "Choose at least one symptom."})
                    return
                response = build_result(engine, symptoms)
                self.send_json(200, response)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_json(400, {"error": "The request could not be read. Please try again."})
            except Exception:
                # Do not return model paths, user data, or tracebacks to the browser.
                self.send_json(500, {"error": "The models could not complete this request. Check the local server setup and try again."})

    return Handler


def build_result(engine, symptoms):
    import numpy as np

    vector = np.zeros((1, len(engine.all_symptoms)), dtype=np.uint8)
    for symptom in symptoms:
        vector[0, engine.sym_idx[symptom]] = 1

    # The supplied diagnose.py helper maps each model's predict_proba output
    # onto disease names (including M2's label encoder) and sorts highest first.
    m1 = engine._probabilities(vector, "rf")
    m2 = engine._probabilities(vector, "xgb")
    # Compare top-class probabilities internally; return only the winning result.
    candidates = [
        {"id": "M1", "name": "Random Forest", "disease": str(m1.index[0]), "probability": float(m1.iloc[0])},
        {"id": "M2", "name": "XGBoost", "disease": str(m2.index[0]), "probability": float(m2.iloc[0])},
    ]
    selected = max(candidates, key=lambda item: item["probability"])
    return {
        "selected": {"id": selected["id"], "name": selected["name"], "disease": selected["disease"]},
    }


def main():
    parser = argparse.ArgumentParser(description="Run the local M1/M2 educational diagnosis website.")
    parser.add_argument("--project-dir", type=Path, default=os.environ.get("DIAGNOSIS_PROJECT_DIR"),
                        help="Folder containing diagnose.py and its supplied model/data files")
    parser.add_argument("--host", default="127.0.0.1", help="Bind locally by default")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.project_dir is None:
        parser.error("Provide --project-dir or set DIAGNOSIS_PROJECT_DIR to the supplied project folder.")
    engine = load_engine(args.project_dir.expanduser().resolve())
    server = ThreadingHTTPServer((args.host, args.port), make_handler(engine))
    print(f"Diagnosis demo ready at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
