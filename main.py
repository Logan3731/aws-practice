from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# 1. FastAPI 앱 객체 생성
# 서버의 중심이 되는 애플리케이션을 만듭니다.
app = FastAPI(title="마이 헬스 로그 API", version="1.0")

# 2. 임시 데이터 저장소 (Day 3에서 파일 저장 방식으로 발전시킬 예정입니다)
records_db = []
current_id = 1


# 3. Pydantic 모델 정의
# Pydantic은 사용자가 보낸 데이터의 타입(숫자, 문자 등)이 올바른지 검증해 줍니다.
class RecordIn(BaseModel):
    date: str              # 측정일 (예: "2026-07-21")
    weight: float          # 몸무게 (kg)
    height: float          # 키 (cm)
    systolic: int          # 수축기 혈압
    diastolic: int         # 이완기 혈압
    blood_sugar: int       # 공복 혈당 (mg/dL)
    steps: int = 0         # 걸음 수 (기본값 0)
    sleep_hours: float = 0.0  # 수면 시간 (기본값 0.0)
    memo: str = ""         # 메모 (기본값 빈 문자열)


# 응답 시 사용될 모델 (ID 및 계산 결과 필드 포함)
class RecordOut(RecordIn):
    id: int
    bmi: float = 0.0
    bmi_category: str = ""
    bp_category: str = ""
    sugar_category: str = ""
    warnings: List[str] = []


# 4. 엔드포인트(API URL) 구현

# [GET /] : 서버가 잘 작동하는지 확인하는 기본 접속 경로
@app.get("/")
def read_root():
    return {"message": "마이 헬스 로그 API 접속 성공!"}


# [POST /records] : 새로운 건강 기록 추가
@app.post("/records", response_model=RecordOut)
def create_record(record: RecordIn):
    global current_id
    
    new_data = record.model_dump() # Pydantic 모델을 파이썬 딕셔너리로 변환
    new_data["id"] = current_id     # 고유 ID 부여
    
    # Day 2에서 이 위치에 BMI 및 건강 분류 계산 로직이 들어갑니다.
    new_data["bmi"] = 0.0
    new_data["bmi_category"] = "미계산"
    new_data["bp_category"] = "미계산"
    new_data["sugar_category"] = "미계산"
    new_data["warnings"] = []
    
    records_db.append(new_data)
    current_id += 1
    return new_data


# [GET /records] : 저장된 전체 기록 목록 조회
@app.get("/records")
def get_records():
    return {
        "total_count": len(records_db),
        "records": records_db
    }


# [GET /records/{id}] : 특정 ID의 기록 하나만 조회
@app.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: int):
    for r in records_db:
        if r["id"] == record_id:
            return r
    # 찾는 ID가 없을 경우 404 에러 반환
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")


# [DELETE /records/{id}] : 특정 ID의 기록 삭제
@app.delete("/records/{record_id}")
def delete_record(record_id: int):
    for idx, r in enumerate(records_db):
        if r["id"] == record_id:
            deleted = records_db.pop(idx)
            return {"message": f"ID {record_id} 기록 삭제 완료", "deleted_record": deleted}
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")