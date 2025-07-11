from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
from typing import List

from models.database import get_db
from models.models import InsuranceClause, InsuranceCompany, InsuranceProduct
from services.pdf_processor import PolicyProcessor

router = APIRouter(tags=["📄 PDF 처리"])

def get_or_create_samsung_company(db: Session) -> InsuranceCompany:
    """삼성생명 보험사를 가져오거나 생성합니다."""
    company = db.query(InsuranceCompany).filter(InsuranceCompany.code == "SAMSUNG").first()
    if not company:
        company = InsuranceCompany(
            name="삼성생명",
            code="SAMSUNG"
        )
        db.add(company)
        db.commit()
        db.refresh(company)
    return company

def get_or_create_default_product(db: Session, company_id: int) -> InsuranceProduct:
    """기본 보험 상품을 가져오거나 생성합니다."""
    product = db.query(InsuranceProduct).filter(
        InsuranceProduct.company_id == company_id,
        InsuranceProduct.product_code == "DEFAULT_PRODUCT"
    ).first()
    
    if not product:
        product = InsuranceProduct(
            company_id=company_id,
            name="기본 보험 상품",
            product_code="DEFAULT_PRODUCT",
            description="PDF에서 추출된 특약들이 저장되는 기본 상품"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
    return product

@router.post("/process-pdf", summary="PDF 보험 조항 추출", description="보험 약관 PDF 파일을 업로드하여 OpenAI GPT-4o AI가 특약(조항)을 자동으로 추출하고 데이터베이스에 저장합니다. 삼성생명 보험사로 자동 설정됩니다.")
async def process_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    보험 약관 PDF 파일을 업로드하여 AI가 특약(조항)을 자동으로 추출하고 데이터베이스에 저장합니다.
    
    - **file**: 업로드할 PDF 파일 (보험 약관서)
    - OpenAI GPT-4o를 사용하여 특약 자동 추출
    - 삼성생명 보험사로 자동 설정
    - 추출된 특약은 데이터베이스에 저장
    - 처리 결과는 JSON 파일로도 저장
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
    
    # 파일 저장
    input_dir = Path("input_pdfs")
    input_dir.mkdir(exist_ok=True)
    file_path = input_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # PDF 처리
    processor = PolicyProcessor()
    try:
        raw_data = processor.extract_from_pdf(file_path)
        cleaned_data = processor.clean_data(raw_data)
        final_data = processor.fix_data_structure(cleaned_data)
        
        # 결과를 JSON 파일로도 저장
        output_filename = f"processed_{file.filename.replace('.pdf', '.json')}"
        processor.save_results(final_data, output_filename)
        
        # DB에 저장
        saved_clauses = save_clauses_to_db(final_data, db)
        
        return {
            "message": "PDF 처리 및 DB 저장 완료",
            "filename": file.filename,
            "extracted_items": len(final_data),
            "saved_clauses": len(saved_clauses),
            "output_file": output_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 처리 중 오류 발생: {str(e)}")

def save_clauses_to_db(clauses_data: List[dict], db: Session) -> List[InsuranceClause]:
    """추출된 특약 데이터를 DB에 저장합니다."""
    # 삼성생명 보험사 가져오기
    company = get_or_create_samsung_company(db)
    
    # 기본 상품 가져오기
    product = get_or_create_default_product(db, company.id)
    
    saved_clauses = []
    
    for clause_data in clauses_data:
        try:
            # 기존에 같은 이름의 특약이 있는지 확인
            existing_clause = db.query(InsuranceClause).filter(
                InsuranceClause.product_id == product.id,
                InsuranceClause.clause_name == clause_data.get('clause_name', '')
            ).first()
            
            if existing_clause:
                # 기존 특약 업데이트
                max_total = clause_data.get('max_total')
                if max_total is None:
                    # max_total이 None인 경우 기본값 설정
                    if clause_data.get('unit_type') == 'percentage':
                        max_total = 100  # 퍼센트형은 최대 100%
                    else:
                        max_total = clause_data.get('per_unit', 0)  # 금액형은 per_unit과 동일
                
                existing_clause.category = clause_data.get('category', '')
                existing_clause.per_unit = clause_data.get('per_unit', 0)
                existing_clause.max_total = max_total
                existing_clause.unit_type = clause_data.get('unit_type', 'amount')
                existing_clause.conditions = clause_data.get('condition', '')
                existing_clause.description = f"PDF에서 추출된 특약: {clause_data.get('clause_name', '')}"
                saved_clauses.append(existing_clause)
            else:
                # 새 특약 생성
                max_total = clause_data.get('max_total')
                if max_total is None:
                    # max_total이 None인 경우 기본값 설정
                    if clause_data.get('unit_type') == 'percentage':
                        max_total = 100  # 퍼센트형은 최대 100%
                    else:
                        max_total = clause_data.get('per_unit', 0)  # 금액형은 per_unit과 동일
                
                new_clause = InsuranceClause(
                    product_id=product.id,
                    clause_code=f"CL_{len(saved_clauses) + 1:03d}",
                    clause_name=clause_data.get('clause_name', ''),
                    category=clause_data.get('category', ''),
                    per_unit=clause_data.get('per_unit', 0),
                    max_total=max_total,
                    unit_type=clause_data.get('unit_type', 'amount'),
                    conditions=clause_data.get('condition', ''),
                    description=f"PDF에서 추출된 특약: {clause_data.get('clause_name', '')}"
                )
                db.add(new_clause)
                saved_clauses.append(new_clause)
                
        except Exception as e:
            print(f"특약 저장 중 오류: {e}")
            continue
    
    db.commit()
    return saved_clauses

@router.get("/insurance-clauses", summary="보험 조항 목록 조회", description="PDF에서 추출된 보험 특약(조항) 목록을 조회합니다. skip과 limit 파라미터로 페이징 기능을 지원합니다.")
async def get_insurance_clauses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    PDF에서 추출된 보험 특약(조항) 목록을 조회합니다.
    
    - **skip**: 건너뛸 항목 수 (기본값: 0)
    - **limit**: 조회할 최대 항목 수 (기본값: 100)
    - 페이징 기능을 지원하여 대량 데이터 효율적 조회
    - 모든 보험사의 특약 정보 포함
    """
    clauses = db.query(InsuranceClause).offset(skip).limit(limit).all()
    return clauses 