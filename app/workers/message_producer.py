"""Message Producer for sending tasks to message queues."""
from typing import Dict, Any, Optional
from app.workers.celery_app import app as celery_app


class MessageProducer:
    """
    Component for sending tasks to message queues.
    
    This class provides methods to send various types of tasks
    to appropriate queues with proper routing.
    """
    
    def __init__(self, celery_app=celery_app):
        """
        Initialize with a Celery app instance.
        
        Args:
            celery_app: Configured Celery application
        """
        self.celery_app = celery_app
    
    def send_llm_task(self, task_name: str, **kwargs) -> str:
        """
        Send a task to the LLM queue.
        
        Args:
            task_name: Name of the task function (without module prefix)
            **kwargs: Task arguments
            
        Returns:
            Task ID for tracking
        """
        task = self.celery_app.send_task(
            f"app.workers.llm_worker.{task_name}",
            kwargs=kwargs,
            queue="llm_queue"
        )
        return task.id
    
    def send_context_task(self, task_name: str, **kwargs) -> str:
        """Send a task to the context analysis queue."""
        task = self.celery_app.send_task(
            f"app.workers.context_worker.{task_name}",
            kwargs=kwargs,
            queue="context_queue"
        )
        return task.id
    
    def send_diary_task(self, task_name: str, **kwargs) -> str:
        """Send a task to the diary queue."""
        task = self.celery_app.send_task(
            f"app.workers.diary_worker.{task_name}",
            kwargs=kwargs,
            queue="db_queue"
        )
        return task.id
    
    def send_tarot_task(self, task_name: str, **kwargs) -> str:
        """Send a task to the tarot queue."""
        task = self.celery_app.send_task(
            f"app.workers.tarot_worker.{task_name}",
            kwargs=kwargs,
            queue="tarot_queue"
        )
        return task.id
    
    def send_astro_task(self, task_name: str, **kwargs) -> str:
        """Send a task to the astrology queue."""
        task = self.celery_app.send_task(
            f"app.workers.astro_worker.{task_name}",
            kwargs=kwargs,
            queue="astro_queue"
        )
        return task.id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task by ID.
        
        Args:
            task_id: Task ID returned when task was created
            
        Returns:
            Dictionary with task status information
        """
        task = self.celery_app.AsyncResult(task_id)
        
        result = {
            "task_id": task_id,
            "status": task.status,
        }
        
        if task.successful():
            result["result"] = task.get()
        elif task.failed():
            result["error"] = str(task.result)
        
        return result
    
    def send_context_analysis_task(self, chat_id: int, user_id: int) -> str:
        """Send task to analyze chat context and possibly create diary entry."""
        task = self.celery_app.send_task(
            "app.workers.context_worker.analyze_conversation_context",
            kwargs={"chat_id": chat_id, "user_id": user_id},
            queue="context_queue"
        )
        return task.id 