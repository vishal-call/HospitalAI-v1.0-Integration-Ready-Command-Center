from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

import models
import schemas
import crud
from database import get_db
from services.auth import check_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/analytics/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """
    Retrieve operational telemetry and AI performance metrics.
    Accessible only to the ADMIN role.
    """
    # 1. Query all operational logs
    res = await db.execute(
        select(models.OperationalLog)
    )
    logs = res.scalars().all()
    
    # 2. Compute metrics
    approved_count = 0
    rejected_count = 0
    expired_count = 0
    response_times = []
    alert_triggered_count = 0
    recommendation_generated_count = 0
    
    for log in logs:
        if log.event_type == "ALERT_TRIGGERED":
            alert_triggered_count += 1
        elif log.event_type == "RECOMMENDATION_GENERATED":
            recommendation_generated_count += 1
        elif log.event_type == "COORDINATOR_ACTION":
            action = log.payload.get("action")
            rt = log.payload.get("response_time_seconds")
            
            if action == "APPROVE":
                approved_count += 1
                if rt is not None:
                    response_times.append(rt)
            elif action == "REJECT":
                rejected_count += 1
                if rt is not None:
                    response_times.append(rt)
            elif action == "EXPIRED":
                expired_count += 1
                if rt is not None:
                    response_times.append(rt)
                    
    total_actions = approved_count + rejected_count
    ai_acceptance_rate = (approved_count / total_actions * 100.0) if total_actions > 0 else 0.0
    
    # Calculate median
    if not response_times:
        median_response_time = 0.0
    else:
        response_times.sort()
        n = len(response_times)
        if n % 2 == 1:
            median_response_time = response_times[n // 2]
        else:
            median_response_time = (response_times[n // 2 - 1] + response_times[n // 2]) / 2.0
            
    return {
        "alert_triggered_count": alert_triggered_count,
        "recommendation_generated_count": recommendation_generated_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "expired_count": expired_count,
        "ai_acceptance_rate": round(ai_acceptance_rate, 2),
        "median_response_time_seconds": round(median_response_time, 2)
    }

@router.post("/wards", response_model=schemas.WardResponse)
async def create_ward(
    payload: schemas.WardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Create a new ward and log the admin action."""
    # Check if ward already exists
    existing_res = await db.execute(
        select(models.Ward).where(models.Ward.name == payload.name)
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ward with name {payload.name} already exists."
        )
        
    ward = models.Ward(
        name=payload.name,
        type=payload.type,
        capacity=payload.capacity
    )
    db.add(ward)
    await db.flush()
    
    # Audit log
    await crud.create_audit_log(
        db,
        action="WARD_CREATE",
        entity_type="ward",
        entity_id=ward.id,
        before_data=None,
        after_data={"name": ward.name, "type": ward.type.value, "capacity": ward.capacity},
        user_id=str(current_user.id)
    )
    await db.commit()
    
    # Re-fetch with selectinload to prevent lazy-loading errors on serialization
    from sqlalchemy.orm import selectinload
    ward_res = await db.execute(
        select(models.Ward)
        .options(selectinload(models.Ward.beds))
        .where(models.Ward.id == ward.id)
    )
    ward = ward_res.scalar_one()
    ward.occupied_beds_count = 0
    ward.utilization_rate = 0.0
    ward.current_nurses = 0
    ward.max_patient_ratio = 2
    
    return ward

@router.delete("/wards/{id}")
async def delete_ward(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Delete a ward. Enforces that no active beds exist."""
    from sqlalchemy.orm import selectinload
    ward_res = await db.execute(
        select(models.Ward).options(selectinload(models.Ward.beds)).where(models.Ward.id == id)
    )
    ward = ward_res.scalar_one_or_none()
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ward not found."
        )
        
    if len(ward.beds) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete ward: active beds exist in this ward."
        )
        
    before_value = {"id": ward.id, "name": ward.name, "type": ward.type.value, "capacity": ward.capacity}
    await db.delete(ward)
    await db.flush()
    
    # Audit log
    await crud.create_audit_log(
        db,
        action="WARD_DELETE",
        entity_type="ward",
        entity_id=id,
        before_data=before_value,
        after_data=None,
        user_id=str(current_user.id)
    )
    await db.commit()
    return {"status": "success", "message": "Ward deleted successfully."}

@router.post("/beds", response_model=schemas.BedResponse)
async def create_bed(
    payload: schemas.BedCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Assign a new bed to a specific ward with relational validation."""
    ward_res = await db.execute(
        select(models.Ward).where(models.Ward.id == payload.ward_id)
    )
    ward = ward_res.scalar_one_or_none()
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward ID {payload.ward_id} not found."
        )
        
    # Check capacity limit
    bed_count_res = await db.execute(
        select(func.count(models.Bed.id)).where(models.Bed.ward_id == payload.ward_id)
    )
    current_beds = bed_count_res.scalar() or 0
    if current_beds >= ward.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add bed: Ward {ward.name} is already at its capacity of {ward.capacity}."
        )
        
    # Check if bed number exists in this ward
    existing_bed = await db.execute(
        select(models.Bed).where(models.Bed.ward_id == payload.ward_id, models.Bed.bed_number == payload.bed_number)
    )
    if existing_bed.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bed number {payload.bed_number} already exists in ward {ward.name}."
        )
        
    bed = models.Bed(
        ward_id=payload.ward_id,
        bed_number=payload.bed_number,
        status=payload.status
    )
    db.add(bed)
    await db.flush()
    
    # Audit log
    await crud.create_audit_log(
        db,
        action="BED_CREATE",
        entity_type="bed",
        entity_id=bed.id,
        before_data=None,
        after_data={"ward_id": bed.ward_id, "bed_number": bed.bed_number, "status": bed.status.value},
        user_id=str(current_user.id)
    )
    await db.commit()
    
    # Re-fetch with selectinload to prevent lazy-loading errors on serialization
    from sqlalchemy.orm import selectinload
    bed_res = await db.execute(
        select(models.Bed)
        .options(selectinload(models.Bed.patient))
        .where(models.Bed.id == bed.id)
    )
    bed = bed_res.scalar_one()
    
    return bed

@router.delete("/beds/{id}")
async def delete_bed(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Delete a bed. Enforces that no active patient is assigned to it."""
    bed_res = await db.execute(
        select(models.Bed).where(models.Bed.id == id)
    )
    bed = bed_res.scalar_one_or_none()
    if not bed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bed not found."
        )
        
    if bed.patient_id is not None or bed.status == models.BedStatus.OCCUPIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete bed: a patient is currently assigned to it."
        )
        
    before_value = {"id": bed.id, "ward_id": bed.ward_id, "bed_number": bed.bed_number, "status": bed.status.value}
    await db.delete(bed)
    await db.flush()
    
    # Audit log
    await crud.create_audit_log(
        db,
        action="BED_DELETE",
        entity_type="bed",
        entity_id=id,
        before_data=before_value,
        after_data=None,
        user_id=str(current_user.id)
    )
    await db.commit()
    return {"status": "success", "message": "Bed deleted successfully."}

@router.patch("/staff/role", response_model=schemas.UserResponse)
async def update_staff_role(
    payload: schemas.StaffRoleUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Dynamically reassign a staff member's RBAC role."""
    user_res = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {payload.email} not found."
        )
        
    before_value = {"email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)}
    user.role = payload.role
    db.add(user)
    await db.flush()
    
    # Audit log
    await crud.create_audit_log(
        db,
        action="USER_ROLE_UPDATE",
        entity_type="user",
        entity_id=user.id,
        before_data=before_value,
        after_data={"email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)},
        user_id=str(current_user.id)
    )
    await db.commit()
    return user
