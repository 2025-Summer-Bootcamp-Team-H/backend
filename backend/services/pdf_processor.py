#!/usr/bin/env python3
"""
보험약관 PDF 추출 → 정제 → 구조 개선까지 한 번에 처리하는 통합 스크립트
"""
import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import fitz  # PyMuPDF
import openai
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal
from models.models import InsuranceCompany, InsuranceProduct, InsuranceClause
# 환경변수 로드
load_dotenv()

def extract_company_and_product(filename: str):
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def get_or_create_company(db, company_name):
    company = db.query(InsuranceCompany).filter(
        (InsuranceCompany.name == company_name) | (InsuranceCompany.code == company_name)
    ).first()
    if not company:
        try:
            company = InsuranceCompany(name=company_name, code=company_name.upper())
            db.add(company)
            db.commit()
            db.refresh(company)
        except Exception as e:
            db.rollback()
            # 다시 조회 시도
            company = db.query(InsuranceCompany).filter(
                (InsuranceCompany.name == company_name) | (InsuranceCompany.code == company_name)
            ).first()
            if not company:
                raise e
    return company.id

def get_or_create_product(db, product_name, company_id):
    product = db.query(InsuranceProduct).filter_by(
        name=product_name, company_id=company_id
    ).first()
    if not product:
        product = InsuranceProduct(
            name=product_name,
            product_code=product_name.upper().replace(' ', '_'),
            company_id=company_id,
            description=f"PDF에서 추출된 상품: {product_name}"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
    return product.id

class PolicyProcessor:
    def __init__(self):
        self.input_dir = Path("input_pdfs")
        self.output_dir = Path("output_results")
        self.output_dir.mkdir(exist_ok=True)
        self.client = openai.OpenAI()  # .env의 OPENAI_API_KEY 자동 사용

    def extract_from_pdf(self, pdf_path: Path, chunk_size: int = 1) -> List[Dict]:
        print(f"📄 PDF 처리 시작: {pdf_path.name}")
        text_chunks = self._extract_text_chunks(pdf_path, chunk_size)
        all_rules = []
        success_count = 0
        error_count = 0
        
        for idx, (chunk, page_num) in enumerate(text_chunks):
            print(f"🔍 {idx+1}/{len(text_chunks)}번째 페이지 분석 중... (페이지 {page_num})")
            ai_response = self._ask_gpt_for_policy_rules(chunk, page_num)
            try:
                rules = self._parse_ai_response(ai_response, chunk, page_num)
                if rules:
                    all_rules.extend(rules)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"❌ {idx+1}번째 페이지 파싱 오류: {e}")
                error_count += 1
        
        print(f"✅ PDF 추출 완료: {len(all_rules)}개 항목 (성공: {success_count}페이지, 실패: {error_count}페이지)")
        return all_rules

    def _extract_text_chunks(self, pdf_path: Path, chunk_size: int) -> List[tuple]:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        chunks = []
        
        # 특약 관련 키워드 (한 페이지에 이 중 하나라도 있으면 분석)
        policy_keywords = [
            '특약', '보장', '입원', '수술', '진단', '장해', '사망', '통원', '외래',
            '보험금', '지급', '한도', '금액', '만원', '원', '일당', '회당',
            '암', '상해', '질병', '재해', '화상', '골절', '이식'
        ]
        
        # 금액 관련 키워드 (이것들이 있으면 더 우선적으로 분석)
        monetary_keywords = [
            '만원', '천원', '원', '일당', '회당', '한도', '최대', '금액',
            '보험금', '지급금', '보상', '급여', '비용'
        ]
        
        # 처리할 페이지 수 증가 (더 많은 정보 추출)
        max_pages = min(50, total_pages)  # 최대 50페이지만 처리
        
        for i in range(max_pages):
            text = doc[i].get_text()
            
            # 텍스트가 너무 적으면 건너뛰기 (20자 미만으로 더 완화)
            if len(text.strip()) < 20:
                continue
                
            # 특약 관련 키워드가 하나라도 있는지 확인
            has_policy_content = any(keyword in text for keyword in policy_keywords)
            has_monetary_content = any(keyword in text for keyword in monetary_keywords)
            
            # 금액 정보가 있으면 우선적으로 포함
            if has_monetary_content:
                chunks.append((text, i+1))
                continue
                
            # 특약 관련 키워드가 있으면 포함
            if has_policy_content:
                chunks.append((text, i+1))
                continue
                
        doc.close()
        print(f"  📄 분석 대상 페이지: {len(chunks)}/{max_pages}페이지 (전체 {total_pages}페이지 중)")
        return chunks

    def _ask_gpt_for_policy_rules(self, text: str, page_num: int) -> str:
        prompt = f"""
아래는 보험 약관 PDF의 한 페이지(페이지 번호: {page_num})입니다. 
**진단서 기반 보험금 산정에 필요한 특약을 추출하세요.**

**중요: 반드시 금액 정보를 포함해서 추출해주세요!**

**금액 추출이 최우선입니다 - 다음 패턴을 찾으세요:**
- "입원 1일당 5만원" → 단위금액: 50000
- "최대 100만원" → 최대한도: 1000000
- "진료비의 80%" → 단위금액: 80
- "일당 3만원" → 단위금액: 30000
- "1회당 50만원" → 단위금액: 500000
- "연간 한도 1000만원" → 최대한도: 10000000
- "보험가입금액의 2%" → 단위금액: 2
- "5000만원을 한도로" → 최대한도: 50000000
- "200만원 초과 시" → 최대한도: 2000000
- "방문 180회 한도" → 최대한도: 180
- "90회 한도" → 최대한도: 90
- "암 진단 시 100만원" → 단위금액: 1000000
- "수술비 500만원" → 단위금액: 5000000
- "입원일당 3만원" → 단위금액: 30000
- "통원 1회당 2만원" → 단위금액: 20000

**추출 대상 (우선순위):**
1. 진단명/병명별 보험금 (가장 중요)
2. 입원일수별 보험금
3. 통원/외래진료별 보험금
4. 수술별 보험금
5. 검사별 보험금
6. 치료별 보험금

**금액 추출 규칙:**
- "만원" = ×10000
- "천원" = ×1000
- "원" = 그대로
- "%" = 그대로
- "회" = 그대로 (횟수)
- "일" = 그대로 (일수)
- 금액이 없으면 null로 표시

**중요: 진단서에서 실제로 확인할 수 있는 정보로 보험금을 산출할 수 있는 특약을 찾으세요!**

**추출 시 주의사항:**
1. 금액 정보가 명확하지 않으면 원문에 포함된 모든 숫자를 기록
2. "보험가입금액의 X%" 형태는 단위금액에 X 입력
3. "최대", "한도", "초과" 등의 키워드가 있으면 최대한도로 분류
4. "1일당", "1회당" 등의 키워드가 있으면 단위금액으로 분류
5. **금액이 명확하지 않으면 추정값을 사용하세요!**
6. **암 관련 특약은 보통 100만원 이상입니다**
7. **입원 특약은 보통 1일당 3-5만원입니다**
8. **수술 특약은 보통 50-500만원입니다**

**추정 규칙:**
- 암진단특약: 단위금액 1000000, 최대한도 1000000
- 암직접치료입원특약: 단위금액 50000, 최대한도 1500000
- 암직접치료수술특약: 단위금액 500000, 최대한도 5000000
- 특정법정감염병진단특약: 단위금액 500000, 최대한도 1000000
- 입원특약: 단위금액 30000, 최대한도 900000

예시:
[
  {{
    "특약명": "질병입원담보",
    "보장항목": "입원의료비",
    "단위금액": 50000,
    "최대한도": 500000,
    "조건/예외": "입원일수에 따라 1일당 5만원 지급",
    "원문": "입원 1일당 5만원, 최대 20일",
    "페이지": 3
  }},
  {{
    "특약명": "질병통원담보", 
    "보장항목": "외래진료",
    "단위금액": null,
    "최대한도": 200000,
    "조건/예외": "통원진료 횟수에 따라 방문 1회당 지급",
    "원문": "방문 1회당, 180회 한도",
    "페이지": 3
  }},
  {{
    "특약명": "암진단특약",
    "보장항목": "진단",
    "단위금액": 1000000,
    "최대한도": 1000000,
    "조건/예외": "암 진단 시 1회 지급",
    "원문": "암 진단 시 100만원 지급",
    "페이지": 3
  }}
]

아래 텍스트에서 **진단서 기반 보험금 산정에 필요한 특약을** 추출해주세요.

약관 텍스트:
{text}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "보험 약관에서 진단서 기반 보험금 산정에 필요한 특약을 추출하는 전문가입니다. 진단명, 입원일수, 통원횟수 등으로 보험금을 산출할 수 있는 조항을 찾습니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=8000,
                timeout=90
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ⚠️ 페이지 {page_num} AI 요청 실패: {e}")
            return "[]"  # 빈 배열 반환

    def _parse_ai_response(self, ai_response: str, source_text: str, page_number: int) -> List[Dict]:
        try:
            # AI 응답에서 JSON 배열 찾기
            start = ai_response.find('[')
            end = ai_response.rfind(']') + 1
            
            if start == -1 or end == 0:
                print(f"  ⚠️ 페이지 {page_number}: JSON 배열을 찾을 수 없음")
                return []
                
            json_str = ai_response[start:end]
            
            # JSON 파싱 시도
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"  ⚠️ 페이지 {page_number}: JSON 파싱 실패 - {e}")
                # 빈 배열 반환
                return []
            
            # 각 항목에 원문/페이지 정보가 없으면 추가
            for item in data:
                if '원문' not in item or not item['원문']:
                    item['원문'] = source_text[:200]  # 앞부분만 저장
                if '페이지' not in item or not item['페이지']:
                    item['페이지'] = page_number
            return data
            
        except Exception as e:
            print(f"❌ AI 응답 파싱 오류: {e}")
            return []

    def clean_data(self, raw_data: List[Dict]) -> List[Dict]:
        print(f"🧹 데이터 정제 시작: {len(raw_data)}개 항목")
        cleaned_data = []
        for item in raw_data:
            cleaned_item = self._clean_single_item(item)
            if cleaned_item:
                cleaned_data.append(cleaned_item)
        print(f"🔧 1단계 정제 후: {len(cleaned_data)}개 항목")
        
        # 중복 제거 추가
        unique_data = self._remove_duplicates(cleaned_data)
        print(f"🔄 2단계 중복제거 후: {len(unique_data)}개 항목")
        
        return unique_data

    def _clean_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        clause_name = item.get('특약명', '')
        category = item.get('보장항목', '')
        per_unit = item.get('단위금액', '미상')
        max_total = item.get('최대한도', '미상')
        condition = item.get('조건/예외', '미상')
        source_text = item.get('원문', '')
        page_number = item.get('페이지', '')
        
        # AI가 추출한 금액이 null이면 원문에서 금액 추출 시도
        if per_unit is None or per_unit == '미상' or per_unit == '':
            extracted_per_unit, extracted_max_total = self._extract_monetary_from_text(source_text)
            if extracted_per_unit is not None:
                per_unit = extracted_per_unit
                print(f"  💰 원문에서 금액 추출: {clause_name} - {per_unit:,}원")
        
        if max_total is None or max_total == '미상' or max_total == '':
            if 'extracted_max_total' not in locals():
                _, extracted_max_total = self._extract_monetary_from_text(source_text)
            if extracted_max_total is not None:
                max_total = extracted_max_total
                print(f"  💰 원문에서 최대한도 추출: {clause_name} - {max_total:,}원")
        
        return {
            'clause_name': clause_name,
            'category': category,
            'per_unit': per_unit,
            'max_total': max_total,
            'condition': condition,
            'source_text': source_text,
            'page_number': page_number
        }
    
    def _extract_monetary_value(self, value) -> Any:
        """금액 값을 추출하고 숫자로 변환"""
        if value is None:
            return None
        
        # 이미 숫자인 경우
        if isinstance(value, (int, float)):
            return value
        
        # 문자열인 경우 금액 추출
        if isinstance(value, str):
            value = value.strip()
            
            # "미상" 체크
            if value == '미상' or value == '':
                return None
            
            # 숫자 + 단위 패턴 찾기
            import re
            
            # "만원" 패턴 (예: "5만원", "100만원")
            man_won_match = re.search(r'(\d+(?:\.\d+)?)\s*만원', value)
            if man_won_match:
                return int(float(man_won_match.group(1)) * 10000)
            
            # "천원" 패턴 (예: "5천원", "100천원")
            cheon_won_match = re.search(r'(\d+(?:\.\d+)?)\s*천원', value)
            if cheon_won_match:
                return int(float(cheon_won_match.group(1)) * 1000)
            
            # "원" 패턴 (예: "50000원")
            won_match = re.search(r'(\d+(?:,\d+)*)\s*원', value)
            if won_match:
                return int(won_match.group(1).replace(',', ''))
            
            # 퍼센트 패턴 (예: "80%", "90%")
            percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', value)
            if percent_match:
                return float(percent_match.group(1))
            
            # 순수 숫자만 있는 경우
            number_match = re.search(r'^(\d+(?:\.\d+)?)$', value)
            if number_match:
                num = float(number_match.group(1))
                # 1-100 범위면 퍼센트로 간주
                if 1 <= num <= 100:
                    return num
                # 그 이상이면 금액으로 간주
                return int(num)
            
            # 분수 패턴 (예: "100분의 80", "40/100")
            fraction_match = re.search(r'(\d+)\s*분의\s*(\d+)', value)
            if fraction_match:
                numerator = int(fraction_match.group(2))
                denominator = int(fraction_match.group(1))
                return round((numerator / denominator) * 100, 1)
            
            # 슬래시 분수 패턴 (예: "80/100")
            slash_fraction_match = re.search(r'(\d+)\s*/\s*(\d+)', value)
            if slash_fraction_match:
                numerator = int(slash_fraction_match.group(1))
                denominator = int(slash_fraction_match.group(2))
                return round((numerator / denominator) * 100, 1)
        
        return value

    def _extract_monetary_from_text(self, text: str) -> tuple:
        """텍스트에서 금액 정보를 추출하는 강화된 함수"""
        if not text:
            return None, None
        
        import re
        
        # 금액 패턴들
        patterns = [
            # "100만원" → 1000000
            (r'(\d+(?:\.\d+)?)\s*만원', lambda m: int(float(m.group(1)) * 10000)),
            # "5천원" → 5000
            (r'(\d+(?:\.\d+)?)\s*천원', lambda m: int(float(m.group(1)) * 1000)),
            # "50000원" → 50000
            (r'(\d+(?:,\d+)*)\s*원', lambda m: int(m.group(1).replace(',', ''))),
            # "80%" → 80
            (r'(\d+(?:\.\d+)?)\s*%', lambda m: float(m.group(1))),
            # 순수 숫자 (큰 숫자는 금액, 작은 숫자는 퍼센트)
            (r'\b(\d{4,})\b', lambda m: int(m.group(1))),  # 4자리 이상은 금액
            (r'\b(\d{1,3})\b', lambda m: float(m.group(1)) if 1 <= float(m.group(1)) <= 100 else None),  # 1-3자리는 퍼센트 가능성
        ]
        
        per_unit = None
        max_total = None
        
        # 텍스트에서 모든 금액 패턴 찾기
        found_amounts = []
        for pattern, converter in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    amount = converter(match)
                    if amount is not None:
                        found_amounts.append(amount)
                except:
                    continue
        
        # 금액이 2개 이상 있으면 첫 번째는 per_unit, 두 번째는 max_total
        if len(found_amounts) >= 2:
            per_unit = found_amounts[0]
            max_total = found_amounts[1]
        elif len(found_amounts) == 1:
            per_unit = found_amounts[0]
        
        return per_unit, max_total

    def _remove_duplicates(self, data: List[Dict]) -> List[Dict]:
        """중복 제거"""
        print("🔄 중복 제거 시작...")
        seen = set()
        unique_data = []
        
        for item in data:
            # clause_name이 None인 경우 처리
            clause_name = item.get('clause_name', '')
            if clause_name is None:
                clause_name = ''
            else:
                clause_name = clause_name.strip()
                
            # category가 None인 경우 처리
            category = item.get('category', '')
            if category is None:
                category = ''
            else:
                category = category.strip()
            
            # 중복 체크 키 생성
            key = f"{clause_name}_{category}"
            
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        print(f"✅ 중복 제거 완료: {len(unique_data)}개")
        return unique_data

    def _filter_practical_clauses(self, data: List[Dict]) -> List[Dict]:
        """실용적인 특약만 필터링 - 임시로 모든 조항 포함"""
        print("🔍 필터링 비활성화 - 모든 조항 포함...")
        
        # 임시로 모든 조항을 포함 (필터링 비활성화)
        practical_clauses = []
        for item in data:
            clause_name = item.get('clause_name', '')
            category = item.get('category', '')
            
            # 기본 필터링만: 특약명과 카테고리가 있어야 함
            if clause_name and category:
                practical_clauses.append(item)
        
        print(f"✅ 필터링 완료: {len(practical_clauses)}개 (모든 조항 포함)")
        return practical_clauses

    def _add_dummy_data_info(self, data: List[Dict]) -> List[Dict]:
        for i, item in enumerate(data):
            item['id'] = i + 1
            
            # per_unit이 None이거나 문자열인 경우 기본값 설정
            if item['per_unit'] is None or not isinstance(item['per_unit'], (int, float)):
                default_amounts = {
                    '입원': 50000, '수술': 500000, '진단': 1000000,
                    '장해': 1000000, '사망': 5000000, '상해': 300000,
                    '질병': 200000, '통원': 20000
                }
                item['per_unit'] = default_amounts.get(item['category'], 100000)
            
            # max_total이 None이거나 문자열인 경우 기본값 설정
            if item['max_total'] is None or not isinstance(item['max_total'], (int, float)):
                if isinstance(item['per_unit'], (int, float)):
                    item['max_total'] = item['per_unit'] * 10
                else:
                    item['max_total'] = 1000000  # 기본값 100만원
            
            item['insurance_company'] = '삼성생명'
            item['policy_type'] = '종신보험'
            item['is_active'] = True
        return data

    # 구조 개선 (per_unit, max_total → 실제 보험금 산출에 맞게)
    def fix_data_structure(self, data: List[Dict]) -> List[Dict]:
        print("🔧 데이터 구조 개선 시작...")
        fixed_data = []
        for item in data:
            fixed_item = self._fix_single_item(item)
            if fixed_item:
                fixed_data.append(fixed_item)
        return fixed_data

    def _fix_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        category = item.get('category', '')
        clause_name = item.get('clause_name', '')
        per_unit = item.get('per_unit')
        
        # unit_type 자동 판별: 두 자리수 이하는 퍼센트, 그 이상은 금액
        unit_type = self._determine_unit_type(per_unit, category)
        
        # per_unit이 숫자인지 확인
        is_numeric_per_unit = isinstance(per_unit, (int, float)) and per_unit is not None
        
        # 간단한 ID 생성 (cl_001, cl_002...)
        # 특약명 + 카테고리 기반으로 일관된 ID 생성
        clause_name_lower = clause_name.lower()
        category_lower = category.lower()
        
        # 주요 특약들은 고정 ID 할당
        if '암진단' in clause_name_lower:
            simple_id = "cl_001"
        elif '암직접치료입원' in clause_name_lower:
            simple_id = "cl_002"
        elif '암직접치료수술' in clause_name_lower:
            simple_id = "cl_003"
        elif '특정법정감염병' in clause_name_lower:
            simple_id = "cl_004"
        elif '질병입원' in clause_name_lower:
            simple_id = "cl_005"
        elif '질병통원' in clause_name_lower:
            simple_id = "cl_006"
        elif '상해입원' in clause_name_lower:
            simple_id = "cl_007"
        elif '상해통원' in clause_name_lower:
            simple_id = "cl_008"
        elif '통원치료' in clause_name_lower:
            simple_id = "cl_009"
        elif '처방조제' in clause_name_lower:
            simple_id = "cl_010"
        elif '특별조건' in clause_name_lower:
            simple_id = "cl_011"
        else:
            # 기본 ID (특약명 + 카테고리 기반)
            combined_key = f"{clause_name}_{category}"
            simple_id = f"cl_{hash(combined_key) % 1000:03d}"
        
        # 추정값 적용 (per_unit이 None이거나 0인 경우)
        if per_unit is None or per_unit == 0:
            clause_name_lower = clause_name.lower()
            if '암진단' in clause_name_lower:
                per_unit = 1000000
                max_total = 1000000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '암직접치료입원' in clause_name_lower:
                per_unit = 50000
                max_total = 1500000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '암직접치료수술' in clause_name_lower:
                per_unit = 500000
                max_total = 5000000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '특정법정감염병' in clause_name_lower:
                per_unit = 500000
                max_total = 1000000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '입원' in clause_name_lower and '암' not in clause_name_lower:
                per_unit = 30000
                max_total = 900000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '수술' in clause_name_lower and '암' not in clause_name_lower:
                per_unit = 200000
                max_total = 2000000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '진단' in clause_name_lower and '암' not in clause_name_lower:
                per_unit = 300000
                max_total = 300000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            elif '통원' in clause_name_lower or '외래' in clause_name_lower:
                per_unit = 20000
                max_total = 600000
                print(f"  💰 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
            else:
                # 기본 추정값
                per_unit = 100000
                max_total = 1000000
                print(f"  💰 기본 추정값 적용: {clause_name} - 단위금액: {per_unit:,}원")
        
        # 퍼센트형 특약 처리 (80%, 90% 등)
        if is_numeric_per_unit and 1 <= per_unit <= 100 and ('%' in str(item.get('condition', '')) or '보상' in str(item.get('condition', ''))):
            max_total = self._calculate_realistic_max_total(per_unit, category, 'percentage')
            return {
                'id': simple_id,
                'clause_name': item.get('clause_name'),
                'category': item.get('category'),
                'unit_type': 'percentage',
                'per_unit': per_unit,
                'max_total': max_total,
                'condition': item.get('condition'),
                'insurance_company': item.get('insurance_company'),
                'policy_type': item.get('policy_type'),
                'is_active': item.get('is_active')
            }
        
        # 입원/통원: per_unit(1일/1회당 금액), max_total(최대 지급금)
        if category in ['입원', '통원']:
            # 비현실적으로 큰 per_unit은 제외 (숫자인 경우에만)
            if is_numeric_per_unit and per_unit > 1000000:  # 100만원 초과면 제외
                print(f"  🚫 비현실적 입원/통원 per_unit 제외: {clause_name} - {per_unit:,}원")
                return None
                
            # 정규화된 max_total 사용 (이미 _validate_and_normalize_data에서 처리됨)
            max_total = item.get('max_total')
            return {
                'id': simple_id,
                'clause_name': item.get('clause_name'),
                'category': item.get('category'),
                'unit_type': 'amount',
                'per_unit': per_unit,
                'max_total': max_total,
                'condition': item.get('condition'),
                'insurance_company': item.get('insurance_company'),
                'policy_type': item.get('policy_type'),
                'is_active': item.get('is_active')
            }
        # 장해(퍼센트형): per_unit(지급률), max_total=None
        elif category == '장해' and unit_type == 'percentage':
            return {
                'id': simple_id,
                'clause_name': item.get('clause_name'),
                'category': item.get('category'),
                'unit_type': 'percentage',
                'per_unit': per_unit,
                'max_total': None,
                'condition': item.get('condition'),
                'insurance_company': item.get('insurance_company'),
                'policy_type': item.get('policy_type'),
                'is_active': item.get('is_active')
            }
        # 수술/진단/사망/상해/장해(고정금액): per_unit과 max_total을 다르게 설정
        elif category in ['수술', '진단', '사망', '상해'] or (category == '장해' and unit_type == 'amount'):
            # max_total을 per_unit의 1-3배로 설정 (보험 특성상)
            max_total = self._calculate_realistic_max_total(per_unit, category, unit_type)
            return {
                'id': simple_id,
                'clause_name': item.get('clause_name'),
                'category': item.get('category'),
                'unit_type': 'amount',
                'per_unit': per_unit,
                'max_total': max_total,
                'condition': item.get('condition'),
                'insurance_company': item.get('insurance_company'),
                'policy_type': item.get('policy_type'),
                'is_active': item.get('is_active')
            }
        else:
            # 기본값으로 unit_type 추가
            return {
                'id': simple_id,
                'clause_name': item.get('clause_name'),
                'category': item.get('category'),
                'unit_type': 'amount',  # 기본값
                'per_unit': item.get('per_unit'),
                'max_total': item.get('max_total'),
                'condition': item.get('condition'),
                'insurance_company': item.get('insurance_company'),
                'policy_type': item.get('policy_type'),
                'is_active': item.get('is_active')
            }

    def _determine_unit_type(self, per_unit, category: str) -> str:
        """per_unit 값을 기반으로 unit_type을 자동 판별"""
        if per_unit is None:
            return 'amount'
        
        # per_unit이 문자열이면 기본값 반환
        if not isinstance(per_unit, (int, float)):
            return 'amount'
        
        # 퍼센트형 판별 (1-100 범위)
        if 1 <= per_unit <= 100:
            return 'percentage'
        
        # 장해 카테고리는 기본적으로 퍼센트형
        if category == '장해' and per_unit <= 100:
            return 'percentage'
        
        # 다른 카테고리들은 기본적으로 금액형
        return 'amount'

    def _calculate_realistic_max_total(self, per_unit: int, category: str, unit_type: str = 'amount') -> int:
        """카테고리별로 현실적인 max_total 계산"""
        if per_unit is None or not isinstance(per_unit, (int, float)):
            return None
            
        # 퍼센트형인 경우 특별 처리
        if unit_type == 'percentage':
            # 퍼센트형은 보통 진료비 대비이므로 현실적인 한도 설정
            if category == '입원':
                return 20000000  # 2000만원 (입원비 대비 80% 등)
            elif category == '통원':
                return 10000000  # 1000만원 (통원비 대비)
            else:
                return 50000000  # 5000만원 (일반적인 진료비 대비)
        
        # 금액형 처리
        # 카테고리별 배수 설정
        multipliers = {
            '수술': 2,      # 수술은 1-2회 정도
            '진단': 3,      # 진단은 여러 번 가능
            '사망': 1,      # 사망은 1회
            '상해': 2,      # 상해는 1-2회 정도
            '장해': 1,      # 장해는 1회
            '입원': 5,      # 입원은 1-5회 정도
            '통원': 12,     # 통원은 월 1회 정도
        }
        
        multiplier = multipliers.get(category, 2)  # 기본값 2
        
        # per_unit이 너무 작으면 보정
        if per_unit < 10000:  # 1만원 미만
            per_unit = per_unit * 1000  # 1000배 증가 (500원 → 50만원)
        
        # 입원 특약은 특별 처리 (일당형)
        if category == '입원':
            max_total = per_unit * 30  # 최대 30일치
        else:
            max_total = per_unit * multiplier
        
        # 카테고리별 최소/최대 한도 설정
        min_limits = {
            '수술': 500000,    # 최소 50만원
            '진단': 1000000,   # 최소 100만원
            '사망': 5000000,   # 최소 500만원
            '상해': 300000,    # 최소 30만원
            '장해': 1000000,   # 최소 100만원
            '입원': 1000000,   # 최소 100만원
            '통원': 500000,    # 최소 50만원
        }
        
        max_limits = {
            '수술': 50000000,   # 최대 5000만원
            '진단': 100000000,  # 최대 1억원
            '사망': 500000000,  # 최대 5억원
            '상해': 20000000,   # 최대 2000만원
            '장해': 100000000,  # 최대 1억원
            '입원': 50000000,   # 최대 5000만원
            '통원': 10000000,   # 최대 1000만원
        }
        
        # 최소/최대 한도 적용
        if category in min_limits:
            max_total = max(max_total, min_limits[category])
        if category in max_limits:
            max_total = min(max_total, max_limits[category])
            
        return max_total

    def save_results(self, data: List[Dict], filename: str):
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 결과 저장: {output_path}")

    def print_summary(self, data: List[Dict]):
        print(f"\n📈 최종 데이터 요약:")
        print(f"총 특약 수: {len(data)}개")
        unit_types = {}
        categories = {}
        for item in data:
            unit_type = item['unit_type']
            category = item['category']
            unit_types[unit_type] = unit_types.get(unit_type, 0) + 1
            categories[category] = categories.get(category, 0) + 1
        print("\n단위 타입별 분포:")
        for unit_type, count in sorted(unit_types.items()):
            print(f"  {unit_type}: {count}개")
        print("\n카테고리별 분포:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}개")
        # 예시 출력
        print("\n📋 데이터 구조 예시:")
        hospitalization_example = next((item for item in data if item['unit_type'] == 'amount'), None)
        if hospitalization_example:
            print(f"\n입원 특약 (일당형):")
            print(f"  {hospitalization_example['clause_name']}: {hospitalization_example['per_unit']:,}원/일 (최대 {hospitalization_example['max_total']}일)")
        percentage_example = next((item for item in data if item['unit_type'] == 'percentage'), None)
        fixed_disability_example = next((item for item in data if item['category'] == '장해' and item['unit_type'] == 'amount'), None)
        if percentage_example:
            print(f"\n장해 특약 (퍼센트형):")
            print(f"  {percentage_example['clause_name']}: {percentage_example['per_unit']}% (보험금 대비)")
        if fixed_disability_example:
            print(f"\n장해 특약 (고정금액형):")
            print(f"  {fixed_disability_example['clause_name']}: {fixed_disability_example['per_unit']:,}원 (1회 지급)")
        surgery_example = next((item for item in data if item['category'] == '수술'), None)
        if surgery_example:
            print(f"\n수술 특약 (고정금액형):")
            print(f"  {surgery_example['clause_name']}: {surgery_example['per_unit']:,}원 (1회 지급)")

    def create_improved_database_schema(self):
        schema = """
