from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}
