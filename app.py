from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse
import google.generativeai as genai
import os
import uvicorn
import json
import database  # Our local DB module
import asyncio

# --- Configuration ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    history: list = []

class StockAnalysisRequest(BaseModel):
    symbol: str

class VerdictRequest(BaseModel):
    symbol: str
    metrics: dict
    score: int
    grade: str

class StrategyRequest(BaseModel):
    portfolio_summary: str
    target_return: int

class ProjectData(BaseModel):
    id: str
    name: str
    stocks: list
    weights: dict
    targetReturn: float
    chatHistory: list
    portfolioStrategy: str | None = None

class ScoreRequest(BaseModel):
    metrics: dict
    weights: dict
    target_return: float

class WeightRequest(BaseModel):
    project_name: str
    target_return: float

# --- AI Helper Function (Async) ---
def _call_gemini_sync(prompt: str, system_instruction: str = "", json_mode: bool = False) -> str:
    """Synchronous Gemini call to be run in threadpool"""
    try:
        config = generation_config.copy()
        if json_mode:
            config["response_mime_type"] = "application/json"
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=config,
            system_instruction=system_instruction,
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        if json_mode:
            # Mock fallback
            return json.dumps({
                "industry_growth": 5.0, "net_profit_growth": 5.0, 
                "mos_status": "Fair", "dividend_yield": 2.0, 
                "competition_score": 50, "beta": 1.0,
                "industry": 20, "profit": 20, "mos": 20, "yield_val": 20, "competition": 20
            })
        return "I'm having trouble connecting to my brain right now. Please check the API Key."

async def call_gemini(prompt: str, system_instruction: str = "", json_mode: bool = False) -> str:
    """Async wrapper primarily to prevent blocking event loop"""
    return await asyncio.to_thread(_call_gemini_sync, prompt, system_instruction, json_mode)

