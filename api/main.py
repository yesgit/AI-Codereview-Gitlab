"""
FastAPI 主应用入口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from biz.utils.db import init_db
from biz.utils.log import logger
from biz.api.routes.daily_report import daily_report_task

from api.routers import auth, webhooks, branch_webhooks, reviews, webhook_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    init_db()
    
    # 启动日报定时任务调度器
    setup_daily_report_scheduler()
    
    yield
    # 关闭时的清理工作


app = FastAPI(
    title="AI Code Review API",
    description="AI 代码审查平台后端 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（按注册顺序，精确路由优先）
# 必须在通配符路由之前注册精确路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["项目配置"])
app.include_router(branch_webhooks.router, prefix="/api/v1/branch-webhooks", tags=["分支配置"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["查询统计"])
app.include_router(webhook_handler.router, prefix="", tags=["Webhook事件"])  # /review/webhook

# 日报路由必须在 serve_spa 之前注册

# 日报路由（必须在 serve_spa 之前注册以避免被通配符捕获）
@app.get("/review/daily_report", tags=["日报"])
async def trigger_daily_report():
    """
    手动触发日报任务
    """
    try:
        daily_report_task()
        return {"message": "Daily report generated and sent successfully."}
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate daily report: {e}")


# Serve frontend static files if built
if os.path.exists("/app/frontend/dist"):
    # 自定义 SPA 路由处理（注册在所有 API 路由之后，作为 fallback）
    from pathlib import Path
    from fastapi.responses import FileResponse
    
    dist_path = Path("/app/frontend/dist")
    
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        """Serve SPA - 所有非 API 和 Webhook 路由都返回 index.html"""
        # FastAPI 会优先匹配精确路由（如 /api/v1/*, /review/webhook, /health）
        # 这个函数只会被未匹配的路径调用（如 /login, /webhooks 等）
        
        # 如果请求的是静态资源，则返回实际文件
        if path and '.' in path and path.split('.')[-1] in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'woff', 'woff2', 'ttf']:
            file_path = dist_path / path
            if file_path.exists():
                return FileResponse(file_path)
        
        # 其他所有请求都返回 index.html（前端路由）
        return FileResponse(dist_path / "index.html")


@app.get("/api", include_in_schema=False)
@app.get("/api/", include_in_schema=False)
@app.get("/api/v1", include_in_schema=False)
@app.get("/api/v1/", include_in_schema=False)
async def api_docs_redirect():
    """Redirect API root to docs"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/")
async def root():
    return {
        "message": "AI Code Review API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def setup_daily_report_scheduler():
    """
    配置并启动日报定时任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
        cron_parts = crontab_expression.split()
        cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts

        # Schedule the task based on the crontab expression
        scheduler.add_job(
            daily_report_task,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day=cron_day,
                month=cron_month,
                day_of_week=cron_day_of_week
            )
        )

        # Start the scheduler
        scheduler.start()
        logger.info(f"Scheduler started successfully with cron expression: {crontab_expression}")
        return scheduler
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
