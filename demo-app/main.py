from fastapi import FastAPI
import time
from typing import List, Dict

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/api/products")
def get_products() -> List[Dict[str, int]]:
    items = []
    for i in range(20):
        time.sleep(0.005)
        items.append({"id": i})
    return items
