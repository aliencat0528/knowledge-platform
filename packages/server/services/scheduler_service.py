"""Scheduler service for automated URL crawling."""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from ..config import settings
from ..storage.database import Database, get_db
from .import_service import ImportService
from ..storage.models import ArticleCreate, SourceType

logger = logging.getLogger(__name__)


class SchedulerServiceError(Exception):
    """Exception raised when scheduler service fails."""

    def __init__(self, message: str, code: str = "SCHEDULER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SchedulerService:
    """Service for managing scheduled URL crawling tasks."""

    def __init__(self):
        """Initialize scheduler service."""
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,  # Combine missed runs into one
                "max_instances": 1,  # Only one instance per job
                "misfire_grace_time": 60,  # Grace time for misfired jobs
            },
        )
        self._is_running = False

    async def start(self) -> None:
        """Start the scheduler."""
        if not self._is_running:
            # Load existing tasks from database and schedule them
            await self._load_tasks_from_db()
            self._scheduler.start()
            self._is_running = True
            logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running

    async def _load_tasks_from_db(self) -> None:
        """Load active tasks from database and schedule them."""
        db = await get_db()
        tasks = await db.fetchall(
            "SELECT * FROM scheduled_tasks WHERE is_active = 1"
        )

        for task in tasks:
            try:
                self._add_job(
                    task_id=task["id"],
                    name=task["name"],
                    url_pattern=task["url_pattern"],
                    cron_expression=task["cron_expression"],
                )
            except Exception as e:
                logger.error(f"Failed to load task {task['id']}: {e}")

    def _add_job(
        self,
        task_id: int,
        name: str,
        url_pattern: str,
        cron_expression: str,
    ) -> None:
        """Add a job to the scheduler."""
        job_id = f"task_{task_id}"

        # Remove existing job if exists
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        # Parse cron expression (format: "minute hour day month day_of_week")
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            raise SchedulerServiceError(
                f"Invalid cron expression: {cron_expression}",
                code="INVALID_CRON",
            )

        trigger = CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
        )

        self._scheduler.add_job(
            self._execute_task,
            trigger=trigger,
            id=job_id,
            name=name,
            kwargs={
                "task_id": task_id,
                "url_pattern": url_pattern,
            },
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id}: {name}")

    async def _execute_task(self, task_id: int, url_pattern: str) -> dict[str, Any]:
        """Execute a scheduled task (fetch URL and save).

        Args:
            task_id: Task ID.
            url_pattern: URL or URL pattern to fetch.

        Returns:
            Execution result.
        """
        db = await get_db()
        result = {
            "task_id": task_id,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "urls_processed": 0,
            "articles_saved": 0,
            "errors": [],
        }

        try:
            # Update last_run_at
            await db.execute(
                "UPDATE scheduled_tasks SET last_run_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )
            await db.commit()

            # For now, treat url_pattern as a single URL
            # Future: support patterns like "https://example.com/page/*"
            urls = [url_pattern]

            import_service = ImportService(db)

            async with httpx.AsyncClient(timeout=30.0) as client:
                for url in urls:
                    try:
                        # Fetch the URL
                        response = await client.get(url, follow_redirects=True)
                        response.raise_for_status()

                        # Extract content (simple HTML to text for now)
                        content = response.text
                        title = self._extract_title(content) or url

                        # Create article
                        article = ArticleCreate(
                            source_type=SourceType.WEB,
                            source_id=f"scheduled:{task_id}:{url}",
                            title=title,
                            content=self._html_to_markdown(content),
                            url=url,
                        )

                        # Import with deduplication
                        import_result = await import_service.import_article(article)
                        result["urls_processed"] += 1

                        if import_result.status.value in ("new", "updated"):
                            result["articles_saved"] += 1

                    except Exception as e:
                        result["errors"].append({
                            "url": url,
                            "error": str(e),
                        })
                        logger.error(f"Error fetching {url}: {e}")

            result["status"] = "completed"
            result["completed_at"] = datetime.now().isoformat()

            # Calculate next run time
            job = self._scheduler.get_job(f"task_{task_id}")
            if job and job.next_run_time:
                await db.execute(
                    "UPDATE scheduled_tasks SET next_run_at = ? WHERE id = ?",
                    (job.next_run_time.isoformat(), task_id),
                )
                await db.commit()

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.exception(f"Task {task_id} failed")

        return result

    def _extract_title(self, html: str) -> str | None:
        """Extract title from HTML content."""
        import re
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to simple markdown."""
        try:
            from markdownify import markdownify
            return markdownify(html, strip=["script", "style", "nav", "footer"])
        except ImportError:
            # Fallback: strip HTML tags
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", "", text)
            return text.strip()

    async def add_task(
        self,
        db: Database,
        name: str,
        url_pattern: str,
        cron_expression: str,
    ) -> dict[str, Any]:
        """Add a new scheduled task.

        Args:
            db: Database connection.
            name: Task name.
            url_pattern: URL or pattern to crawl.
            cron_expression: Cron expression (minute hour day month day_of_week).

        Returns:
            Created task info.
        """
        # Validate cron expression
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            raise SchedulerServiceError(
                "Invalid cron expression. Format: 'minute hour day month day_of_week'",
                code="INVALID_CRON",
            )

        # Calculate next run time
        try:
            trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
            )
            next_run = trigger.get_next_fire_time(None, datetime.now())
        except Exception as e:
            raise SchedulerServiceError(
                f"Invalid cron expression: {e}",
                code="INVALID_CRON",
            )

        # Insert into database
        cursor = await db.execute(
            """
            INSERT INTO scheduled_tasks (name, url_pattern, cron_expression, next_run_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, url_pattern, cron_expression, next_run.isoformat() if next_run else None),
        )
        await db.commit()

        task_id = cursor.lastrowid

        # Add to scheduler if running
        if self._is_running:
            self._add_job(task_id, name, url_pattern, cron_expression)

        return {
            "id": task_id,
            "name": name,
            "url_pattern": url_pattern,
            "cron_expression": cron_expression,
            "is_active": True,
            "next_run_at": next_run.isoformat() if next_run else None,
        }

    async def remove_task(self, db: Database, task_id: int) -> bool:
        """Remove a scheduled task.

        Args:
            db: Database connection.
            task_id: Task ID to remove.

        Returns:
            True if removed, False if not found.
        """
        # Check if exists
        task = await db.fetchone(
            "SELECT id FROM scheduled_tasks WHERE id = ?",
            (task_id,),
        )

        if not task:
            return False

        # Remove from scheduler
        job_id = f"task_{task_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        # Delete from database
        await db.execute(
            "DELETE FROM scheduled_tasks WHERE id = ?",
            (task_id,),
        )
        await db.commit()

        return True

    async def update_task(
        self,
        db: Database,
        task_id: int,
        name: str | None = None,
        url_pattern: str | None = None,
        cron_expression: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update a scheduled task.

        Args:
            db: Database connection.
            task_id: Task ID.
            name: New name (optional).
            url_pattern: New URL pattern (optional).
            cron_expression: New cron expression (optional).
            is_active: Active status (optional).

        Returns:
            Updated task info or None if not found.
        """
        task = await db.fetchone(
            "SELECT * FROM scheduled_tasks WHERE id = ?",
            (task_id,),
        )

        if not task:
            return None

        # Build update
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if url_pattern is not None:
            updates.append("url_pattern = ?")
            params.append(url_pattern)
        if cron_expression is not None:
            # Validate
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                raise SchedulerServiceError(
                    "Invalid cron expression",
                    code="INVALID_CRON",
                )
            updates.append("cron_expression = ?")
            params.append(cron_expression)

            # Update next_run_at
            try:
                trigger = CronTrigger(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4],
                )
                next_run = trigger.get_next_fire_time(None, datetime.now())
                updates.append("next_run_at = ?")
                params.append(next_run.isoformat() if next_run else None)
            except Exception:
                pass

        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(task_id)

            await db.execute(
                f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            await db.commit()

        # Reschedule if needed
        if self._is_running:
            job_id = f"task_{task_id}"
            updated_task = await db.fetchone(
                "SELECT * FROM scheduled_tasks WHERE id = ?",
                (task_id,),
            )

            if updated_task["is_active"]:
                self._add_job(
                    task_id,
                    updated_task["name"],
                    updated_task["url_pattern"],
                    updated_task["cron_expression"],
                )
            else:
                # Remove job if deactivated
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)

        return await self.get_task(db, task_id)

    async def get_task(self, db: Database, task_id: int) -> dict[str, Any] | None:
        """Get a task by ID.

        Args:
            db: Database connection.
            task_id: Task ID.

        Returns:
            Task info or None if not found.
        """
        task = await db.fetchone(
            "SELECT * FROM scheduled_tasks WHERE id = ?",
            (task_id,),
        )

        if not task:
            return None

        return {
            "id": task["id"],
            "name": task["name"],
            "url_pattern": task["url_pattern"],
            "cron_expression": task["cron_expression"],
            "is_active": bool(task["is_active"]),
            "last_run_at": task["last_run_at"],
            "next_run_at": task["next_run_at"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"],
        }

    async def list_tasks(
        self,
        db: Database,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List all scheduled tasks.

        Args:
            db: Database connection.
            active_only: Only return active tasks.
            limit: Maximum number of tasks.
            offset: Offset for pagination.

        Returns:
            List of tasks.
        """
        where = "WHERE is_active = 1" if active_only else ""

        tasks = await db.fetchall(
            f"""
            SELECT * FROM scheduled_tasks
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        return [
            {
                "id": t["id"],
                "name": t["name"],
                "url_pattern": t["url_pattern"],
                "cron_expression": t["cron_expression"],
                "is_active": bool(t["is_active"]),
                "last_run_at": t["last_run_at"],
                "next_run_at": t["next_run_at"],
                "created_at": t["created_at"],
                "updated_at": t["updated_at"],
            }
            for t in tasks
        ]

    async def run_task_now(self, db: Database, task_id: int) -> dict[str, Any]:
        """Manually run a task immediately.

        Args:
            db: Database connection.
            task_id: Task ID to run.

        Returns:
            Execution result.
        """
        task = await db.fetchone(
            "SELECT * FROM scheduled_tasks WHERE id = ?",
            (task_id,),
        )

        if not task:
            raise SchedulerServiceError(
                f"Task {task_id} not found",
                code="TASK_NOT_FOUND",
            )

        # Execute the task
        result = await self._execute_task(task_id, task["url_pattern"])

        return result

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get scheduler status.

        Returns:
            Scheduler status info.
        """
        jobs = []
        if self._is_running:
            for job in self._scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                })

        return {
            "is_running": self._is_running,
            "job_count": len(jobs),
            "jobs": jobs,
        }


# Global scheduler instance
_scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Get or create scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


async def start_scheduler() -> None:
    """Start the global scheduler."""
    service = get_scheduler_service()
    await service.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    service = get_scheduler_service()
    await service.stop()
