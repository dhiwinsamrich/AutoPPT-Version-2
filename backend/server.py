"""
FastAPI service exposing PPT generation as background jobs with progress logs.
Run: uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
import logging

from config import TEMPLATE_PRESENTATION_ID, LOG_LEVEL, LOG_FILE
from utils.logger import get_logger
from core.automation import PPTAutomation
from utils.job_manager import JobManager


logger = get_logger("server", LOG_LEVEL, LOG_FILE)
app = FastAPI(title="PPT Automation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_manager = JobManager()


class GenerateAutoRequest(BaseModel):
    template_id: Optional[str] = None
    output_title: Optional[str] = None
    context: Optional[str] = None
    profile: Optional[str] = "company"
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    company_name: Optional[str] = None
    proposal_type: Optional[str] = None
    company_website: Optional[str] = None
    sheets_id: Optional[str] = None  # Can be Sheet ID or full URL
    sheets_range: Optional[str] = "Sheet1"  # Sheet name or A1 range (default: whole sheet)
    primary_color: Optional[str] = None  # User-provided primary color (hex)
    secondary_color: Optional[str] = None  # User-provided secondary color (hex)
    accent_color: Optional[str] = None  # User-provided accent color (hex)


class CopyRequest(BaseModel):
    template_id_or_url: str
    new_title: Optional[str] = None

class InteractiveRequest(BaseModel):
    template_id: Optional[str] = None
    company_name: str
    project_name: str
    project_description: str
    output_title: Optional[str] = None
    company_website: Optional[str] = None
    auto_detect: Optional[bool] = False
    sheets_id: Optional[str] = None  # Can be Sheet ID or full URL
    sheets_range: Optional[str] = "Sheet1"  # Sheet name or A1 range (default: whole sheet)
    primary_color: Optional[str] = None  # User-provided primary color (hex)
    secondary_color: Optional[str] = None  # User-provided secondary color (hex)
    accent_color: Optional[str] = None  # User-provided accent color (hex)


@app.post("/jobs/auto")
def start_generate_auto(req: GenerateAutoRequest):
    params: Dict[str, Any] = req.model_dump()
    job = job_manager.create("generate_auto", params)

    def run_job():
        job.status = "running"
        job.started_at = __import__("time").time()

        # Attach per-job log handler to key loggers
        handler = job_manager.attach_logger_handler(job)
        root = logging.getLogger()
        automation_logger = logging.getLogger("backend.core.automation")
        for target_logger in [root, automation_logger, logging.getLogger("server")]:
            target_logger.addHandler(handler)

        try:
            automation = PPTAutomation(use_ai=True)
            
            # Debug: Log received color parameters
            logger.info("="*80)
            logger.info("🎨 COLOR PARAMETERS RECEIVED FROM FRONTEND:")
            logger.info(f"   primary_color: {params.get('primary_color')}")
            logger.info(f"   secondary_color: {params.get('secondary_color')}")
            logger.info(f"   accent_color: {params.get('accent_color')}")
            logger.info("="*80)
            
            result = automation.generate_presentation_auto(
                params.get("context") or params.get("company_name") or "General Presentation",
                template_id=params.get("template_id") or TEMPLATE_PRESENTATION_ID,
                output_title=params.get("output_title"),
                profile=params.get("profile"),
                project_name=params.get("project_name"),
                project_description=params.get("project_description"),
                company_name=params.get("company_name"),
                proposal_type=params.get("proposal_type"),
                company_website=params.get("company_website"),
                sheets_id=params.get("sheets_id"),
                sheets_range=params.get("sheets_range"),
                primary_color=params.get("primary_color"),
                secondary_color=params.get("secondary_color"),
                accent_color=params.get("accent_color"),
            )

            if not result or not result.get("success"):
                job.status = "failed"
                job.error = (result or {}).get("message") or "Generation failed"
            else:
                job.status = "succeeded"
                job.result = result
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            job.completed_at = __import__("time").time()
            # Remove handler
            for target_logger in [root, automation_logger, logging.getLogger("server")]:
                try:
                    target_logger.removeHandler(handler)
                except Exception:
                    pass

    threading.Thread(target=run_job, daemon=True).start()
    return {"job_id": job.id}


@app.post("/jobs/copy")
def start_copy(req: CopyRequest):
    from core.slides_client import SlidesClient
    params: Dict[str, Any] = req.model_dump()
    job = job_manager.create("copy", params)

    def run_job():
        job.status = "running"
        job.started_at = __import__("time").time()
        handler = job_manager.attach_logger_handler(job)
        root = logging.getLogger()
        for target_logger in [root, logging.getLogger("server")]:
            target_logger.addHandler(handler)
        try:
            client = SlidesClient()
            new_id = client.copy_presentation(
                params.get("template_id_or_url"), params.get("new_title")
            )
            if not new_id:
                job.status = "failed"
                job.error = "Copy failed"
            else:
                job.status = "succeeded"
                job.result = {
                    "presentation_id": new_id,
                    "presentation_url": client.get_presentation_url(new_id),
                }
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            job.completed_at = __import__("time").time()
            try:
                root.removeHandler(handler)
            except Exception:
                pass

    threading.Thread(target=run_job, daemon=True).start()
    return {"job_id": job.id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@app.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"logs": job.logs}


@app.post("/jobs/interactive")
def start_interactive(req: InteractiveRequest):
    params: Dict[str, Any] = req.model_dump()
    job = job_manager.create("interactive", params)

    def run_job():
        job.status = "running"
        job.started_at = __import__("time").time()
        handler = job_manager.attach_logger_handler(job)
        root = logging.getLogger()
        for target_logger in [root, logging.getLogger("server")]:
            target_logger.addHandler(handler)
        try:
            from interactive_mode import InteractiveMode
            im = InteractiveMode()
            
            # Debug: Log received color parameters
            logger.info("="*80)
            logger.info("🎨 COLOR PARAMETERS RECEIVED FROM FRONTEND (INTERACTIVE):")
            logger.info(f"   primary_color: {params.get('primary_color')}")
            logger.info(f"   secondary_color: {params.get('secondary_color')}")
            logger.info(f"   accent_color: {params.get('accent_color')}")
            logger.info("="*80)
            
            result = im.run_with_params(
                template_id=params.get("template_id") or TEMPLATE_PRESENTATION_ID,
                company_name=params["company_name"],
                project_name=params["project_name"],
                project_description=params["project_description"],
                output_title=params.get("output_title"),
                company_website=params.get("company_website"),
                use_ai=True,
                auto_detect=bool(params.get("auto_detect")),
                sheets_id=params.get("sheets_id"),
                sheets_range=params.get("sheets_range"),
                primary_color=params.get("primary_color"),
                secondary_color=params.get("secondary_color"),
                accent_color=params.get("accent_color"),
            )
            if not result or not result.get("success"):
                job.status = "failed"
                job.error = (result or {}).get("message") or "Interactive run failed"
            else:
                job.status = "succeeded"
                job.result = result
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            job.completed_at = __import__("time").time()
            try:
                root.removeHandler(handler)
            except Exception:
                pass

    threading.Thread(target=run_job, daemon=True).start()
    return {"job_id": job.id}


