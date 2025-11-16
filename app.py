# D:\Projects\NextMove\app.py

from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from pipelines.run_pipeline import run_pipeline

import uvicorn

app = FastAPI(title="NextMove Query Processing API")


# ---------------------
# 📦 Request Model (Updated)
# ---------------------
class QueryRequest(BaseModel):
    query: str
    debug_mode: Optional[bool] = False # Use one flag for debug mode


# ---------------------
# 📦 Response Models (Updated)
# ---------------------
class AnalyzeResponse(BaseModel):
    analyzed_result: Dict[str, Any]

class DecomposeResponse(BaseModel):
    analyzed_result: Dict[str, Any]
    decomposed_result: Dict[str, Any]

class RunResponse(BaseModel):
    final_answer: str
    debug_info: Optional[Dict[str, Any]] = None # Add debug_info field

class ErrorResponse(BaseModel):
    error: str


# ---------------------
# 🔍 Analyze Endpoint
# ---------------------
@app.post("/analyze", response_model=AnalyzeResponse, responses={500: {"model": ErrorResponse}})
def analyze_query(request: QueryRequest):
    result = run_single_query(request.query)
    if result is None:
        return Response(content=json.dumps({"error": "Failed to analyze the query"}), status_code=500, media_type="application/json")
    return {"analyzed_result": result}


# ---------------------
# 🔨 Decompose Endpoint
# ---------------------
@app.post("/decompose", response_model=DecomposeResponse, responses={500: {"model": ErrorResponse}})
def decompose_query(request: QueryRequest):
    analyzed_result = run_single_query(request.query)
    if analyzed_result is None:
        return Response(content=json.dumps({"error": "Failed to analyze the query"}), status_code=500, media_type="application/json")

    analyzed_result["original_query"] = request.query
    try:
        decomposed_result = decompose_single_query(analyzed_result)
        return {
            "analyzed_result": analyzed_result,
            "decomposed_result": decomposed_result
        }
    except Exception as e:
        return Response(content=json.dumps({
            "analyzed_result": analyzed_result,
            "error": f"Failed to decompose: {str(e)}"
        }), status_code=500, media_type="application/json")

# ---------------------
# 🔁 Full Pipeline Endpoint (Updated)
# ---------------------
@app.post("/run", response_model=RunResponse, responses={500: {"model": ErrorResponse}})
def run_full_pipeline(request: QueryRequest):
    
    # Pass the debug_mode flag from the request to the pipeline
    pipeline_response = run_pipeline(
        natural_language_query=request.query,
        debug_mode=request.debug_mode
    )

    if pipeline_response is None:
        return Response(content=json.dumps({"error": "Pipeline execution failed"}), status_code=500, media_type="application/json")
    
    # Return the entire response dictionary (final_answer + debug_info)
    return pipeline_response


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