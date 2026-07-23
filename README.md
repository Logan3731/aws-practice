# 🏥 마이 헬스 로그 API (My Health Log API)

> 개인의 건강 수치를 기록하고 분석하여 BMI, 혈압, 혈당 상태를 분류 및 경고해 주는 FastAPI 기반 RESTful API입니다.

---

## 🛠️ 기술 스택
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Validation**: Pydantic
- **Container**: Docker
- **Data Persistence**: JSON File (`data.json`)

---

## ✨ 주요 기능
- **건강 기록 CRUD**: 건강 데이터 추가/조회/수정/삭제
- **자동 계산 & 분류**: BMI 자동 계산, 비만도/혈압/혈당 단계 분류
- **경고 메시지 생성**: 이상 수치 감지 시 위험 경고 문구 출력 (`warnings`)
- **검색 & 통계**: 날짜 구간 검색 (`GET /search`) 및 평균 수치 통계 (`GET /stats`)

---

## 📌 API 엔드포인트 목록

| 메서드 | 경로 | 설명 |
| :--- | :--- | :--- |
| `GET` | `/` | API 접속 확인 |
| `POST` | `/records` | 건강 기록 추가 (BMI 및 상태 자동 계산) |
| `GET` | `/records` | 전체 기록 목록 조회 |
| `GET` | `/records/{id}` | 특정 기록 단건 조회 |
| `PUT` | `/records/{id}` | 특정 기록 수정 |
| `DELETE` | `/records/{id}` | 특정 기록 삭제 |
| `GET` | `/search` | 날짜 범위(`start`, `end`) 검색 |
| `GET` | `/stats` | 전체 기록 평균 통계 반환 |

---

## 🚀 실행 방법

### 1. 로컬 실행 (Local)
```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload