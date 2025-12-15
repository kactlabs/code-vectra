from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import random
import time
import uvicorn

# Seed random with current time for better randomness
random.seed(time.time())

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "rand_pass": "", "pattern": "1"})

@app.post("/", response_class=HTMLResponse)
async def pwdgenerator(request: Request, pattern: str = Form("1")):
    
    return templates.TemplateResponse("index.html", {"request": request, "rand_pass": "", "pattern": pattern})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
