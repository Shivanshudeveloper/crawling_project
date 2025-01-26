from fastapi import FastAPI, HTTPException
import asyncio
from crawl4ai import AsyncWebCrawler
from typing import List
from pydantic import BaseModel

app = FastAPI()

class CrawlRequest(BaseModel):
    urls: List[str]
    batch_size: int = 5

async def crawl_single_url(url: str, crawler: AsyncWebCrawler) -> dict:
    try:
        result = await crawler.arun(url=url)
        return {"url": url, "data": result.markdown, "status": "success"}
    except Exception as e:
        return {"url": url, "data": None, "status": "error", "error": str(e)}

async def batch_crawler(urls: List[str], batch_size: int = 5):
    async with AsyncWebCrawler() as crawler:
        tasks = [crawl_single_url(url, crawler) for url in urls]
        results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            await asyncio.sleep(1)
            
    return results

@app.post("/crawl")
async def crawl_urls(request: CrawlRequest):
    try:
        results = await batch_crawler(request.urls, request.batch_size)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))