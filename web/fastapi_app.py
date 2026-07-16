# web/fastapi_app.py
"""FastAPI Web应用 - 异步股票分析系统
支持后台任务、实时进度推送、缓存加速、计时统计
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import os
import sys
import time
from typing import Any
import uuid

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

load_dotenv()

from src.config import Config
from src.stock_analysis_system import StockAnalysisSystem

logger = logging.getLogger(__name__)

# 全局线程池 - 限制并发避免API超限
executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

app = FastAPI(title="AI 股票分析系统 API", description="基于 CrewAI Multi-Agent 的智能股票投资分析", version="2.0.0")

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

    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}

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
            "progress_history": [],
        }
        return task_id

    def update_progress(self, task_id: str, update: dict[str, Any]) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].update(update)
            self.tasks[task_id]["progress_history"].append({**update, "timestamp": datetime.now().isoformat()})

    def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "completed" if result.get("success") else "failed"
            self.tasks[task_id]["progress"] = 100
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list:
        tasks = list(self.tasks.values())
        tasks.sort(key=lambda t: t["started_at"], reverse=True)
        return tasks[:limit]


task_store = TaskStore()

# 全局系统实例
analysis_system = StockAnalysisSystem()

# ============ 后台分析任务 ============


def run_analysis_task(task_id: str, company: str, ticker: str, use_cache: bool) -> None:
    """在后台线程执行分析（带计时和进度）"""
    start_time = time.perf_counter()
    try:

        def progress_callback(update: dict[str, Any]) -> None:
            task_store.update_progress(task_id, update)

        task_store.update_progress(
            task_id,
            {"progress": 5, "stage": "starting", "status": "running", "message": f"开始分析 {company} ({ticker})..."},
        )

        result = analysis_system.analyze_stock(
            company, ticker, use_cache=use_cache, progress_callback=progress_callback
        )

        elapsed = round(time.perf_counter() - start_time, 2)
        result["_elapsed_time"] = elapsed
        task_store.update_progress(
            task_id,
            {
                "progress": 100,
                "stage": "done",
                "status": "completed",
                "message": f"分析完成，耗时 {elapsed}秒",
                "elapsed_time": elapsed,
            },
        )
        task_store.complete_task(task_id, result)
        logger.info(f"Task {task_id} completed: {company} ({ticker}), 耗时 {elapsed}秒")

    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 2)
        logger.error(f"Task {task_id} failed: {str(e)}, 耗时 {elapsed}秒")
        task_store.complete_task(
            task_id,
            {
                "success": False,
                "error": str(e),
                "company": company,
                "ticker": ticker,
                "_elapsed_time": elapsed,
            },
        )


# ============ API 端点 ============


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回分析页面"""
    return get_html_page()


@app.get("/health")
async def health_check():
    """健康检查 — 包含数据源和断路器状态"""
    from src.tools.circuit_breaker import CircuitBreaker

    redis_ok = False
    redis_error = None
    try:
        from src.utils.redis_cache_manager import RedisCacheManager
        rm = RedisCacheManager()
        redis_ok = rm.redis_available
        if not redis_ok:
            redis_error = rm.redis_error
    except Exception:
        redis_error = "unable to import"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "tasks": {
            "pending": len([t for t in task_store.tasks.values() if t["status"] == "pending"]),
            "running": len([t for t in task_store.tasks.values() if t["status"] == "running"]),
            "completed": len([t for t in task_store.tasks.values() if t["status"] == "completed"]),
        },
        "redis": {
            "available": redis_ok,
            "error": redis_error,
        },
        "data_sources": CircuitBreaker.all_status(),
    }


@app.get("/page", response_class=HTMLResponse)
async def serve_page():
    """返回分析页面（兼容旧路由）"""
    return get_html_page()


@app.post("/analyze", summary="提交股票分析任务")
async def submit_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """提交新的股票分析任务，立即返回任务ID"""
    if not request.company or not request.ticker:
        raise HTTPException(status_code=400, detail="公司名称和股票代码不能为空")

    # 检查缓存
    if request.use_cache:
        cached = analysis_system.cache_manager.check_cache(request.ticker)
        if cached:
            cached_result = analysis_system.cache_manager.get_from_cache(request.ticker)
            return {"success": True, "cached": True, "result": cached_result}

    # 创建新任务
    task_id = task_store.create_task(request.company, request.ticker)
    task_store.tasks[task_id]["status"] = "running"

    # 提交到后台线程
    background_tasks.add_task(run_analysis_task, task_id, request.company, request.ticker, request.use_cache)

    logger.info(f"Task {task_id} submitted: {request.company} ({request.ticker})")

    return {
        "success": True,
        "cached": False,
        "task_id": task_id,
        "company": request.company,
        "ticker": request.ticker,
        "status": "running",
        "message": "分析任务已提交到后台",
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
    return {"success": True, "tasks": task_store.list_tasks(limit)}


@app.get("/reports/{filename}", summary="下载报告文件")
async def get_report(filename: str):
    """下载生成的报告文件（.md / .docx）"""
    report_path = os.path.join(os.getcwd(), "reports", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"报告文件 {filename} 不存在")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if filename.endswith(".docx") else "text/markdown"
    return FileResponse(report_path, filename=filename, media_type=media_type)


@app.get("/charts/{filename}", summary="查看图表")
async def get_chart(filename: str):
    """查看生成的图表PNG"""
    chart_path = os.path.join(os.getcwd(), "reports", "charts", filename)
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail=f"图表文件 {filename} 不存在")
    return FileResponse(chart_path, filename=filename, media_type="image/png")


_HTML_PAGE_CACHE = None


def get_html_page():
    """返回前端页面HTML"""
    global _HTML_PAGE_CACHE
    if _HTML_PAGE_CACHE is None:
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "fastapi_page.html")
        with open(html_path, encoding="utf-8") as f:
            _HTML_PAGE_CACHE = f.read()
    return HTMLResponse(content=_HTML_PAGE_CACHE)


if __name__ == "__main__":
    import uvicorn

    port = Config.FASTAPI_PORT
    uvicorn.run("web.fastapi_app:app", host="0.0.0.0", port=port, reload=False, workers=1)