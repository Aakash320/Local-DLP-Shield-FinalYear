from fastapi import FastAPI

app = FastAPI(title="Local Shield DLP")


@app.get("/health")
def health():
    return {"status": "ok"}
