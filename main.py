import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

import models
from database import engine, get_db

# DB 테이블 자동 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="마이 헬스 로그 API", version="2.0")

# --- [인증 및 보안 설정] ---
SECRET_KEY = "my_secret_key_for_health_log_app_change_this_in_prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1일

# bcrypt 대신 pbkdf2_sha256 사용
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# --- [유틸리티 함수: 비밀번호 암호화 및 토큰] ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 검증할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# --- [Pydantic 스키마] ---
class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


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
    user_id: int
    bmi: float = 0.0
    bmi_category: str = ""
    bp_category: str = ""
    sugar_category: str = ""
    activity_category: str = ""
    sleep_category: str = ""

    class Config:
        from_attributes = True


# --- [비즈니스 로직 함수] ---
def calculate_metrics(
    weight: float,
    height: float,
    systolic: int,
    diastolic: int,
    blood_sugar: int,
    steps: int,
    sleep_hours: float,
):
    height_m = height / 100
    bmi = round(weight / (height_m * height_m), 1)

    bmi_cat = (
        "저체중"
        if bmi < 18.5
        else ("정상" if bmi <= 22.9 else ("과체중" if bmi <= 24.9 else "비만"))
    )
    bp_cat = (
        "정상"
        if (systolic < 120 and diastolic < 80)
        else ("고혈압" if (systolic >= 140 or diastolic >= 90) else "주의")
    )
    sugar_cat = (
        "정상"
        if blood_sugar < 100
        else ("공복혈당장애" if blood_sugar <= 125 else "당뇨 의심")
    )
    act_cat = "부족" if steps < 5000 else ("적정" if steps < 10000 else "우수")
    sleep_cat = (
        "수면 부족" if sleep_hours < 7.0 else ("적정 수면" if sleep_hours <= 9.0 else "수면 과다")
    )

    return {
        "bmi": bmi,
        "bmi_category": bmi_cat,
        "bp_category": bp_cat,
        "sugar_category": sugar_cat,
        "activity_category": act_cat,
        "sleep_category": sleep_cat,
    }


