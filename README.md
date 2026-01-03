# JomoScorer: Dual-AI Investment Analysis

A powerful, AI-driven stock scoring and analysis tool that combines the wisdom of a witty consultant ("Jomo") with a strict quantitative scorer ("StockScorer").

## Features

*   **Dual-AI Persona**:
    *   **Jomo**: Provides qualitative analysis, strategy, and chat support (powered by Gemini).
    *   **StockScorer**: strictly calculates scores based on the "Master Scoring Model".
*   **Master Scoring Model**:
    *   Strict 5-factor evaluation: Industry Growth, Net Profit Growth, MOS, Dividend Yield, Competitiveness.
    *   **Risk Multiplier**: Adjusts scores based on Stock Beta vs. User Target Return.
*   **Reactive Dashboard**:
    *   Modern, glassmorphism-style UI.
    *   Real-time score recalculation via sliders and manual data entry.
    *   Full manual override support for all 7 key metrics.
*   **Full Stack**:
    *   **Frontend**: React (Single Page Application via `index.html`).
    *   **Backend**: FastAPI (`app.py`).
    *   **Database**: SQLite (`jomo.db`) for persisting projects and portfolios.

## Tech Stack

*   **Python**: FastAPI, Uvicorn, Pydantic
*   **AI**: Google Gemini (`google-generativeai`)
*   **Frontend**: React, TailwindCSS (CDN)
*   **Storage**: SQLite

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/StartYourName/JomoScorer.git
    cd JomoScorer
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Environment Variable**:
    You need a Google Gemini API Key.
    ```bash
    set GOOGLE_API_KEY=your_api_key_here
    ```

4.  **Run the App**:
    ```bash
    uvicorn app:app --reload
    ```
    *Or simply double-click `run.bat` on Windows.*

5.  **Open Browser**:
    Go to `http://127.0.0.1:8000`

## Usage

1.  **Create a Project**: Name your portfolio (e.g., "Tech Stocks").
2.  **Add Stocks**: Enter symbols (e.g., `PTT`, `KBANK`).
3.  **Analyze**: Jomo will extract data (or use defaults).
4.  **Refine**:
    *   Use the **sliders** to adjust how much each factor matters.
    *   Edit the **Raw Metrics** manually in the table if the AI data is off.
5.  **Get Verdict**: Click the document icon to get a qualitative summary from Jomo.

## License

Evaluating stocks is risky. Use this tool for educational purposes only.