# --- Core Business Logic (Backend) ---
def calculate_master_score(metrics: dict, weights: dict, target_return: float):
    """
    Master Scoring Model (0-100)
    
    Weights (Default):
    - Industry Growth: 15%
    - Net Profit Growth: 25%
    - MOS (Valuation): 25%
    - Dividend Yield: 20%
    - Competitiveness: 15%
    """
    
    # Check for missing keys and set safe defaults
    m = {
        "industry_growth_3yr": metrics.get("industry_growth_3yr", 0),
        "net_profit_growth_5yr": metrics.get("net_profit_growth_5yr", 0),
        "pe_ratio": metrics.get("pe_ratio", 0),
        "sector_pe": metrics.get("sector_pe", 0),
        "dividend_yield": metrics.get("dividend_yield", 0),
        "dividend_years_consecutive": metrics.get("dividend_years_consecutive", 0),
        "company_growth_rate": metrics.get("company_growth_rate", 0),
        "beta": metrics.get("beta", 1.0)
    }

    raw_scores = {}

    # 1. Industry Growth (3yr CAGR)
    ind_growth = m["industry_growth_3yr"]
    if ind_growth >= 20: raw_scores["industry"] = 100
    elif ind_growth >= 10: raw_scores["industry"] = 80
    elif ind_growth >= 0: raw_scores["industry"] = 60
    else: raw_scores["industry"] = 0

    # 2. Net Profit Growth (5yr CAGR)
    prof_growth = m["net_profit_growth_5yr"]
    if prof_growth >= 20: raw_scores["profit"] = 100
    elif prof_growth >= 10: raw_scores["profit"] = 80
    elif prof_growth >= 5: raw_scores["profit"] = 60
    elif prof_growth >= 0: raw_scores["profit"] = 40
    else: raw_scores["profit"] = 0

    # 3. MOS (Valuation)
    # Formula: (Sector PE - Stock PE) / Sector PE
    # If Sector PE is 0 or None, handle gracefully (assume not cheap)
    stock_pe = m["pe_ratio"]
    sect_pe = m["sector_pe"]
    mos_score = 0
    if sect_pe > 0:
        mos_pct = (sect_pe - stock_pe) / sect_pe
        if mos_pct > 0.20: mos_score = 100      # > 20% Cheaper
        elif mos_pct >= 0.10: mos_score = 80    # 10-20% Cheaper
        elif mos_pct >= -0.10: mos_score = 50   # +/- 10% (Fair)
        else: mos_score = 0                     # More expensive
    else:
        # Fallback if no sector data: Assume Fair if PE is reasonable (<20), else 0
        if stock_pe > 0 and stock_pe < 20: mos_score = 50
        else: mos_score = 0
    raw_scores["mos"] = mos_score

    # 4. Dividend Yield
    # CRITICAL: If consecutive years < 5, Score = 0
    div_yield = m["dividend_yield"]
    div_years = m["dividend_years_consecutive"]
    
    if div_years < 5:
        raw_scores["yield"] = 0
    else:
        if div_yield >= 8: raw_scores["yield"] = 100
        elif div_yield >= 5: raw_scores["yield"] = 80
        elif div_yield >= 3: raw_scores["yield"] = 60
        else: raw_scores["yield"] = 30

    # 5. Competitiveness (Company Growth vs Industry Growth)
    # Diff = Company Growth - Industry Growth
    comp_growth = m["company_growth_rate"]
    # We compare comp_growth (Generic Company Growth) vs ind_growth (Industry Growth 3yr)
    # Or should we compare Net Profit Growth vs Industry Growth? 
    # The requirement says "Company Growth - Industry Growth". 
    # We will use 'company_growth_rate' extracted specifically for this.
    
    diff = comp_growth - ind_growth
    if diff >= 15: raw_scores["competition"] = 100
    elif diff >= 5: raw_scores["competition"] = 80
    elif diff >= -5: raw_scores["competition"] = 50
    else: raw_scores["competition"] = 20

    # Step A: Base Score Calculation
    # Weights should be passed as integers (e.g. 15, 25...). We divide by 100.
    w_ind = weights.get("industry", 15)
    w_prof = weights.get("profit", 25)
    w_mos = weights.get("mos", 25)
    w_yield = weights.get("yield_val", 20)
    w_comp = weights.get("competition", 15)
    
    base_score = (
        (raw_scores["industry"] * w_ind) +
        (raw_scores["profit"] * w_prof) +
        (raw_scores["mos"] * w_mos) +
        (raw_scores["yield"] * w_yield) +
        (raw_scores["competition"] * w_comp)
    ) / 100.0

    # Step B: Risk Multiplier Logic
    beta = m["beta"]
    risk_mult = 1.0
    
    if target_return < 10: # Conservative
        if beta < 0.8: risk_mult = 1.0
        elif beta <= 1.2: risk_mult = 0.9
        else: risk_mult = 0.5
    elif target_return >= 15: # Aggressive
        if beta >= 1.2 and beta <= 2.5: risk_mult = 1.0
        elif beta >= 0.9 and beta < 1.2: risk_mult = 0.9
        else: risk_mult = 0.6 # < 0.9 (Too low/sluggish) or > 2.5 (Too volatile)
    else: # Moderate (10 - 14.99)
        if beta >= 0.7 and beta <= 1.5: risk_mult = 1.0
        else: risk_mult = 0.8

    # Step C: Final Grading
    final_score = base_score * risk_mult
    
    grade = "C" # Default
    if final_score >= 80: grade = "A"
    elif final_score >= 60: grade = "B"
    
    return {
        "baseScore": round(base_score, 1),
        "finalScore": int(final_score),
        "grade": grade,
        "riskMult": risk_mult,
        "rawScores": raw_scores
    }

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/api/projects")
async def get_projects():
    return database.get_all_projects()

