from fastapi import FastAPI
from app.rooms import rooms_router

app = FastAPI(title="Guess the Prompt Backend")

app.include_router(rooms_router)

@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}
