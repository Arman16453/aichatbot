@echo off
echo Starting ISRO HelpBot...

echo Starting MongoDB...
start "MongoDB" mongod

timeout /t 3 /nobreak > nul

echo Starting Backend Server...
cd backend
start "Backend" python main.py

timeout /t 2 /nobreak > nul

echo Starting Frontend...
cd ../frontend
start "Frontend" npm run dev

echo All services started!
echo.
echo Access the chatbot at: http://localhost:3000
echo Backend API at: http://localhost:8001
echo.
pause