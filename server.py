import sys
import os

# Add src/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from outreach.webhook_server import router

app = FastAPI(title="Vigil Outreach Server")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
