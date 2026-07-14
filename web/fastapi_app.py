# web/fastapi_app.py
"""
FastAPI Web应用 - 异步股票分析系统
支持后台任务、实时进度推送、缓存加速
"""
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.stock_analysis_system import StockAnalysisSystem

logger = logging.getLogger(__name__)

# 全局线程池 - 限制并发避免API超限
executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

app = FastAPI(
    title="AI 股票分析系统 API",
    description="基于 CrewAI Multi-Agent 的智能股票投资分析",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============

class AnalysisRequest(BaseModel):
    company: str
    ticker: str
    use_cache: bool = True

class ProgressUpdate(BaseModel):
    task_id: str
    stage: str
    status: str
    message: str
    progress: int
    company: str
    ticker: str
    timestamp: str

# ============ 任务存储 ============

class TaskStore:
    """简单的任务存储"""
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, company: str, ticker: str) -> str:
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {
            "task_id": task_id,
            "company": company,
            "ticker": ticker,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "progress_history": []
        }
        return task_id

    def update_progress(self, task_id: str, update: Dict[str, Any]):
        if task_id in self.tasks:
            self.tasks[task_id].update(update)
            self.tasks[task_id]["progress_history"].append({
                **update,
                "timestamp": datetime.now().isoformat()
            })

    def complete_task(self, task_id: str, result: Dict[str, Any]):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "completed" if result.get("success") else "failed"
            self.tasks[task_id]["progress"] = 100
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list:
        tasks = list(self.tasks.values())
        tasks.sort(key=lambda t: t["started_at"], reverse=True)
        return tasks[:limit]

task_store = TaskStore()

# 全局系统实例
analysis_system = StockAnalysisSystem()

# ============ 后台分析任务 ============

def run_analysis_task(task_id: str, company: str, ticker: str, use_cache: bool):
    """在后台线程执行分析"""
    try:
        def progress_callback(update):
            task_store.update_progress(task_id, {
                "progress": update["progress"],
                "stage": update["stage"],
                "status": update["status"],
                "message": update["message"]
            })

        result = analysis_system.analyze_stock(
            company, ticker,
            use_cache=use_cache,
            progress_callback=progress_callback
        )

        task_store.complete_task(task_id, result)
        logger.info(f"Task {task_id} completed: {company} ({ticker})")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task_store.complete_task(task_id, {
            "success": False,
            "error": str(e),
            "company": company,
            "ticker": ticker
        })

# ============ API 端点 ============

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "AI 股票分析系统",
        "version": "2.0.0",
        "max_concurrent_tasks": Config.MAX_WORKERS,
        "current_tasks": len([t for t in task_store.tasks.values() if t["status"] == "running"])
    }

@app.get("/page", response_class=HTMLResponse)
async def serve_page():
    """返回分析页面"""
    return get_html_page()

@app.post("/analyze", summary="提交股票分析任务")
async def submit_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """提交新的股票分析任务，立即返回任务ID"""
    if not request.company or not request.ticker:
        raise HTTPException(status_code=400, detail="公司名称和股票代码不能为空")

    # 检查缓存
    if request.use_cache:
        cached = analysis_system.cache.check(request.ticker)
        if cached:
            cached_result = analysis_system.cache.get(request.ticker)
            return {
                "success": True,
                "cached": True,
                "result": cached_result
            }

    # 创建新任务
    task_id = task_store.create_task(request.company, request.ticker)
    task_store.tasks[task_id]["status"] = "running"

    # 提交到后台线程
    background_tasks.add_task(
        run_analysis_task,
        task_id,
        request.company,
        request.ticker,
        request.use_cache
    )

    logger.info(f"Task {task_id} submitted: {request.company} ({request.ticker})")

    return {
        "success": True,
        "cached": False,
        "task_id": task_id,
        "company": request.company,
        "ticker": request.ticker,
        "status": "running",
        "message": "分析任务已提交到后台"
    }

@app.get("/task/{task_id}", summary="获取任务状态")
async def get_task_status(task_id: str):
    """获取任务当前状态和进度"""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return task

@app.get("/tasks", summary="列出最近任务")
async def list_recent_tasks(limit: int = 20):
    """列出最近的分析任务"""
    return {
        "success": True,
        "tasks": task_store.list_tasks(limit)
    }

@app.get("/reports/{filename}", summary="下载报告文件")
async def get_report(filename: str):
    """下载生成的报告文件"""
    report_path = os.path.join(os.getcwd(), "reports", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"报告文件 {filename} 不存在")
    return FileResponse(report_path, filename=filename, media_type="text/markdown")

@app.get("/health", summary="健康检查")
async def health_check():
    """健康检查端点"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "pending_tasks": len([t for t in task_store.tasks.values() if t["status"] == "pending"]),
        "running_tasks": len([t for t in task_store.tasks.values() if t["status"] == "running"]),
        "completed_tasks": len([t for t in task_store.tasks.values() if t["status"] == "completed"])
    })


_HTML_PAGE_CACHE = None

def get_html_page():
    """返回前端页面HTML"""
    global _HTML_PAGE_CACHE
    if _HTML_PAGE_CACHE is None:
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'fastapi_page.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            _HTML_PAGE_CACHE = f.read()
    return HTMLResponse(content=_HTML_PAGE_CACHE)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", str(Config.FASTAPI_PORT)))
    uvicorn.run(
        "web.fastapi_app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        workers=1
    )