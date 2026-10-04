# Wellnest — M1 / M2 symptom-pattern demo

A responsive website that uses the supplied `diagnose.py` and project artifacts. M1 is the Random Forest model; M2 is XGBoost. The `model_data` folder contains the runtime files needed from the supplied project so the site can run or deploy by itself.

## Run locally

From PowerShell in this website folder, create an isolated environment and install the pinned packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\server.py --project-dir .\model_data
```

Then open <http://127.0.0.1:8000>. You can also double-click `run_website.bat` after installing dependencies. Stop the local server with Ctrl+C in its window.

To use the original project folder instead, pass its location to `--project-dir`. It must contain `diagnose.py`, both model pickles, the label encoder, symptom list and frequency table, severity CSV, description CSV, and precaution CSV. The pickle metadata reports scikit-learn 1.9.0, while the supplied script header mentions 1.8.0; the requirements pin the pickle's version to avoid the compatibility warning.

## How selection works

Both models receive the same 264-feature binary symptom vector, constructed in the order from `symptom_list.pkl`. M1 and M2 each return a disease probability vector. The server reads the highest class probability from each model and returns only the disease result from the model with the larger top-class score, along with that selected model's name. Scores and the other model's output are not sent to or shown in the results view.

The selection rule compares the models' top-class probability outputs internally. These are not validated estimates of medical accuracy or certainty, and differently calibrated models may not be directly comparable. The result is an educational model output, not a definitive diagnosis.

Disease descriptions, precaution notes, symptom choices, and symptom-pattern frequencies come from the supplied files. Reference notes are for project demonstration only; do not treat them as medical advice. The site's severity label is the same sum-of-weights rule in `diagnose.py`; it is a project estimate, not a clinical triage assessment.

## Integration and privacy

- `server.py` loads the supplied `diagnose.py` from the project folder at startup and refuses to start if either model or the shared feature list does not load.
- `/api/options` exposes the model's actual symptom vocabulary; `/api/diagnose` validates selected values against it and evaluates both models in memory.
- The server binds to `127.0.0.1` by default. It does not save requests, and request logging is suppressed to keep symptom selections out of logs.
- The front end escapes model-provided text before displaying it and the server limits request size and symptom count.
- No database exists in the supplied files; the app reads the CSV reference data and pickle models via the existing diagnosis module.

This is an educational demonstration only. It is not medical advice and is not a substitute for a qualified healthcare professional.

## Put it online with Render

This folder includes `render.yaml` and `.python-version` for a Render Python web service. To publish it:

1. Create a **private GitHub repository** and upload the contents of this website folder, including `model_data`. Do not include `.venv`.
2. In Render, choose **New → Blueprint**, connect that GitHub repository, and let Render apply `render.yaml` and deploy the service.
3. When the deploy finishes, use the `onrender.com` URL shown in the Render dashboard. The included start command binds the app to `0.0.0.0` on Render's `PORT`; Render serves public web services over HTTPS. [Render web service guide](https://render.com/docs/web-services)

The free plan works for a school demo, but free services sleep after 15 minutes without visits and can take about a minute to start again. [Free plan limits](https://render.com/docs/free) Keep the GitHub repository private because it contains the model files. Use sample/demo inputs only: this project is educational and is not prepared or reviewed for real patient information or clinical use.
