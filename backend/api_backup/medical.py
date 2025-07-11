from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from models.schemas import MedicalDiagnosisCreate, MedicalReceiptCreate, MedicalDiagnosisResponse, MedicalReceiptResponse

router = APIRouter(tags=["🏥 의료 정보"])

@router.post("/diagnoses", response_model=dict, summary="진단서 등록", description="고객의 의료 진단서 정보를 입력하여 보험금 청구를 위한 진단 데이터를 생성합니다.")
async def create_medical_diagnosis(
    diagnosis: MedicalDiagnosisCreate,
    db: Session = Depends(get_db)
):
    """
    고객의 의료 진단서 정보를 입력하여 보험금 청구를 위한 진단 데이터를 생성합니다.
    
    - **patient_name**: 환자 이름 (필수)
    - **patient_ssn**: 환자 주민등록번호 (필수)
    - **diagnosis_name**: 진단명
    - **diagnosis_date**: 진단 날짜
    - **icd_code**: ICD 코드 (선택사항)
    - **hospital_name**: 병원명
    - **doctor_name**: 담당 의사명
    - **admission_days**: 입원 일수
    """
    # 시스템 사용자 ID (기본값 1)
    system_user_id = 1
    
    db_diagnosis = MedicalDiagnosis(
        user_id=system_user_id,
        patient_name=diagnosis.patient_name,
        patient_ssn=diagnosis.patient_ssn,
        diagnosis_name=diagnosis.diagnosis_name,
        diagnosis_date=diagnosis.diagnosis_date,
        diagnosis_text=diagnosis.diagnosis_text or diagnosis.diagnosis_name,
        icd_code=diagnosis.icd_code,
        hospital_name=diagnosis.hospital_name,
        doctor_name=diagnosis.doctor_name,
        admission_days=diagnosis.admission_days or 0
    )
    db.add(db_diagnosis)
    db.commit()
    db.refresh(db_diagnosis)
    
    return {
        "message": "진단서가 성공적으로 등록되었습니다", 
        "id": db_diagnosis.id,
        "patient_name": diagnosis.patient_name,
        "patient_ssn": diagnosis.patient_ssn,
        "diagnosis_name": diagnosis.diagnosis_name,
        "diagnosis_date": diagnosis.diagnosis_date.isoformat(),
        "hospital_name": diagnosis.hospital_name
    }

@router.post("/receipts", response_model=dict, summary="영수증 등록", description="고객의 의료 영수증 정보를 입력하여 보험금 청구를 위한 진료비 데이터를 생성합니다.")
async def create_medical_receipt(
    receipt: MedicalReceiptCreate,
    db: Session = Depends(get_db)
):
    """
    고객의 의료 영수증 정보를 입력하여 보험금 청구를 위한 진료비 데이터를 생성합니다.
    
    - **patient_name**: 환자 이름 (필수)
    - **receipt_date**: 영수증 날짜
    - **total_amount**: 총 진료비
    - **hospital_name**: 병원명
    - **treatment_details**: 진료 내역
    
    주의: 영수증에는 주민번호가 없으므로, 청구 생성 시 진단서의 주민번호를 기준으로 매칭됩니다.
    """
    # 시스템 사용자 ID (기본값 1)
    system_user_id = 1
    
    db_receipt = MedicalReceipt(
        user_id=system_user_id,
        patient_name=receipt.patient_name,
        patient_ssn=None,  # 영수증에는 주민번호가 없음
        receipt_date=receipt.receipt_date,
        total_amount=receipt.total_amount,
        hospital_name=receipt.hospital_name,
        treatment_details=receipt.treatment_details
    )
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    
    return {
        "message": "영수증이 성공적으로 등록되었습니다", 
        "id": db_receipt.id,
        "patient_name": receipt.patient_name,
        "receipt_date": receipt.receipt_date.isoformat(),
        "total_amount": receipt.total_amount,
        "hospital_name": receipt.hospital_name
    }