@app.post("/api/projects")
async def save_project(project: ProjectData):
    # Fallback for Pydantic v1 vs v2
    try:
        data = project.model_dump()
    except AttributeError:
        data = project.dict()
        
    database.save_project(data)
    print(f"Saved project: {project.id} - {project.name}") 
    return {"status": "success"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    database.delete_project(project_id)
    return {"status": "success"}

# --- AI & Logic Endpoints ---

@app.post("/api/chat")
async def chat_jomo(req: ChatRequest):
    system_prompt = "You are Jomo, a witty investment consultant. Keep answers short, helpful, and suggest specific stock tickers."
    reply = await call_gemini(req.message, system_prompt)
    return {"reply": reply}

@app.post("/api/analyze-stock")
async def analyze_stock(req: StockAnalysisRequest):
    prompt = f"""
    Analyze stock {req.symbol}. Extract these EXACT metrics (estimate if needed for Thai/Global context):
    1. industry_growth_3yr (Float %)
    2. net_profit_growth_5yr (Float %)
    3. pe_ratio (Float)
    4. sector_pe (Float) - Average PE of the sector
    5. dividend_yield (Float %)
    6. dividend_years_consecutive (Int) - How many years of continuous dividends?
    7. company_growth_rate (Float %) - General revenue/growth rate
    8. beta (Float)
    
    Return JSON only:
    {{
        "industry_growth_3yr": float, 
        "net_profit_growth_5yr": float, 
        "pe_ratio": float, 
        "sector_pe": float,
        "dividend_yield": float, 
        "dividend_years_consecutive": int,
        "company_growth_rate": float,
        "beta": float
    }}
    """
    json_str = await call_gemini(prompt, "You are a financial data extractor. Output ONLY valid JSON.", json_mode=True)
    try:
        data = json.loads(json_str)
        return data
    except:
        # Mock Default on Error
        return {
            "industry_growth_3yr": 5.0, "net_profit_growth_5yr": 5.0, 
            "pe_ratio": 15.0, "sector_pe": 15.0,
            "dividend_yield": 2.0, "dividend_years_consecutive": 5,
            "company_growth_rate": 5.0, "beta": 1.0
        }

@app.post("/api/calculate-score")
async def calculate_score_endpoint(req: ScoreRequest):
    return calculate_master_score(req.metrics, req.weights, req.target_return)

@app.post("/api/suggest-weights")
async def suggest_weights(req: WeightRequest):
    print(f"Suggesting weights for {req.project_name}")
    # Default recommended weights
    default_weights = {"industry": 15, "profit": 25, "mos": 25, "yield_val": 20, "competition": 15}
    
    prompt = f"""
    Acting as Jomo (Investment Strategist), suggest the optimal weighting (Total 100%) for:
    1. industry (Industry Growth)
    2. profit (Net Profit Growth)
    3. mos (Valuation/MOS)
    4. yield_val (Dividend Yield)
    5. competition (Competitiveness)

    Context: Project Name "{req.project_name}", Target Return {req.target_return}%.
    If the project implies dividends, boost yield. If growth, boost industry/profit.
    
    Return JSON only: {{"industry": int, "profit": int, "mos": int, "yield_val": int, "competition": int}}
    """
    json_str = await call_gemini(prompt, "Output ONLY valid JSON.", json_mode=True)
    try:
        data = json.loads(json_str)
        return data
    except:
        return default_weights

@app.post("/api/verdict")
async def generate_verdict(req: VerdictRequest):
    prompt = f"""Acting as a senior investment analyst, write a concise 2-sentence verdict for {req.symbol}. 
    Key Data: PE {req.metrics.get('pe_ratio')} (Sector {req.metrics.get('sector_pe')}), Yield {req.metrics.get('dividend_yield')}%. 
    The model scored it {req.score}/100 (Grade {req.grade}). 
    Explain why it got this score based on the Master Scoring Model rules."""
    
    reply = await call_gemini(prompt)
    return {"verdict": reply}

@app.post("/api/strategy")
async def generate_strategy(req: StrategyRequest):
    prompt = f"""Analyze this stock portfolio: [{req.portfolio_summary}]. 
    Target Return is {req.target_return}%. 
    Provide a summary of the portfolio's overall quality and 3 concise bullet points for optimization strategy."""
    
    reply = await call_gemini(prompt)
    return {"strategy": reply}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
