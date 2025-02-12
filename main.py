import asyncio
import sys

# Set the event loop policy for Windows to avoid NotImplementedError
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from crawl4ai import AsyncWebCrawler
from typing import List
from pydantic import BaseModel
import re

app = FastAPI()

class CrawlRequest(BaseModel):
    urls: List[str]
    batch_size: int = 5

@app.on_event("startup")
async def on_startup():
    # Create a single global AsyncWebCrawler instance 
    app.state.crawler = AsyncWebCrawler()
    await app.state.crawler.__aenter__()  # "async with" under the hood

@app.on_event("shutdown")
async def on_shutdown():
    crawler = app.state.crawler
    if crawler:
        asyncio.create_task(crawler.__aexit__(None, None, None))

async def crawl_single_url(url: str) -> dict:
    try:
        crawler: AsyncWebCrawler = app.state.crawler
        result = await crawler.arun(url=url)
        # Remove all http:// or https:// links
        data_no_links = re.sub(r"(https?://[^\s]+)", "", result.markdown)
        return {"url": url, "data": data_no_links.strip(), "status": "success"}
    except Exception as e:
        return {"url": url, "data": None, "status": "error", "error": str(e)}

async def batch_crawler(urls: List[str], batch_size: int = 5):
    tasks = [crawl_single_url(url) for url in urls]
    results = []
    
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)
        # Optional: sleep to throttle requests
        await asyncio.sleep(1)
    return results

@app.post("/crawl")
async def crawl_urls(request: CrawlRequest):
    try:
        results = await batch_crawler(request.urls, request.batch_size)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
