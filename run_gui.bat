@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -m case_study.gui %*) || (python -m case_study.gui %*)