# --- [회원가입 & 로그인 엔드포인트] ---
@app.post("/signup", status_code=201)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = (
        db.query(models.User)
        .filter(models.User.username == user_data.username)
        .first()
    )
    if db_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    hashed_pwd = get_password_hash(user_data.password)
    new_user = models.User(
        username=user_data.username, hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"'{new_user.username}' 님, 회원가입이 완료되었습니다!"}


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.username == form_data.username)
        .first()
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400, detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- [건강 기록 CRUD 엔드포인트] ---
@app.post("/records", response_model=RecordOut)
def create_record(
    record: RecordIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_record = models.Record(**record.model_dump(), user_id=current_user.id)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    res = RecordOut.model_validate(db_record)
    metrics = calculate_metrics(
        db_record.weight,
        db_record.height,
        db_record.systolic,
        db_record.diastolic,
        db_record.blood_sugar,
        db_record.steps,
        db_record.sleep_hours,
    )
    for k, v in metrics.items():
        setattr(res, k, v)
    return res


@app.get("/records", response_model=List[RecordOut])
def get_records(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(models.Record)
        .filter(models.Record.user_id == current_user.id)
        .all()
    )
    results = []
    for r in records:
        r_out = RecordOut.model_validate(r)
        metrics = calculate_metrics(
            r.weight,
            r.height,
            r.systolic,
            r.diastolic,
            r.blood_sugar,
            r.steps,
            r.sleep_hours,
        )
        for k, v in metrics.items():
            setattr(r_out, k, v)
        results.append(r_out)
    return results


# --- [HTML 대시보드] ---
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>마이 헬스 로그 (SQLite & JWT)</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 30px auto; padding: 0 20px; line-height: 1.6; }
        h1, h2 { color: #2c3e50; }
        .card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .form-group { margin-bottom: 12px; }
        label { display: inline-block; width: 110px; font-weight: bold; }
        input { padding: 8px; width: 200px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .hidden { display: none; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background: #e9ecef; }
    </style>
</head>
<body>
    <h1>🏥 마이 헬스 로그 대시보드</h1>

    <!-- 로그인 / 회원가입 영역 -->
    <div id="authSection" class="card">
        <h2>🔑 로그인 / 회원가입</h2>
        <div class="form-group"><label>아이디:</label><input type="text" id="auth_username"></div>
        <div class="form-group"><label>비밀번호:</label><input type="password" id="auth_password"></div>
        <button type="button" onclick="login()">로그인</button>
        <button type="button" onclick="signup()" style="background: #28a745;">회원가입</button>
    </div>

    <!-- 대시보드 메인 영역 -->
    <div id="appSection" class="hidden">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 id="welcomeMsg"></h3>
            <button type="button" onclick="logout()" style="background: #dc3545;">로그아웃</button>
        </div>

        <div class="card">
            <h2>📝 건강 기록 입력</h2>
            <div class="form-group"><label>날짜:</label><input type="date" id="date"></div>
            <div class="form-group"><label>체중 (kg):</label><input type="number" step="0.1" id="weight" value="70"></div>
            <div class="form-group"><label>신장 (cm):</label><input type="number" step="0.1" id="height" value="175"></div>
            <div class="form-group"><label>수축기 혈압:</label><input type="number" id="systolic" value="120"></div>
            <div class="form-group"><label>이완기 혈압:</label><input type="number" id="diastolic" value="80"></div>
            <div class="form-group"><label>공복 혈당:</label><input type="number" id="blood_sugar" value="95"></div>
            <div class="form-group"><label>걸음 수:</label><input type="number" id="steps" value="8000"></div>
            <div class="form-group"><label>수면 시간:</label><input type="number" step="0.5" id="sleep_hours" value="7.5"></div>
            <button type="button" onclick="submitRecord()">기록 저장하기</button>
        </div>

        <div class="card">
            <h2>📋 나의 건강 기록</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>날짜</th><th>BMI</th><th>혈압</th><th>혈당</th><th>걸음수</th><th>수면</th></tr>
                </thead>
                <tbody id="recordTable"></tbody>
            </table>
        </div>
    </div>

    <script>
        document.getElementById('date').value = new Date().toISOString().substring(0, 10);
        let token = localStorage.getItem('access_token');

        if (token) showApp();

        async function signup() {
            const u = document.getElementById('auth_username').value.trim();
            const p = document.getElementById('auth_password').value.trim();
            if (!u || !p) { alert('아이디와 비밀번호를 모두 입력해 주세요!'); return; }

            try {
                const res = await fetch('/signup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                const data = await res.json();
                if (res.ok) {
                    alert(data.message + ' 이제 로그인을 진행해 주세요.');
                } else {
                    alert('회원가입 실패: ' + (data.detail || '오류 발생'));
                }
            } catch (err) {
                alert('서버와 통신할 수 없습니다.');
            }
        }

        async function login() {
            const u = document.getElementById('auth_username').value.trim();
            const p = document.getElementById('auth_password').value.trim();
            if (!u || !p) { alert('아이디와 비밀번호를 입력해 주세요!'); return; }

            try {
                const body = new URLSearchParams({username: u, password: p});
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: body
                });
                const data = await res.json();
                if (res.ok) {
                    token = data.access_token;
                    localStorage.setItem('access_token', token);
                    showApp();
                } else {
                    alert('로그인 실패: ' + (data.detail || '정보를 확인하세요.'));
                }
            } catch (err) {
                alert('로그인 처리 중 오류가 발생했습니다.');
            }
        }

        function logout() {
            localStorage.removeItem('access_token');
            token = null;
            document.getElementById('authSection').classList.remove('hidden');
            document.getElementById('appSection').classList.add('hidden');
        }

        function showApp() {
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('appSection').classList.remove('hidden');
            fetchRecords();
        }

        async function fetchRecords() {
            const res = await fetch('/records', {
                headers: {'Authorization': 'Bearer ' + token}
            });
            if (res.status === 401) { logout(); return; }
            const records = await res.json();
            const tbody = document.getElementById('recordTable');
            tbody.innerHTML = '';
            records.forEach(r => {
                tbody.innerHTML += `<tr>
                    <td>${r.id}</td><td>${r.date}</td>
                    <td>${r.bmi} (${r.bmi_category})</td>
                    <td>${r.systolic}/${r.diastolic} (${r.bp_category})</td>
                    <td>${r.blood_sugar} (${r.sugar_category})</td>
                    <td>${r.steps}보 (${r.activity_category})</td>
                    <td>${r.sleep_hours}h (${r.sleep_category})</td>
                </tr>`;
            });
        }

        async function submitRecord() {
            const payload = {
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
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) { fetchRecords(); } else { alert('저장 실패!'); }
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)