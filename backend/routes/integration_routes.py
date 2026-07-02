from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import schemas
from database import get_db
from services import integration_service, csv_import_service
from models import IntegrationStatus

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

@router.post("/csv-import/preview")
async def preview_csv_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...)
):
    try:
        preview_data = csv_import_service.parse_and_validate_csv(file, entity_type)
        return JSONResponse(content=preview_data)
    finally:
        await file.close()

@router.post("/csv-import/commit")
async def commit_csv_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Default Integration ID 1 per user request
        commit_data = await csv_import_service.commit_csv_import(db, file, entity_type, integration_id=1)
        return JSONResponse(content=commit_data)
    finally:
        await file.close()

from services.data_quality_service import get_data_quality_metrics
from services.reconciliation_service import get_open_issues, resolve_issue

@router.get("/data-quality")
async def fetch_data_quality_metrics(db: AsyncSession = Depends(get_db)):
    metrics = await get_data_quality_metrics(db)
    return metrics

@router.get("/reconciliation-issues")
async def fetch_reconciliation_issues(db: AsyncSession = Depends(get_db)):
    issues = await get_open_issues(db)
    return [issue.__dict__ for issue in issues] # Note: basic serialization

from pydantic import BaseModel
class ResolutionRequest(BaseModel):
    action: str
    note: str = ""

@router.post("/reconciliation-issues/{id}/resolve")
async def handle_resolve_issue(id: int, req: ResolutionRequest, db: AsyncSession = Depends(get_db)):
    # Assuming user_id = 1 for now (admin)
    try:
        issue = await resolve_issue(db, id, req.action, req.note, user_id=1)
        return {"status": "success", "issue_id": issue.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=schemas.IntegrationResponse)
async def create_integration(
    integration_in: schemas.IntegrationCreate,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.create_integration(db, integration_in)

@router.get("/", response_model=List[schemas.IntegrationResponse])
async def read_integrations(
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.get_integrations(db)

@router.put("/{integration_id}", response_model=schemas.IntegrationResponse)
async def update_integration(
    integration_id: int,
    integration_in: schemas.IntegrationUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.update_integration(db, integration_id, integration_in)

@router.patch("/{integration_id}/status", response_model=schemas.IntegrationResponse)
async def change_status(
    integration_id: int,
    status: IntegrationStatus,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.change_integration_status(db, integration_id, status)
