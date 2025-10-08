from fastapi import FastAPI
from telegram.ext import Application
import uvicorn

app = FastAPI()

@app.get("/")
async def health_check():
    return {"message": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)