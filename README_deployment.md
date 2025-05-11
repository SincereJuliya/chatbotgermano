Here’s a clean and short `README.md`-ready formatted version of your notes:

---

# 🧠 Chat App – FastAPI Backend & Streamlit Frontend

## 🔧 BACKEND (`main.py`, `database.py`)

### ✅ Key Changes

* **Port Configuration**

  * Changed env var from `BACKEND_PORT` → `PORT`
  * Used `_port` in `uvicorn.run(...)`

* **Database Schema (`database.py`)**

  * **UUIDs**: Used `String(255)` for `id`, `session_id` (consistency) and so on.

* **Cleanup**

  * Removed unused imports.

---

## ☁️ AWS Deployment

* Create EC2 instance:

  * Ubuntu, t3.micro, 25 GB volume
  * Configure **security group** (e.g., allow port 8000)

* SSH & Setup:

  ```bash
  git clone <your-repo>
  source venv/bin/activate
  export PORT=8000
  # or use a .env variables
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  ```

---

## 💻 FRONTEND (`main.py`)

### ✅ Key Features

* Dynamic backend URL (from `st.secrets` or default to localhost).
* Chat session management with Streamlit `session_state`.
* Citation modal using `streamlit_modal`.
* Clean UI with header, sidebar, and chat window.

---

## ☁️ Streamlit Cloud Setup

1. Log in to [Streamlit Cloud](https://streamlit.io/cloud)
2. Link your repo, select `frontend/main.py`
3. Add a secret:

   ```
   API_URL = "http://13.50.234.243:8000"
   ```

---
