## ⚙️ How to Use These Commands

You would typically run these commands in **two separate terminal windows or tabs** because both the backend server and the frontend development process are long-running tasks that need to stay active simultaneously.

1.  **Terminal 1 (Backend):** 
    Run `cd backend` and then `uvicorn server:app --host 0.0.0.0 --port 8000 --reload`.
2.  **Terminal 2 (Frontend):** 
    Run `cd frontend` and then `npm run dev`.
