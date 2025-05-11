
## Repo Structure
chatbot_project/  
│  
├── backend/                ← FastAPI app  
│   ├── api/                ← API routes and logic  
│   │   ├── chat.py  
│   │   ├── sessions.py  
│   │   └── ...  
│   ├── core/               ← Core logic (LLM, vector store, etc.)  
│   │   ├── llm.py  
│   │   ├── vectorstore.py  
│   │   ├── chat_engine.py  
│   │   └── config.py  
│   ├── db/                 ← DB models and operations  
│   │   ├── models.py  
│   │   ├── crud.py  
│   │   └── database.py  
│   ├── main.py             ← Entry point for FastAPI server  
│   └── requirements.txt  
│  
├── frontend/               ← Streamlit or other frontend  
│   ├── main.py             ← Streamlit UI logic  
│   ├── components/         ← Reusable UI components  
│   ├── assets/             ← CSS, images, etc.  
│   └── utils.py            ← Frontend utilities  
│  
├── scripts/                ← Setup, training, indexing scripts  
│   ├── ingest_docs.py  
│   └── test_vectorstore.py  
│  
├── .env                    ← Secrets and config  
├── README.md  
└── pyproject.toml / requirements.txt  


## Create Virtual Environment on Windows
- Create Venv. For example:
    > `C:\Users\yusup\AppData\Local\Microsoft\WindowsApps\python3.13.exe -m venv .venv`
- Activate it:
    > `.\.venv\Scripts\activate`
- To deactivate it:
    > deactivate

- To install a package:
    > `pip install package_name`
- To install all packages in the requirement file:
    > `pip install -r requirements.txt`

## Download and Install MySQL

- Download from the official website at: https://dev.mysql.com/downloads/file/?id=541637
- Set it up ...
- After installation, you can verify with: `sc query MySQL80`

## Google sites, Analytics and Search Console

- How to connect your [website](https://sites.google.com/view/chatbot-germano/scenario?authuser=0) to [google analytics](https://analytics.google.com/analytics/web/provision/#/p487121650/reports/intelligenthome?params=_u..nav%3Dmaui&collectionId=user) and search console? [Watch this Youtube video](https://www.youtube.com/watch?v=QiPvlznkA7k) 
- Google Analytics 4 (GA4) Tutorial for Beginners [Youtube video](https://www.youtube.com/watch?v=S7r83NvINiM)


## Network Port
- If you get error relating to network issues (port), check which process is using the port and whether you want to kill it, where :8000 is the example port and 19368 is the process using it.
    - netstat -aon | findstr :8000
    - TaskKill /PID 19368 /F 

## Tags

- To `Tag` a specific git repo version:
  - Create a version tag
    > `git tag -a v1.0.0 -m "Latest stable version"`
  - Push the tag to the remote repository
    > `git push origin v1.0.0`

- To delete a tag
  - locally: `git tag -d v1.0.0`
  - Remotely: `git push --delete origin v1.0.0`

- To work on a tag
  - Clone the repo if not already and cd to the project root
  - - To fetch all tags `git fetch --tags`
  - then run `git checkout v1.0.0`


- Nice [article](https://dev.to/kodebae/how-to-remove-a-leaked-env-file-from-github-permanently-3lei) to remove wrongly pushed files to github


## To run
- For Bash/Unix-based terminals:
  - Backend:
    - be in the project root `chatbotgermano`
    - `PYTHONPATH=. uvicorn backend.main:app --reload --port 3003`
    - However, if you already call the uvicorn.app(...) in the backend\main.py:
      - `PYTHONPATH=. python backend/main.py`
  - Frontend:
    - `PYTHONPATH=. streamlit run frontend/main.py --server.port 3005`

- For Windows Powershell:
  - Variable=value command doesn't work! SO, you need another way of setting the path.
  - `$env:PYTHONPATH = "."` should set your PYTHONPATH correctly in your current PowerShell session. If you need this to be set every time you open a new PowerShell window, you would add $env:PYTHONPATH = "." to your PowerShell profile script.
  - So, for backend:
  ```bash
  $env:PYTHONPATH = "."
  uvicorn backend.main:app --reload --port 3003
  ```
  - For frontend:
  ```bash
  $env:PYTHONPATH = "."
  streamlit run frontend/main.py --server.port 3005
  ```


