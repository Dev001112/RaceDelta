@echo off
cd race-delta-frontend
echo Installing dependencies...
call npm install framer-motion clsx tailwind-merge lucide-react
echo Done! Please restart your development server (npm run dev).
pause
