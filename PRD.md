# 📄 Product Requirement Document (PRD)

## 1. 프로젝트 개요 (Overview)
* **프로젝트명**: 마이 헬스 로그 (My Health Log)
* **목적**: 사용자가 일별 신체 지표(체중, 혈압, 혈당) 및 라이프스타일 데이터(걸음 수, 수면 시간)를 손쉽게 기록하고, 지표별 건강 상태를 즉시 확인할 수 있는 개별 맞춤형 서비스 제공
* **주요 타겟**: 일상적인 건강 데이터 관리가 필요한 개인 사용자

---

## 2. 핵심 기능 요구사항 (Key Features)

### 2.1. 사용자 인증 및 보안 (Authentication)
* **회원가입**: 아이디 및 비밀번호를 통한 신규 계정 생성 (PBKDF2-SHA256 해싱 적용)
* **로그인 / 토큰 발급**: OAuth2 규격 기반 JWT(JSON Web Token) 발급 및 브라우저 LocalStorage 내 저장
* **데이터 격리**: 로그인한 개별 사용자의 데이터만 조회/수정/삭제 가능하도록 사용자 단위 분리

### 2.2. 건강 기록 관리 (Health Records - CRUD)
* **기록 입력**: 날짜, 체중(kg), 신장(cm), 수축기/이완기 혈압(mmHg), 공복 혈당(mg/dL), 걸음 수, 수면 시간(시간) 저장
* **기록 조회**: 본인의 과거 기록 목록 일괄 조회

### 2.3. 건강 지표 자동 계산 및 판정 (Health Metrics Engine)
* **BMI 계산**: $\text{BMI} = \text{체중}(\text{kg}) / (\text{신장}(\text{m}))^2$
  * 저체중(<18.5) / 정상(18.5~22.9) / 과체중(23.0~24.9) / 비만(≥25.0)
* **혈압 판정**:
  * 정상(<120/80) / 고혈압(≥140/90) / 주의(기타 범위)
* **공복 혈당 판정**:
  * 정상(<100) / 공복혈당장애(100~125) / 당뇨 의심(≥126)
* **활동량 & 수면 분석**:
  * 활동량: 부족(<5000보) / 적정(<10000보) / 우수(≥10000보)
  * 수면: 수면 부족(<7h) / 적정 수면(7~9h) / 수면 과다(>9h)

---

## 3. 시스템 아키텍처 및 기술 스택 (System Architecture)
* **Backend**: Python 3.11, FastAPI
* **Database / ORM**: SQLite3, SQLAlchemy
* **Authentication**: Passlib (PBKDF2), PyJWT
* **Deployment**: AWS Lightsail (Ubuntu OS), Docker 컨테이너 기반 배포
* **Frontend**: HTML5, CSS3, JavaScript (Fetch API)