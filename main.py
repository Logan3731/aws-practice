import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="마이 헬스 로그 API", version="1.0")

DATA_FILE = "data.json"
records_db = []
current_id = 1


# --- [파일 저장 & 불러오기] ---
def load_data():
    global records_db, current_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                records_db = json.load(f)
                if records_db:
                    current_id = max(r["id"] for r in records_db) + 1
                else:
                    current_id = 1
        except Exception:
            records_db = []
            current_id = 1
    else:
        records_db = []
        current_id = 1


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records_db, f, ensure_ascii=False, indent=2)


load_data()


# --- [Pydantic 스키마] ---
class RecordIn(BaseModel):
    date: str
    weight: float
    height: float
    systolic: int
    diastolic: int
    blood_sugar: int
    steps: int = 0
    sleep_hours: float = 0.0
    memo: str = ""


class RecordOut(RecordIn):
    id: int
    bmi: float = 0.0
    bmi_category: str = ""
    bp_category: str = ""
    sugar_category: str = ""
    activity_category: str = ""  # 걸음 수 등급
    sleep_category: str = ""     # 수면 분석 등급 (신규)
    warnings: List[str] = []


# --- [비즈니스 로직] ---
def calculate_health_metrics(weight: float, height: float, systolic: int, diastolic: int, blood_sugar: int, steps: int = 0, sleep_hours: float = 0.0):
    height_m = height / 100
    bmi = round(weight / (height_m * height_m), 1)

    if bmi < 18.5:
        bmi_category = "저체중"
    elif bmi <= 22.9:
        bmi_category = "정상"
    elif bmi <= 24.9:
        bmi_category = "과체중"
    else:
        bmi_category = "비만"

    if systolic < 120 and diastolic < 80:
        bp_category = "정상"
    elif systolic >= 140 or diastolic >= 90:
        bp_category = "고혈압"
    else:
        bp_category = "주의"

    if blood_sugar < 100:
        sugar_category = "정상"
    elif blood_sugar <= 125:
        sugar_category = "공복혈당장애"
    else:
        sugar_category = "당뇨 의심"

    # 1. 걸음 수 활동량 분류
    if steps < 5000:
        activity_category = "부족"
    elif steps < 10000:
        activity_category = "적정"
    else:
        activity_category = "우수"

    # 2. 수면 분석 분류 (신규)
    if sleep_hours < 7.0:
        sleep_category = "수면 부족"
    elif sleep_hours <= 9.0:
        sleep_category = "적정 수면"
    else:
        sleep_category = "수면 과다"

    warnings = []
    if bmi_category == "비만":
        warnings.append("BMI 비만 상태입니다. 체중 관리가 필요합니다.")
    if bp_category == "고혈압":
        warnings.append("혈압이 고혈압 수준입니다. 정밀 검진을 권장합니다.")
    if sugar_category == "당뇨 의심":
        warnings.append("공복 혈당이 당뇨 의심 수준입니다. 관리가 필요합니다.")
    if activity_category == "부족":
        warnings.append("일일 활동량이 부족합니다. 걷기 운동을 권장합니다.")
    if sleep_category == "수면 부족":
        warnings.append("권장 수면시간(7~9시간)보다 적게 잤습니다. 충분한 휴식이 필요합니다.")

    return {
        "bmi": bmi,
        "bmi_category": bmi_category,
        "bp_category": bp_category,
        "sugar_category": sugar_category,
        "activity_category": activity_category,
        "sleep_category": sleep_category,
        "warnings": warnings
    }


# --- [API 엔드포인트] ---
@app.get("/")
def read_root():
    return {"message": "마이 헬스 로그 API 접속 성공!"}


@app.post("/records", response_model=RecordOut)
def create_record(record: RecordIn):
    global current_id
    
    new_data = record.model_dump()
    new_data["id"] = current_id

    metrics = calculate_health_metrics(
        record.weight, record.height, record.systolic, record.diastolic, 
        record.blood_sugar, record.steps, record.sleep_hours
    )
    new_data.update(metrics)

    records_db.append(new_data)
    current_id += 1
    
    save_data()
    return new_data


@app.get("/records")
def get_records():
    return {
        "total_count": len(records_db),
        "records": records_db
    }


@app.get("/search")
def search_records(start: str, end: str):
    filtered = [r for r in records_db if start <= r["date"] <= end]
    return {
        "start": start,
        "end": end,
        "count": len(filtered),
        "records": filtered
    }


@app.get("/stats")
def get_stats():
    if not records_db:
        return {"message": "저장된 기록이 없습니다."}

    total = len(records_db)
    avg_weight = sum(r["weight"] for r in records_db) / total
    avg_systolic = sum(r["systolic"] for r in records_db) / total
    avg_diastolic = sum(r["diastolic"] for r in records_db) / total
    avg_blood_sugar = sum(r["blood_sugar"] for r in records_db) / total

    return {
        "total_records": total,
        "avg_weight": round(avg_weight, 1),
        "avg_systolic": round(avg_systolic, 1),
        "avg_diastolic": round(avg_diastolic, 1),
        "avg_blood_sugar": round(avg_blood_sugar, 1)
    }


@app.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: int):
    for r in records_db:
        if r["id"] == record_id:
            return r
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")


@app.put("/records/{record_id}", response_model=RecordOut)
def update_record(record_id: int, updated_record: RecordIn):
    for idx, r in enumerate(records_db):
        if r["id"] == record_id:
            data = updated_record.model_dump()
            data["id"] = record_id

            metrics = calculate_health_metrics(
                updated_record.weight, updated_record.height, 
                updated_record.systolic, updated_record.diastolic, 
                updated_record.blood_sugar, updated_record.steps,
                updated_record.sleep_hours
            )
            data.update(metrics)

            records_db[idx] = data
            save_data()
            return data

    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")


@app.delete("/records/{record_id}")
def delete_record(record_id: int):
    for idx, r in enumerate(records_db):
        if r["id"] == record_id:
            deleted = records_db.pop(idx)
            save_data()
            return {"message": f"ID {record_id} 기록 삭제 완료", "deleted_record": deleted}
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")