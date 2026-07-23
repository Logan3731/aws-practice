import json
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="마이 헬스 로그 API", version="1.0")

DATA_FILE = "data.json"
records_db = []
goal_db = {}
current_id = 1


# --- [파일 저장 & 불러오기] ---
def load_data():
    global records_db, goal_db, current_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    records_db = data.get("records", [])
                    goal_db = data.get("goal", {})
                elif isinstance(data, list):
                    records_db = data
                    goal_db = {}

                if records_db:
                    valid_ids = [r.get("id", 0) for r in records_db if isinstance(r, dict)]
                    current_id = max(valid_ids) + 1 if valid_ids else 1
                else:
                    current_id = 1
        except Exception:
            records_db = []
            goal_db = {}
            current_id = 1
    else:
        records_db = []
        goal_db = {}
        current_id = 1


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"records": records_db, "goal": goal_db}, f, ensure_ascii=False, indent=2)


load_data()


# --- [Pydantic 스키마] ---
class RecordIn(BaseModel):
    user_id: str = "default_user"
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
    activity_category: str = ""
    sleep_category: str = ""
    warnings: List[str] = []


class GoalSchema(BaseModel):
    user_id: str = "default_user"
    target_weight: float
    target_systolic: int


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

    if steps < 5000:
        activity_category = "부족"
    elif steps < 10000:
        activity_category = "적정"
    else:
        activity_category = "우수"

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
    return {"message": "마이 헬스 로그 API 접속 성공! /dashboard 로 접속해보세요."}


