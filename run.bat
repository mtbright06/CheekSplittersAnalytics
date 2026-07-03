@echo off
cd /d "%~dp0"

echo.
echo ==========================================
echo         SharpStack Analytics
echo ==========================================
echo.

echo Pulling latest code...
git pull

echo.
echo Building KBO...
python cheek_splitters_engine.py

echo.
echo Building MLB...
python tools_build_mlb_card.py

echo.
echo Building Bomb Lab...
python tools_build_bomb_lab.py

echo.
echo Tracking recommendations...
python tools_track_recommendations.py

echo.
echo Building Discord report...
python tools_build_discord_report.py

echo.
echo Launching Dashboard...
python -m streamlit run dashboard\app.py