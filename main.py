import redis.asyncio as aioredis
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

REDIS_AVAILABLE = False
redis_client = None
try:
    redis_client = aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    REDIS_AVAILABLE = True
except Exception:
    pass

class ParseRequest(BaseModel):
    url: str

@app.post("/api/parse")
async def parse(req: ParseRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="链接不能为空")

    cache_key = f"wm:{url}"
    if REDIS_AVAILABLE:
        cached = await redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)

    if "douyin.com" in url:
        result = await parse_douyin(url)
    else:
        raise HTTPException(status_code=400, detail="目前支持抖音链接，其他平台开发中")

    if REDIS_AVAILABLE:
        import json
        await redis_client.setex(cache_key, 7200, json.dumps(result, ensure_ascii=False))

    return result

@app.get("/")
def root():
    return {"status": "ok"}