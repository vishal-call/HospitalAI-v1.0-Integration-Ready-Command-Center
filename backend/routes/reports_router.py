import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
import models
from services.auth import get_current_user
from fpdf import FPDF

router = APIRouter(prefix="/api/reports", tags=["reports"])

class HandoverPDF(FPDF):
    def header(self):
        # Hospital Logo styling
        self.set_fill_color(30, 41, 59) # Slate-800
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 20)
        self.cell(0, 15, 'HOSPITALAI COMMAND CENTER', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('helvetica', 'I', 11)
        self.cell(0, 5, 'Shift Handover & Clinical Census Summary', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        
        self.set_text_color(0, 0, 0)
        self.ln(25)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'CONFIDENTIAL - SHIFT HANDOVER REPORT | Page {self.page_no()}/{{nb}}', border=False, new_x="LMARGIN", new_y="NEXT", align='C')

@router.get("/handover")
async def get_handover_report(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        # 1. Fetch census metrics
        wards_res = await db.execute(
            select(models.Ward).options(selectinload(models.Ward.beds))
        )
        wards = wards_res.scalars().all()
        
        total_beds = sum(w.capacity for w in wards)
        total_occupied = 0
        ward_summaries = []
        
        for w in wards:
            occ = sum(1 for b in w.beds if b.status == models.BedStatus.OCCUPIED)
            total_occupied += occ
            ward_summaries.append({
                "name": w.name,
                "occupied": occ,
                "capacity": w.capacity,
                "utilization": round((occ / w.capacity) * 100.0, 1) if w.capacity > 0 else 0
            })
            
        # 2. Fetch all CRITICAL patients
        crit_res = await db.execute(
            select(models.Patient)
            .options(selectinload(models.Patient.bed).selectinload(models.Bed.ward))
            .where(models.Patient.status == models.PatientStatus.CRITICAL)
            .where(models.Patient.discharged_at == None)
            .order_by(models.Patient.criticality_score.desc())
        )
        critical_patients = crit_res.scalars().all()
        
        # 3. Fetch all active alerts (is_acknowledged = False)
        alerts_res = await db.execute(
            select(models.Alert)
            .options(selectinload(models.Alert.patient))
            .where(models.Alert.is_acknowledged == False)
            .order_by(models.Alert.created_at.desc())
        )
        active_alerts = alerts_res.scalars().all()
        
        # 4. Fetch pending AI recommendations
        recs_res = await db.execute(
            select(models.Recommendation)
            .options(selectinload(models.Recommendation.patient))
            .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
            .order_by(models.Recommendation.criticality_score.desc())
        )
        pending_recs = recs_res.scalars().all()

        # 5. Build PDF document
        pdf = HandoverPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("helvetica", size=10)
        
        # --- SECTION: Hospital Summary ---
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, "1. Hospital Census Overview", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(0, 6, f"Total Capacity: {total_beds} Beds", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Total Occupied: {total_occupied} Beds (Overall Utilization: {round((total_occupied / total_beds)*100, 1) if total_beds > 0 else 0}%)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        
        # Draw a summary table
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(60, 6, "Ward Name", border=1)
        pdf.cell(40, 6, "Occupied / Capacity", border=1, align="C")
        pdf.cell(40, 6, "Utilization Rate", border=1, align="C")
        pdf.ln(6)
        
        pdf.set_font("helvetica", "", 9)
        for ws in ward_summaries:
            pdf.cell(60, 6, ws["name"], border=1)
            pdf.cell(40, 6, f"{ws['occupied']} / {ws['capacity']}", border=1, align="C")
            pdf.cell(40, 6, f"{ws['utilization']}%", border=1, align="C")
            pdf.ln(6)
            
        pdf.ln(8)
        
        # --- SECTION: Critical Patients ---
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(185, 28, 28) # Red-700
        pdf.cell(0, 10, f"2. Critical Patients ({len(critical_patients)} Admitted)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        
        if not critical_patients:
            pdf.cell(0, 6, "No critical patients currently admitted.", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(45, 6, "Patient Name", border=1)
            pdf.cell(20, 6, "Age/Gender", border=1, align="C")
            pdf.cell(45, 6, "Current Bed / Ward", border=1)
            pdf.cell(30, 6, "Criticality Score", border=1, align="C")
            pdf.cell(50, 6, "Admission Reason", border=1)
            pdf.ln(6)
            
            pdf.set_font("helvetica", "", 9)
            for cp in critical_patients:
                bed_str = f"{cp.bed.bed_number} ({cp.bed.ward.name})" if cp.bed and cp.bed.ward else "N/A"
                pdf.cell(45, 6, cp.name, border=1)
                pdf.cell(20, 6, f"{cp.age}y / {cp.gender[0]}", border=1, align="C")
                pdf.cell(45, 6, bed_str, border=1)
                pdf.cell(30, 6, f"{cp.criticality_score:.1f} / 10.0", border=1, align="C")
                pdf.cell(50, 6, cp.admission_reason[:25], border=1)
                pdf.ln(6)
                
        pdf.ln(8)
        
        # --- SECTION: Active Alerts ---
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(217, 119, 6) # Amber-600
        pdf.cell(0, 10, f"3. Active Clinical Alerts ({len(active_alerts)} Active)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        
        if not active_alerts:
            pdf.cell(0, 6, "No active unacknowledged alerts.", new_x="LMARGIN", new_y="NEXT")
        else:
            for alert in active_alerts:
                pat_name = alert.patient.name if alert.patient else "System Alert"
                alert_type_str = alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type)
                msg = f"[{alert_type_str}] {pat_name}: {alert.message}"
                pdf.multi_cell(0, 6, msg, border=1)
                pdf.ln(1)
                
        pdf.ln(8)
        
        # --- SECTION: Pending AI Recommendations ---
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(79, 70, 229) # Indigo-600
        pdf.cell(0, 10, f"4. Pending AI Transfer Recommendations ({len(pending_recs)} Pending)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        
        if not pending_recs:
            pdf.cell(0, 6, "No pending AI transfer recommendations.", new_x="LMARGIN", new_y="NEXT")
        else:
            for rec in pending_recs:
                pat_name = rec.patient.name if rec.patient else f"Patient #{rec.patient_id}"
                rec_type_str = rec.recommendation_type.value if hasattr(rec.recommendation_type, "value") else str(rec.recommendation_type)
                msg = f"[{rec_type_str}] Patient: {pat_name} (Score: {rec.criticality_score:.1f})\nReasoning: {rec.reasoning}"
                pdf.multi_cell(0, 6, msg, border=1)
                pdf.ln(2)

        # 6. Stream back bytes
        pdf_bytes = pdf.output(dest='S')
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=shift_handover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate handover report PDF: {str(e)}"
        )