# --- [간단 화면 HTML 엔드포인트] ---
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>마이 헬스 로그 대시보드</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 30px auto; padding: 0 20px; line-height: 1.6; }
            h1, h2 { color: #2c3e50; }
            .card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .form-group { margin-bottom: 12px; }
            label { display: inline-block; width: 100px; font-weight: bold; }
            input { padding: 8px; width: 200px; border: 1px solid #ccc; border-radius: 4px; }
            button { background: #007bff; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background: #e9ecef; }
        </style>
    </head>
    <body>
        <h1>🏥 마이 헬스 로그 대시보드</h1>
        
        <div class="card">
            <h2>📝 건강 기록 입력</h2>
            <form id="recordForm">
                <div class="form-group"><label>사용자 ID:</label><input type="text" id="user_id" value="user1"></div>
                <div class="form-group"><label>날짜:</label><input type="date" id="date"></div>
                <div class="form-group"><label>체중 (kg):</label><input type="number" step="0.1" id="weight" value="70"></div>
                <div class="form-group"><label>신장 (cm):</label><input type="number" step="0.1" id="height" value="175"></div>
                <div class="form-group"><label>수축기 혈압:</label><input type="number" id="systolic" value="120"></div>
                <div class="form-group"><label>이완기 혈압:</label><input type="number" id="diastolic" value="80"></div>
                <div class="form-group"><label>공복 혈당:</label><input type="number" id="blood_sugar" value="95"></div>
                <div class="form-group"><label>걸음 수:</label><input type="number" id="steps" value="8000"></div>
                <div class="form-group"><label>수면 시간:</label><input type="number" step="0.5" id="sleep_hours" value="7.5"></div>
                <button type="button" onclick="submitRecord()">기록 저장하기</button>
            </form>
        </div>

        <div class="card">
            <h2>📋 저장된 건강 기록 목록</h2>
            <button onclick="fetchRecords()">목록 새로고침</button>
            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>사용자</th><th>날짜</th><th>BMI</th><th>혈압</th><th>혈당</th><th>걸음수</th><th>수면</th>
                    </tr>
                </thead>
                <tbody id="recordTable"></tbody>
            </table>
        </div>

        <script>
            document.getElementById('date').value = new Date().toISOString().substring(0, 10);

            async function fetchRecords() {
                const res = await fetch('/records');
                const data = await res.json();
                const tbody = document.getElementById('recordTable');
                tbody.innerHTML = '';
                data.records.forEach(r => {
                    const row = `<tr>
                        <td>${r.id}</td>
                        <td>${r.user_id || 'default'}</td>
                        <td>${r.date}</td>
                        <td>${r.bmi} (${r.bmi_category})</td>
                        <td>${r.systolic}/${r.diastolic} (${r.bp_category})</td>
                        <td>${r.blood_sugar} (${r.sugar_category})</td>
                        <td>${r.steps}보 (${r.activity_category})</td>
                        <td>${r.sleep_hours}h (${r.sleep_category})</td>
                    </tr>`;
                    tbody.innerHTML += row;
                });
            }

            async function submitRecord() {
                const payload = {
                    user_id: document.getElementById('user_id').value,
                    date: document.getElementById('date').value,
                    weight: parseFloat(document.getElementById('weight').value),
                    height: parseFloat(document.getElementById('height').value),
                    systolic: parseInt(document.getElementById('systolic').value),
                    diastolic: parseInt(document.getElementById('diastolic').value),
                    blood_sugar: parseInt(document.getElementById('blood_sugar').value),
                    steps: parseInt(document.getElementById('steps').value),
                    sleep_hours: parseFloat(document.getElementById('sleep_hours').value)
                };

                const res = await fetch('/records', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    alert('기록이 성공적으로 저장되었습니다!');
                    fetchRecords();
                } else {
                    alert('저장 실패!');
                }
            }

            fetchRecords();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# --- [기타 CRUD 및 목표/주간 엔드포인트 생략 없이 유지] ---
@app.post("/goals")
def set_goal(goal: GoalSchema):
    global goal_db
    user_id = goal.user_id
    goal_db[user_id] = goal.model_dump()
    save_data()
    return {"message": f"'{user_id}' 사용자의 목표가 설정되었습니다.", "goal": goal_db[user_id]}


@app.get("/goals/progress")
def get_goal_progress(user_id: str = "default_user"):
    user_goal = goal_db.get(user_id)
    if not user_goal:
        raise HTTPException(status_code=404, detail=f"'{user_id}' 사용자의 목표가 없습니다.")

    user_records = [r for r in records_db if isinstance(r, dict) and r.get("user_id") == user_id]
    if not user_records:
        raise HTTPException(status_code=404, detail=f"'{user_id}' 사용자의 건강 기록이 없습니다.")

    valid_records = []
    for r in user_records:
        try:
            datetime.strptime(r.get("date", ""), "%Y-%m-%d")
            valid_records.append(r)
        except (ValueError, TypeError):
            continue

    if not valid_records:
        raise HTTPException(status_code=404, detail="유효한 날짜 형식을 가진 기록이 없습니다.")

    latest_record = sorted(valid_records, key=lambda x: x["date"])[-1]
    current_weight = latest_record["weight"]
    target_weight = user_goal["target_weight"]
    
    diff = abs(current_weight - target_weight)
    weight_progress = max(0.0, round(100.0 - (diff / target_weight * 100), 1))

    current_systolic = latest_record["systolic"]
    target_systolic = user_goal["target_systolic"]
    bp_achieved = current_systolic <= target_systolic

    return {
        "user_id": user_id,
        "latest_date": latest_record["date"],
        "target": user_goal,
        "current": {"weight": current_weight, "systolic": current_systolic},
        "progress": {
            "weight_achievement_rate": f"{weight_progress}%",
            "bp_target_achieved": bp_achieved
        }
    }


@app.get("/reports/weekly")
def get_weekly_report(user_id: str = "default_user"):
    user_records = [r for r in records_db if isinstance(r, dict) and r.get("user_id", "default_user") == user_id]
    if not user_records:
        return {"message": f"'{user_id}' 사용자의 기록된 데이터가 없습니다."}

    valid_records = []
    for r in user_records:
        date_str = r.get("date", "")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            valid_records.append(r)
        except (ValueError, TypeError):
            continue

    if not valid_records:
        return {"message": "유효한 날짜(YYYY-MM-DD) 데이터가 없습니다."}

    latest_date_str = max(r["date"] for r in valid_records)
    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")

    this_week_start = (latest_date - timedelta(days=6)).strftime("%Y-%m-%d")
    last_week_start = (latest_date - timedelta(days=13)).strftime("%Y-%m-%d")
    last_week_end = (latest_date - timedelta(days=7)).strftime("%Y-%m-%d")

    this_week_records = [r for r in valid_records if this_week_start <= r["date"] <= latest_date_str]
    last_week_records = [r for r in valid_records if last_week_start <= r["date"] <= last_week_end]

    def get_avg(records, key):
        valid_vals = [r[key] for r in records if key in r and isinstance(r[key], (int, float))]
        if not valid_vals:
            return 0.0
        return round(sum(valid_vals) / len(valid_vals), 1)

    this_avg_weight = get_avg(this_week_records, "weight")
    last_avg_weight = get_avg(last_week_records, "weight")

    this_avg_systolic = get_avg(this_week_records, "systolic")
    last_avg_systolic = get_avg(last_week_records, "systolic")

    return {
        "user_id": user_id,
        "period": {
            "this_week": f"{this_week_start} ~ {latest_date_str}",
            "last_week": f"{last_week_start} ~ {last_week_end}"
        },
        "this_week_avg": {
            "weight": this_avg_weight,
            "systolic": this_avg_systolic,
            "count": len(this_week_records)
        },
        "last_week_avg": {
            "weight": last_avg_weight,
            "systolic": last_avg_systolic,
            "count": len(last_week_records)
        },
        "comparison": {
            "weight_diff": round(this_avg_weight - last_avg_weight, 1) if last_avg_weight > 0 else "지난주 데이터 없음",
            "systolic_diff": round(this_avg_systolic - last_avg_systolic, 1) if last_avg_systolic > 0 else "지난주 데이터 없음"
        }
    }


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
def get_records(user_id: Optional[str] = None):
    if user_id:
        filtered = [r for r in records_db if isinstance(r, dict) and r.get("user_id") == user_id]
        return {"user_id": user_id, "total_count": len(filtered), "records": filtered}
    return {
        "total_count": len(records_db),
        "records": records_db
    }


@app.get("/search")
def search_records(start: str, end: str, user_id: Optional[str] = None):
    filtered = [r for r in records_db if isinstance(r, dict) and start <= r.get("date", "") <= end]
    if user_id:
        filtered = [r for r in filtered if r.get("user_id") == user_id]
    return {
        "user_id": user_id,
        "start": start,
        "end": end,
        "count": len(filtered),
        "records": filtered
    }


@app.get("/stats")
def get_stats(user_id: Optional[str] = None):
    target_records = records_db
    if user_id:
        target_records = [r for r in records_db if isinstance(r, dict) and r.get("user_id") == user_id]

    if not target_records:
        return {"message": "저장된 기록이 없습니다."}

    total = len(target_records)
    avg_weight = sum(r["weight"] for r in target_records if isinstance(r, dict) and "weight" in r) / total
    avg_systolic = sum(r["systolic"] for r in target_records if isinstance(r, dict) and "systolic" in r) / total
    avg_diastolic = sum(r["diastolic"] for r in target_records if isinstance(r, dict) and "diastolic" in r) / total
    avg_blood_sugar = sum(r["blood_sugar"] for r in target_records if isinstance(r, dict) and "blood_sugar" in r) / total

    return {
        "user_id": user_id,
        "total_records": total,
        "avg_weight": round(avg_weight, 1),
        "avg_systolic": round(avg_systolic, 1),
        "avg_diastolic": round(avg_diastolic, 1),
        "avg_blood_sugar": round(avg_blood_sugar, 1)
    }


@app.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: int):
    for r in records_db:
        if isinstance(r, dict) and r.get("id") == record_id:
            return r
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")


@app.put("/records/{record_id}", response_model=RecordOut)
def update_record(record_id: int, updated_record: RecordIn):
    for idx, r in enumerate(records_db):
        if isinstance(r, dict) and r.get("id") == record_id:
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
        if isinstance(r, dict) and r.get("id") == record_id:
            deleted = records_db.pop(idx)
            save_data()
            return {"message": f"ID {record_id} 기록 삭제 완료", "deleted_record": deleted}
    raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다.")