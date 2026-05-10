import re
import os
import random
import asyncio
import httpx
from fastapi import HTTPException
from utils import get_final_url, get_mobile_headers

DOUYIN_COOKIE = os.getenv("DOUYIN_COOKIE", "")

def extract_video_id(url: str) -> str:
    patterns = [
        r'/video/(\d+)',
        r'/note/(\d+)',
        r'modal_id=(\d+)',
        r'aweme_id=(\d+)',
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    raise ValueError("无法提取视频ID")

async def parse_douyin(share_url: str) -> dict:
    try:
        long_url = await get_final_url(share_url)
        video_id = extract_video_id(long_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"链接解析失败: {str(e)}")

    api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
    headers = get_mobile_headers(referer="https://www.douyin.com/")
    if DOUYIN_COOKIE:
        headers["Cookie"] = DOUYIN_COOKIE

    await asyncio.sleep(random.uniform(0.5, 1.5))

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        resp = await client.get(api_url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="抖音拒绝请求，Cookie可能失效")
        data = resp.json()
        aweme_detail = data.get("aweme_detail")
        if not aweme_detail:
            raise HTTPException(status_code=404, detail="视频不存在或已删除")

    video_info = aweme_detail["video"]
    clean_url = None
    bit_rates = video_info.get("bit_rate", [])
    if bit_rates:
        best = sorted(bit_rates, key=lambda x: x.get("bit_rate", 0), reverse=True)[0]
        play_addr = best.get("play_addr")
        if play_addr and play_addr.get("url_list"):
            clean_url = play_addr["url_list"][0]

    if not clean_url:
        for key in ["play_addr_h264", "play_addr"]:
            addr = video_info.get(key)
            if addr and addr.get("url_list"):
                raw_url = addr["url_list"][0]
                raw_url = raw_url.replace("play.mm2080.com", "aweme.snssdk.com")
                raw_url = raw_url.replace("watermark=1", "watermark=0")
                clean_url = raw_url
                break

    if not clean_url:
        raise HTTPException(status_code=500, detail="提取无水印地址失败")

    title = aweme_detail.get("desc", "无标题")
    cover_info = video_info.get("cover")
    cover_url = cover_info["url_list"][0] if cover_info and cover_info.get("url_list") else ""

    quality_list = []
    if bit_rates:
        label_map = {540: "540p", 720: "720p", 1080: "1080p"}
        for b in sorted(bit_rates, key=lambda x: x.get("bit_rate", 0), reverse=True):
            br = b.get("bit_rate", 0)
            label = label_map.get(br, f"{br}p" if br else "高清")
            play = b.get("play_addr")
            if play and play.get("url_list"):
                quality_list.append({"label": label, "size": "未知", "url": play["url_list"][0]})
    else:
        quality_list.append({"label": "无水印", "size": "未知", "url": clean_url})

    return {
        "title": title,
        "cover": cover_url,
        "clean_url": clean_url,
        "qualities": quality_list,
        "audio_url": video_info.get("music", {}).get("play_url", {}).get("url_list", [""])[0] if video_info.get("music") else ""
    }