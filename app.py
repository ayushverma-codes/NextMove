from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import uvicorn

# --- Import Pipelines ---
from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from pipelines.run_pipeline import run_pipeline

app = FastAPI(title="NextMove Query Processing API")

# ---------------------
# 📦 Request Model
# ---------------------
class QueryRequest(BaseModel):
    query: str
    debug_mode: Optional[bool] = False 
    use_history: Optional[bool] = False
    session_id: Optional[str] = "default_session" # <--- Added Session ID

# ---------------------
# 📦 Response Models
# ---------------------
class AnalyzeResponse(BaseModel):
    analyzed_result: Dict[str, Any]

class DecomposeResponse(BaseModel):
    analyzed_result: Dict[str, Any]
    decomposed_result: Dict[str, Any]

class RunResponse(BaseModel):
    final_answer: str
    debug_info: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: str

# ---------------------
# 🔍 Analyze Endpoint (Test)
# ---------------------
@app.post("/analyze", response_model=AnalyzeResponse, responses={500: {"model": ErrorResponse}})
def analyze_query(request: QueryRequest):
    # Note: Simple test endpoint, does not use history context
    result = run_single_query(request.query)
    if result is None:
        return Response(content=json.dumps({"error": "Failed to analyze the query"}), status_code=500, media_type="application/json")
    return {"analyzed_result": result}

# ---------------------
# 🔨 Decompose Endpoint (Test)
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
# 🔁 Full Pipeline Endpoint (Main)
# ---------------------
@app.post("/run", response_model=RunResponse, responses={500: {"model": ErrorResponse}})
def run_full_pipeline_endpoint(request: QueryRequest):
    try:
        # Pass all parameters including session_id to the pipeline
        pipeline_response = run_pipeline(
            natural_language_query=request.query,
            debug_mode=request.debug_mode,
            use_history=request.use_history,
            session_id=request.session_id 
        )

        if pipeline_response is None:
            return Response(content=json.dumps({"error": "Pipeline execution returned None"}), status_code=500, media_type="application/json")
        
        return pipeline_response

    except Exception as e:
        return Response(content=json.dumps({"error": f"Internal Server Error: {str(e)}"}), status_code=500, media_type="application/json")

# ---------------------
# 🌐 Root Endpoint
# ---------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to NextMove API. Use /run for the full pipeline."
    }

# ---------------------
# 🚀 Run with Uvicorn
# ---------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)