from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# This is CRITICAL for your GitHub Pages panel to talk to Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

class LinkRequest(BaseModel):
    url: str

@app.post("/process")
async def process_link(request: LinkRequest):
    # This is the logic that returns your result
    return {"output": f"Result for {request.url}"}
