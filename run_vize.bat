@echo off
echo Startuji Vize System...
start cmd /k "streamlit run app.py"
start cmd /k "python bridge.py"
echo Vse bezi. Pro ukonceni zavri okna terminalu.