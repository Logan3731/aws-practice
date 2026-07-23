# 1. 파이썬 3.11 경량화 이미지 사용
FROM python:3.11-slim

# 2. 컨테이너 내부 작업 디렉토리 설정
WORKDIR /app

# 3. 필요 패키지 목록 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 전체 복사
COPY . .

# 5. FastAPI 기본 포트 8000 노출
EXPOSE 8000

# 6. 컨테이너 실행 명령 (Uvicorn으로 main:app 구동)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]