@router.get("/diagnoses", response_model=List[MedicalDiagnosisResponse], summary="진단서 목록 조회", description="등록된 모든 진단서 목록을 페이지네이션으로 조회합니다.")
async def get_all_diagnoses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    모든 진단서 목록을 조회합니다.
    
    - **skip**: 건너뛸 항목 수 (기본값: 0)
    - **limit**: 조회할 최대 항목 수 (기본값: 100)
    - 삭제되지 않은 진단서만 조회
    """
    diagnoses = db.query(MedicalDiagnosis).filter(
        MedicalDiagnosis.is_deleted == False
    ).offset(skip).limit(limit).all()
    
    return diagnoses

@router.get("/receipts", response_model=List[MedicalReceiptResponse], summary="영수증 목록 조회", description="등록된 모든 영수증 목록을 페이지네이션으로 조회합니다.")
async def get_all_receipts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    모든 영수증 목록을 조회합니다.
    
    - **skip**: 건너뛸 항목 수 (기본값: 0)
    - **limit**: 조회할 최대 항목 수 (기본값: 100)
    - 삭제되지 않은 영수증만 조회
    """
    receipts = db.query(MedicalReceipt).filter(
        MedicalReceipt.is_deleted == False
    ).offset(skip).limit(limit).all()
    
    return receipts

@router.get("/patient/{patient_ssn}/diagnoses", response_model=List[MedicalDiagnosisResponse], summary="환자별 진단서 조회", description="특정 환자의 모든 진단서를 주민등록번호로 조회합니다.")
async def get_patient_diagnoses(
    patient_ssn: str,
    db: Session = Depends(get_db)
):
    """
    특정 환자의 모든 진단서를 조회합니다.
    
    - **patient_ssn**: 환자 주민등록번호
    - 해당 환자의 모든 진단서를 최신순으로 조회
    """
    diagnoses = db.query(MedicalDiagnosis).filter(
        MedicalDiagnosis.patient_ssn == patient_ssn,
        MedicalDiagnosis.is_deleted == False
    ).order_by(MedicalDiagnosis.created_at.desc()).all()
    
    return diagnoses

@router.get("/patient/{patient_ssn}/receipts", response_model=List[MedicalReceiptResponse], summary="환자별 영수증 조회", description="특정 환자의 모든 영수증을 주민등록번호로 조회합니다.")
async def get_patient_receipts(
    patient_ssn: str,
    db: Session = Depends(get_db)
):
    """
    특정 환자의 모든 영수증을 조회합니다.
    
    - **patient_ssn**: 환자 주민등록번호
    - 해당 환자의 모든 영수증을 최신순으로 조회
    """
    receipts = db.query(MedicalReceipt).filter(
        MedicalReceipt.patient_ssn == patient_ssn,
        MedicalReceipt.is_deleted == False
    ).order_by(MedicalReceipt.created_at.desc()).all()
    
    return receipts

@router.get("/diagnoses/{diagnosis_id}", response_model=MedicalDiagnosisResponse, summary="진단서 상세 조회", description="특정 진단서의 상세 정보를 ID로 조회합니다.")
async def get_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 진단서의 상세 정보를 조회합니다.
    
    - **diagnosis_id**: 조회할 진단서 ID
    - 삭제되지 않은 진단서만 조회 가능
    - 존재하지 않는 진단서 조회 시 404 에러 반환
    """
    diagnosis = db.query(MedicalDiagnosis).filter(
        MedicalDiagnosis.id == diagnosis_id,
        MedicalDiagnosis.is_deleted == False
    ).first()
    
    if not diagnosis:
        raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다")
    
    return diagnosis

@router.get("/receipts/{receipt_id}", response_model=MedicalReceiptResponse, summary="영수증 상세 조회", description="특정 영수증의 상세 정보를 ID로 조회합니다.")
async def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 영수증의 상세 정보를 조회합니다.
    
    - **receipt_id**: 조회할 영수증 ID
    - 삭제되지 않은 영수증만 조회 가능
    - 존재하지 않는 영수증 조회 시 404 에러 반환
    """
    receipt = db.query(MedicalReceipt).filter(
        MedicalReceipt.id == receipt_id,
        MedicalReceipt.is_deleted == False
    ).first()
    
    if not receipt:
        raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다")
    
    return receipt 