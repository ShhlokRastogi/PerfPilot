import time
from typing import List, Dict

class SimpleApp:
    def __init__(self):
        self.routes = {}

app = SimpleApp()

def get(path: str):
    def decorator(func):
        return func
    return decorator

@get("/api/products")
def get_products() -> List[Dict[str, int]]:
    items = []
    for i in range(20):
        time.sleep(0.005)
        items.append({"id": i})
    return items
