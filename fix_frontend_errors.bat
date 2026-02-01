@echo off
echo ==========================================
echo FIXING DEPENDENCIES FOR RACE DELTA
echo ==========================================
cd race-delta-frontend
echo.
echo 1. Clearing package-lock.json...
if exist package-lock.json del package-lock.json
echo.
echo 2. Installing missing packages...
call npm install framer-motion clsx tailwind-merge lucide-react --save
echo.
echo 3. Installing all other dependencies...
call npm install
echo.
echo ==========================================
echo INSTALLATION COMPLETE
echo You may now restart your server with: npm run dev
echo ==========================================
pause
