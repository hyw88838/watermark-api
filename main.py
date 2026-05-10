from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from parsers.douyin import parse_douyin

app = FastAPI(title="去水印助手", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ParseRequest(BaseModel):
    url: str

@app.post("/api/parse")
async def parse(req: ParseRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="链接不能为空")

    if "douyin.com" in url:
        result = await parse_douyin(url)
    else:
        raise HTTPException(status_code=400, detail="目前支持抖音链接，其他平台开发中")

    return result

@app.get("/")
def root():
    return {"status": "ok"}
