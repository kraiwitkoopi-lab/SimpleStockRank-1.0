@echo off
echo Starting JomoScorer Server...
echo Open http://127.0.0.1:8000 in your browser after the server starts.
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
pause
