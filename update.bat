@echo off
cd /d %~dp0

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
git pull
pip install .