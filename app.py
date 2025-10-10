from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from pipelines.run_pipeline import run_pipeline

import uvicorn

app = FastAPI(title="NextMove Query Processing API")


# ---------------------
# 📦 Request Model
# ---------------------
class QueryRequest(BaseModel):
    query: str
    show_analysis_json: Optional[bool] = False
    show_decomposition_json: Optional[bool] = False


# ---------------------
# 🔍 Analyze Endpoint
# ---------------------
@app.post("/analyze")
def analyze_query(request: QueryRequest):
    result = run_single_query(request.query)
    if result is None:
        return {"error": "Failed to analyze the query"}
    return {"analyzed_result": result}


# ---------------------
# 🔨 Decompose Endpoint
# ---------------------
@app.post("/decompose")
def decompose_query(request: QueryRequest):
    # Step 1: Analyze
    analyzed_result = run_single_query(request.query)
    if analyzed_result is None:
        return {"error": "Failed to analyze the query"}

    # Step 2: Decompose
    try:
        decomposed_result = decompose_single_query(analyzed_result)
        return {
            "analyzed_result": analyzed_result,
            "decomposed_result": decomposed_result
        }
    except Exception as e:
        return {
            "analyzed_result": analyzed_result,
            "error": f"Failed to decompose: {e}"
        }


# ---------------------
# 🔁 Full Pipeline Endpoint
# ---------------------
@app.post("/run")
def run_full_pipeline(request: QueryRequest):
    results = run_pipeline(
        natural_language_query=request.query,
        show_analysis_json=request.show_analysis_json,
        show_decomposition_json=request.show_decomposition_json
    )

    if results is None:
        return {"error": "Pipeline execution failed"}
    return {
        "results": results
    }


# ---------------------
# 🌐 Root Endpoint
# ---------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to NextMove API. Use /analyze, /decompose or /run."
    }


# ---------------------
# 🚀 Run with Uvicorn
# ---------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
