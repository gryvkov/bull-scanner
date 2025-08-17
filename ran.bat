@echo off
REM Запуск Streamlit-дэшборда бычьих трендов

REM Переходим в папку, где лежит скрипт
cd /d "%~dp0"

REM Запускаем Streamlit
streamlit run Main.py

pause