-- 개선된 보험 특약 테이블 스키마
CREATE TABLE insurance_clauses (
    id INTEGER PRIMARY KEY,
    clause_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit_type VARCHAR(30) NOT NULL,  -- 'fixed_amount', 'amount_per_day', 'percentage_of_sum'
    per_unit INTEGER NOT NULL,       -- 보험금, 일당, 지급률
    max_total INTEGER,               -- 최대 보험금 (NULL 가능)
    max_days INTEGER,                -- 최대 일수 (입원의 경우)
    condition TEXT,
    insurance_company VARCHAR(50),
    policy_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_clause_category ON insurance_clauses(category);
CREATE INDEX idx_unit_type ON insurance_clauses(unit_type);
CREATE INDEX idx_insurance_company ON insurance_clauses(insurance_company);

-- 보험금 계산 함수 예시 (PostgreSQL)
CREATE OR REPLACE FUNCTION calculate_insurance_payment(
    clause_id INTEGER,
    base_amount INTEGER DEFAULT NULL,
    days INTEGER DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    clause_record RECORD;
    payment INTEGER;
BEGIN
    SELECT * INTO clause_record FROM insurance_clauses WHERE id = clause_id;
    IF NOT FOUND THEN RETURN 0; END IF;
    CASE clause_record.unit_type
        WHEN 'fixed_amount' THEN
            payment := clause_record.per_unit;
        WHEN 'amount_per_day' THEN
            IF days IS NULL THEN payment := 0;
            ELSE payment := LEAST(days, clause_record.max_days) * clause_record.per_unit;
            END IF;
        WHEN 'percentage_of_sum' THEN
            IF base_amount IS NULL THEN payment := 0;
            ELSE payment := (base_amount * clause_record.per_unit) / 100;
            END IF;
        ELSE payment := 0;
    END CASE;
    IF clause_record.max_total IS NOT NULL AND payment > clause_record.max_total THEN
        payment := clause_record.max_total;
    END IF;
    RETURN payment;
END;
$$ LANGUAGE plpgsql;
"""
        schema_path = Path("improved_database_schema.sql")
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(schema)
        print("💾 개선된 데이터베이스 스키마 생성: improved_database_schema.sql")

    def run_full_process(self):
        db = SessionLocal()
        print("🚀 보험약관 PDF 추출 및 처리 시작!")
        print("=" * 50)
        pdf_files = list(self.input_dir.glob('*.pdf'))
        if not pdf_files:
            print(f"❌ {self.input_dir} 폴더에 PDF 파일이 없습니다.")
            return
        print(f"📁 발견된 PDF 파일: {len(pdf_files)}개")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file.name}")
        for pdf_path in pdf_files:
            print(f"\n📄 처리 중: {pdf_path.name}")
            raw_data = self.extract_from_pdf(pdf_path)
            if not raw_data:
                print(f"⚠️ {pdf_path.name}에서 추출된 데이터가 없습니다.")
                continue
            cleaned_data = self.clean_data(raw_data)
            filtered_data = self._filter_practical_clauses(cleaned_data)
            validated_data = self._validate_and_normalize_data(filtered_data)
            final_data = self.fix_data_structure(validated_data)
            
            # 진단서/영수증 기반 보험금 산정을 위한 더미 특약 추가
            final_data = self.add_dummy_clauses_for_claim_calculation(final_data)
            # PDF 파일명에서 보험사명/상품명 추출
            company_name, product_name = extract_company_and_product(pdf_path.name)
            try:
                company_id = get_or_create_company(db, company_name)
                product_id = get_or_create_product(db, product_name, company_id)
            except Exception as e:
                print(f"❌ {pdf_path.name} - {e}")
                continue
            # DB에 특약 저장 (중복 방지)
            saved_count = 0
            skipped_count = 0
            for item in final_data:
                # 기존 특약 확인 (중복 방지)
                existing_clause = db.query(InsuranceClause).filter(
                    InsuranceClause.product_id == product_id,
                    InsuranceClause.clause_name == item['clause_name']
                ).first()
                
                if existing_clause:
                    print(f"  ⚠️ 특약 '{item['clause_name']}' 이미 존재 - 건너뜀")
                    skipped_count += 1
                    continue
                
                # DB 저장 전 타입 검증 및 변환
                per_unit = item['per_unit']
                max_total = item['max_total']
                
                # null 값이 있는 경우 기본값 적용
                if per_unit is None or not isinstance(per_unit, (int, float)):
                    # 추정값 적용
                    clause_name_lower = item['clause_name'].lower()
                    if '암진단' in clause_name_lower:
                        per_unit = 1000000
                    elif '암직접치료입원' in clause_name_lower:
                        per_unit = 50000
                    elif '암직접치료수술' in clause_name_lower:
                        per_unit = 500000
                    elif '특정법정감염병' in clause_name_lower:
                        per_unit = 500000
                    elif '입원' in clause_name_lower and '암' not in clause_name_lower:
                        per_unit = 30000
                    elif '수술' in clause_name_lower and '암' not in clause_name_lower:
                        per_unit = 200000
                    elif '진단' in clause_name_lower and '암' not in clause_name_lower:
                        per_unit = 300000
                    elif '통원' in clause_name_lower or '외래' in clause_name_lower:
                        per_unit = 20000
                    else:
                        per_unit = 100000
                    print(f"  💰 DB 저장 시 추정값 적용: {item['clause_name']} - {per_unit:,}원")
                
                # max_total이 null인 경우 (장해 퍼센트형 제외)
                if max_total is None or not isinstance(max_total, (int, float)):
                    # 장해 퍼센트형은 max_total이 null일 수 있음
                    if item['category'] == '장해' and isinstance(per_unit, (int, float)) and 1 <= per_unit <= 100:
                        max_total = None  # 장해 퍼센트형은 max_total을 null로 저장
                    else:
                        # 추정값 적용
                        clause_name_lower = item['clause_name'].lower()
                        if '암진단' in clause_name_lower:
                            max_total = 1000000
                        elif '암직접치료입원' in clause_name_lower:
                            max_total = 1500000
                        elif '암직접치료수술' in clause_name_lower:
                            max_total = 5000000
                        elif '특정법정감염병' in clause_name_lower:
                            max_total = 1000000
                        elif '입원' in clause_name_lower and '암' not in clause_name_lower:
                            max_total = 900000
                        elif '수술' in clause_name_lower and '암' not in clause_name_lower:
                            max_total = 2000000
                        elif '진단' in clause_name_lower and '암' not in clause_name_lower:
                            max_total = 300000
                        elif '통원' in clause_name_lower or '외래' in clause_name_lower:
                            max_total = 600000
                        else:
                            max_total = 1000000
                        print(f"  💰 DB 저장 시 최대한도 추정값 적용: {item['clause_name']} - {max_total:,}원")
                
                clause = InsuranceClause(
                    product_id=product_id,
                    clause_code=f"CL_{saved_count+1:03d}",
                    clause_name=item['clause_name'],
                    category=item['category'],
                    per_unit=per_unit,
                    max_total=max_total,
                    unit_type=item['unit_type'],
                    description=item.get('description', ''),
                    conditions=item.get('condition', ''),
                )
                db.add(clause)
                saved_count += 1
                print(f"  ✅ 특약 저장: {item['clause_name']}")
            
            db.commit()
            print(f"✅ {pdf_path.name} - 새로 저장: {saved_count}건, 건너뜀: {skipped_count}건")
            
            # 결과를 JSON 파일로 저장
            output_filename = f"{pdf_path.stem}_extracted_clauses.json"
            self.save_results(final_data, output_filename)
        db.close()
        print("✅ 전체 PDF 처리 및 DB 저장 완료!")
        
        # 최종 요약 정보 출력
        self.print_final_summary()

    def print_final_summary(self):
        """최종 DB 상태 요약 출력"""
        db = SessionLocal()
        try:
            print("\n" + "="*60)
            print("📊 최종 DB 상태 요약")
            print("="*60)
            
            # 보험사별 통계
            companies = db.query(InsuranceCompany).all()
            print(f"\n🏢 보험사: {len(companies)}개")
            for company in companies:
                products = db.query(InsuranceProduct).filter(InsuranceProduct.company_id == company.id).all()
                total_clauses = 0
                for product in products:
                    clauses = db.query(InsuranceClause).filter(InsuranceClause.product_id == product.id).all()
                    total_clauses += len(clauses)
                    print(f"  📋 {company.name} - {product.name}: {len(clauses)}개 특약")
                print(f"    총 특약: {total_clauses}개")
            
            # 전체 통계
            total_companies = db.query(InsuranceCompany).count()
            total_products = db.query(InsuranceProduct).count()
            total_clauses = db.query(InsuranceClause).count()
            
            print(f"\n📈 전체 통계:")
            print(f"  - 보험사: {total_companies}개")
            print(f"  - 상품: {total_products}개")
            print(f"  - 특약: {total_clauses}개")
            
            # 카테고리별 분포
            print(f"\n🏷️ 카테고리별 특약 분포:")
            from sqlalchemy import func
            categories = db.query(InsuranceClause.category, func.count(InsuranceClause.id)).group_by(InsuranceClause.category).all()
            for category, count in categories:
                print(f"  - {category}: {count}개")
            
            # 단위 타입별 분포
            print(f"\n💰 단위 타입별 분포:")
            unit_types = db.query(InsuranceClause.unit_type, func.count(InsuranceClause.id)).group_by(InsuranceClause.unit_type).all()
            for unit_type, count in unit_types:
                print(f"  - {unit_type}: {count}개")
                
        except Exception as e:
            print(f"❌ 요약 정보 출력 중 오류: {e}")
        finally:
            db.close()

    def _validate_and_normalize_data(self, data: List[Dict]) -> List[Dict]:
        """실무에서 안전하게 사용할 수 있도록 데이터 검증 및 정규화"""
        print("🔒 데이터 검증 및 정규화 시작...")
        validated_data = []
        
        for item in data:
            validated_item = self._validate_single_item(item)
            if validated_item:
                validated_data.append(validated_item)
        
        print(f"✅ 검증 완료: {len(validated_data)}개 조항")
        return validated_data
    
    def _validate_single_item(self, item: Dict) -> Dict:
        """개별 조항 검증 및 정규화"""
        clause_name = item.get('clause_name', '')
        category = item.get('category', '')
        per_unit = item.get('per_unit')
        max_total = item.get('max_total')
        unit_type = item.get('unit_type', 'amount')
        
        # 1. 기본 유효성 검사
        if not clause_name or not category:
            return None
            
        # 2. '미상' 값 처리
        if per_unit == '미상':
            per_unit = None
        if max_total == '미상':
            max_total = None
            
        # 3. 퍼센트형 조항 검증
        if unit_type == 'percentage':
            if not per_unit or (isinstance(per_unit, (int, float)) and (per_unit < 1 or per_unit > 100)):
                print(f"  ⚠️ 퍼센트형 조항 수정: {clause_name} - {per_unit}% → 80%")
                per_unit = 80
            max_total = None  # 퍼센트형은 max_total 없음
            
        # 4. 금액형 조항 검증 및 정규화
        else:
            # per_unit이 숫자인 경우에만 정규화
            if isinstance(per_unit, (int, float)):
                # 최소 금액 정규화 (카테고리별 현실적인 최소값 적용)
                if per_unit < 10000:
                    per_unit = self._apply_realistic_per_unit(category, 10000)
                else:
                    per_unit = self._apply_realistic_per_unit(category, per_unit)
                    
                # 최대 금액 제한 (1억원 초과는 1억원으로 제한)
                if per_unit > 100000000:
                    print(f"  ⚠️ 최대 금액 제한: {clause_name} - {per_unit:,}원 → 100,000,000원")
                    per_unit = 100000000
                    
                # max_total 정규화 (실제 보험 한도 적용)
                if isinstance(max_total, (int, float)):
                    max_total = self._normalize_max_total(category, per_unit, max_total)
            else:
                # per_unit이 숫자가 아니면 그대로 유지 (사람이 검수할 수 있도록)
                pass
        
        return {
            'id': item.get('id'),
            'clause_name': clause_name,
            'category': category,
            'unit_type': unit_type,
            'per_unit': per_unit,
            'max_total': max_total,
            'condition': item.get('condition', ''),
            'source_text': item.get('source_text', ''),
            'page_number': item.get('page_number', ''),
            'insurance_company': item.get('insurance_company', '삼성생명'),
            'policy_type': item.get('policy_type', '종신보험'),
            'is_active': True
        }
    
    def _normalize_max_total(self, category: str, per_unit: int, original_max: int) -> int:
        """실제 보험 한도에 맞게 max_total 정규화"""
        # original_max가 None이거나 숫자가 아니면 None 반환
        if original_max is None or not isinstance(original_max, (int, float)):
            return None
            
        # 실제 보험 한도 (실무 기준)
        limits = {
            '통원': 180,  # 연간 180회
            '입원': 120,  # 연간 120일
            '수술': 10,   # 연간 10회
            '진단': 5,    # 연간 5회
            '장해': 1,    # 1회성
            '사망': 1,    # 1회성
            '상해': 10,   # 연간 10회
            '질병': 5,    # 연간 5회
        }
        
        # 작은 값들을 만원 단위로 해석 (800 → 800만원)
        if original_max < 10000:
            print(f"    💰 작은 값 만원 단위 해석: {original_max} → {original_max * 10000:,}원")
            original_max = original_max * 10000
        
        # 카테고리별 한도 적용
        if category in limits:
            realistic_max = per_unit * limits[category]
            
            # 원래 max_total이 비현실적으로 크면 무조건 현실적 한도 적용
            if original_max > 1000000000:  # 10억원 초과
                print(f"    🚫 비현실적 max_total 정규화: {original_max:,}원 → {realistic_max:,}원")
                return realistic_max
            elif original_max < realistic_max:
                return original_max
            else:
                print(f"    📊 {category} 한도 적용: {per_unit:,}원 × {limits[category]}회 = {realistic_max:,}원")
                return realistic_max
        
        # 기타 카테고리는 per_unit의 10배로 설정
        default_max = per_unit * 10
        if original_max > 1000000000:  # 10억원 초과
            print(f"    🚫 비현실적 max_total 정규화: {original_max:,}원 → {default_max:,}원")
            return default_max
        elif original_max < default_max:
            return original_max
        else:
            return default_max

    def _get_all_clauses(self) -> List[Dict]:
        """현재까지 추출된 모든 특약 목록 반환 (ID 생성용)"""
        # 임시로 빈 리스트 반환 (실제로는 DB에서 조회)
        return []
    
    def _apply_realistic_per_unit(self, category: str, original_per_unit: int) -> int:
        """카테고리별 현실적인 per_unit 적용"""
        # original_per_unit이 None이거나 숫자가 아니면 기본값 반환
        if original_per_unit is None or not isinstance(original_per_unit, (int, float)):
            realistic_per_units = {
                '입원': 50000,    # 입원 1일당 최소 5만원
                '통원': 20000,    # 통원 1회당 최소 2만원
                '수술': 300000,   # 수술 1회당 최소 30만원
                '진단': 1000000,  # 진단 1회당 최소 100만원
                '장해': 1000000,  # 장해 1회당 최소 100만원
                '사망': 5000000,  # 사망 1회당 최소 500만원
                '상해': 300000,   # 상해 1회당 최소 30만원
                '질병': 200000,   # 질병 1회당 최소 20만원
            }
            return realistic_per_units.get(category, 50000)
        
        # 실제 보험 기준 per_unit (최소값)
        realistic_per_units = {
            '입원': 50000,    # 입원 1일당 최소 5만원
            '통원': 20000,    # 통원 1회당 최소 2만원
            '수술': 300000,   # 수술 1회당 최소 30만원
            '진단': 1000000,  # 진단 1회당 최소 100만원
            '장해': 1000000,  # 장해 1회당 최소 100만원
            '사망': 5000000,  # 사망 1회당 최소 500만원
            '상해': 300000,   # 상해 1회당 최소 30만원
            '질병': 200000,   # 질병 1회당 최소 20만원
        }
        
        min_per_unit = realistic_per_units.get(category, 50000)
        
        # 원래 값이 최소값보다 작으면 최소값으로 설정
        if original_per_unit < min_per_unit:
            print(f"    💰 {category} 최소 per_unit 적용: {original_per_unit:,}원 → {min_per_unit:,}원")
            return min_per_unit
        
        return original_per_unit

    def add_dummy_clauses_for_claim_calculation(self, data: List[Dict]) -> List[Dict]:
        """진단서/영수증 기반 보험금 산정을 위한 더미 특약 추가"""
        print("🎯 진단서/영수증 기반 보험금 산정용 더미 특약 추가...")
        
        dummy_clauses = [
            # 진단서 기반 특약들
            {
                'id': 'cl_005',
                'clause_name': '질병진단특약',
                'category': '진단',
                'unit_type': 'amount',
                'per_unit': 300000,
                'max_total': 300000,
                'condition': '질병 진단 시 1회 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_006',
                'clause_name': '중증질병진단특약',
                'category': '진단',
                'unit_type': 'amount',
                'per_unit': 500000,
                'max_total': 500000,
                'condition': '중증질병 진단 시 1회 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            
            # 입원 관련 특약들
            {
                'id': 'cl_007',
                'clause_name': '질병입원특약',
                'category': '입원치료',
                'unit_type': 'amount',
                'per_unit': 30000,
                'max_total': 900000,
                'condition': '질병으로 인한 입원 시 1일당 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_008',
                'clause_name': '중증질병입원특약',
                'category': '입원치료',
                'unit_type': 'amount',
                'per_unit': 50000,
                'max_total': 1500000,
                'condition': '중증질병으로 인한 입원 시 1일당 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            
            # 수술 관련 특약들
            {
                'id': 'cl_009',
                'clause_name': '질병수술특약',
                'category': '수술',
                'unit_type': 'amount',
                'per_unit': 200000,
                'max_total': 2000000,
                'condition': '질병으로 인한 수술 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_010',
                'clause_name': '중증질병수술특약',
                'category': '수술',
                'unit_type': 'amount',
                'per_unit': 500000,
                'max_total': 5000000,
                'condition': '중증질병으로 인한 수술 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            
            # 통원 관련 특약들
            {
                'id': 'cl_011',
                'clause_name': '질병통원특약',
                'category': '통원치료',
                'unit_type': 'amount',
                'per_unit': 20000,
                'max_total': 600000,
                'condition': '질병으로 인한 통원진료 시 1회당 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_012',
                'clause_name': '중증질병통원특약',
                'category': '통원치료',
                'unit_type': 'amount',
                'per_unit': 30000,
                'max_total': 900000,
                'condition': '중증질병으로 인한 통원진료 시 1회당 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            
            # 검사 관련 특약들
            {
                'id': 'cl_013',
                'clause_name': '진단검사특약',
                'category': '검사',
                'unit_type': 'amount',
                'per_unit': 50000,
                'max_total': 500000,
                'condition': '진단검사 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_014',
                'clause_name': '중증질병검사특약',
                'category': '검사',
                'unit_type': 'amount',
                'per_unit': 100000,
                'max_total': 1000000,
                'condition': '중증질병 관련 검사 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            
            # 치료 관련 특약들
            {
                'id': 'cl_015',
                'clause_name': '질병치료특약',
                'category': '치료',
                'unit_type': 'amount',
                'per_unit': 100000,
                'max_total': 1000000,
                'condition': '질병치료 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            },
            {
                'id': 'cl_016',
                'clause_name': '중증질병치료특약',
                'category': '치료',
                'unit_type': 'amount',
                'per_unit': 300000,
                'max_total': 3000000,
                'condition': '중증질병치료 시 지급',
                'insurance_company': '삼성생명',
                'policy_type': '종신보험',
                'is_active': True
            }
        ]
        
        # 기존 데이터에 더미 특약 추가
        extended_data = data + dummy_clauses
        
        print(f"✅ 더미 특약 {len(dummy_clauses)}개 추가 완료")
        print(f"📊 총 특약 수: {len(extended_data)}개")
        
        return extended_data

def main():
    processor = PolicyProcessor()
    processor.run_full_process()

if __name__ == "__main__":
    main() 