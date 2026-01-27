"""Scheduler API endpoints for managing automated URL crawling."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..storage.database import Database, get_db
from ..services.scheduler_service import (
    SchedulerService,
    SchedulerServiceError,
    get_scheduler_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# Request Models
class CreateTaskRequest(BaseModel):
    """Request model for creating a scheduled task."""

    name: str = Field(..., min_length=1, max_length=200, description="Task name")
    url_pattern: str = Field(
        ...,
        min_length=1,
        description="URL or URL pattern to crawl",
    )
    cron_expression: str = Field(
        ...,
        description="Cron expression: 'minute hour day month day_of_week'",
        examples=["0 */6 * * *", "30 2 * * 1"],
    )


class UpdateTaskRequest(BaseModel):
    """Request model for updating a scheduled task."""

    name: str | None = Field(None, min_length=1, max_length=200)
    url_pattern: str | None = Field(None, min_length=1)
    cron_expression: str | None = Field(None)
    is_active: bool | None = Field(None)


# Response Models
class TaskResponse(BaseModel):
    """Response model for a task."""

    id: int
    name: str
    url_pattern: str
    cron_expression: str
    is_active: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    """Response model for task list."""

    success: bool = True
    tasks: list[TaskResponse]
    total: int


class TaskRunResponse(BaseModel):
    """Response model for task run result."""

    success: bool = True
    task_id: int
    started_at: str
    completed_at: str | None = None
    status: str
    urls_processed: int
    articles_saved: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    success: bool = True
    is_running: bool
    job_count: int
    jobs: list[dict[str, Any]]


def _get_scheduler() -> SchedulerService:
    """Get scheduler service."""
    return get_scheduler_service()


@router.post("/tasks", response_model=dict[str, Any])
async def create_task(
    request: CreateTaskRequest,
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Create a new scheduled crawling task.

    Cron expression format: 'minute hour day month day_of_week'

    Examples:
    - "0 */6 * * *" - Every 6 hours
    - "30 2 * * *" - Daily at 2:30 AM
    - "0 9 * * 1" - Every Monday at 9:00 AM
    - "*/30 * * * *" - Every 30 minutes
    """
    try:
        task = await scheduler.add_task(
            db=db,
            name=request.name,
            url_pattern=request.url_pattern,
            cron_expression=request.cron_expression,
        )

        return {
            "success": True,
            "task": task,
        }

    except SchedulerServiceError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )
    except Exception as e:
        logger.exception("Error creating task")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    active_only: bool = Query(False, description="Only return active tasks"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> TaskListResponse:
    """List all scheduled tasks."""
    try:
        tasks = await scheduler.list_tasks(
            db=db,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

        # Get total count
        where = "WHERE is_active = 1" if active_only else ""
        total_result = await db.fetchone(
            f"SELECT COUNT(*) as count FROM scheduled_tasks {where}"
        )
        total = total_result["count"] if total_result else 0

        return TaskListResponse(
            success=True,
            tasks=[
                TaskResponse(
                    id=t["id"],
                    name=t["name"],
                    url_pattern=t["url_pattern"],
                    cron_expression=t["cron_expression"],
                    is_active=t["is_active"],
                    last_run_at=str(t["last_run_at"]) if t["last_run_at"] else None,
                    next_run_at=str(t["next_run_at"]) if t["next_run_at"] else None,
                    created_at=str(t["created_at"]),
                    updated_at=str(t["updated_at"]),
                )
                for t in tasks
            ],
            total=total,
        )

    except Exception as e:
        logger.exception("Error listing tasks")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/tasks/{task_id}", response_model=dict[str, Any])
async def get_task(
    task_id: int,
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Get a specific task by ID."""
    try:
        task = await scheduler.get_task(db, task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task {task_id} not found",
                },
            )

        return {
            "success": True,
            "task": task,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting task")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.put("/tasks/{task_id}", response_model=dict[str, Any])
async def update_task(
    task_id: int,
    request: UpdateTaskRequest,
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Update a scheduled task."""
    try:
        task = await scheduler.update_task(
            db=db,
            task_id=task_id,
            name=request.name,
            url_pattern=request.url_pattern,
            cron_expression=request.cron_expression,
            is_active=request.is_active,
        )

        if not task:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task {task_id} not found",
                },
            )

        return {
            "success": True,
            "task": task,
        }

    except HTTPException:
        raise
    except SchedulerServiceError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )
    except Exception as e:
        logger.exception("Error updating task")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Delete a scheduled task."""
    try:
        deleted = await scheduler.remove_task(db, task_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task {task_id} not found",
                },
            )

        return {
            "success": True,
            "message": "Task deleted",
            "task_id": task_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting task")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.post("/tasks/{task_id}/run", response_model=TaskRunResponse)
async def run_task(
    task_id: int,
    db: Database = Depends(get_db),
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> TaskRunResponse:
    """Manually run a task immediately.

    This triggers the task to execute now, regardless of its schedule.
    """
    try:
        result = await scheduler.run_task_now(db, task_id)

        return TaskRunResponse(
            success=True,
            task_id=result["task_id"],
            started_at=result["started_at"],
            completed_at=result.get("completed_at"),
            status=result["status"],
            urls_processed=result["urls_processed"],
            articles_saved=result["articles_saved"],
            errors=result.get("errors", []),
        )

    except SchedulerServiceError as e:
        raise HTTPException(
            status_code=404 if e.code == "TASK_NOT_FOUND" else 400,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )
    except Exception as e:
        logger.exception("Error running task")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> SchedulerStatusResponse:
    """Get scheduler status and running jobs."""
    status = scheduler.get_scheduler_status()

    return SchedulerStatusResponse(
        success=True,
        is_running=status["is_running"],
        job_count=status["job_count"],
        jobs=status["jobs"],
    )


@router.post("/start")
async def start_scheduler(
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Start the scheduler.

    This will load all active tasks from the database and start executing them
    according to their schedules.
    """
    try:
        await scheduler.start()
        return {
            "success": True,
            "message": "Scheduler started",
            "status": scheduler.get_scheduler_status(),
        }
    except Exception as e:
        logger.exception("Error starting scheduler")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.post("/stop")
async def stop_scheduler(
    scheduler: SchedulerService = Depends(_get_scheduler),
) -> dict[str, Any]:
    """Stop the scheduler.

    This will stop all scheduled jobs. Tasks remain in the database and will
    resume when the scheduler is started again.
    """
    try:
        await scheduler.stop()
        return {
            "success": True,
            "message": "Scheduler stopped",
        }
    except Exception as e:
        logger.exception("Error stopping scheduler")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )
