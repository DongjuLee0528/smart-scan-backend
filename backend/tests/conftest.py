"""
백엔드 유닛 테스트 공통 설정

JWT, DB 연결 없이 순수 서비스 로직만 테스트할 수 있도록
환경변수를 development 모드로 강제 설정한다.
"""
import os

# Settings / db.py 임포트 전에 환경변수를 세팅해야 각종 guard를 우회할 수 있다
os.environ["ENV"] = "development"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32c")
os.environ.setdefault("KAKAO_LINK_JWT_SECRET", "test-kakao-link-secret-for-unit-tests!!")
# DB 연결은 실제로 이루어지지 않지만 db.py 모듈 로드 시 URL 검사를 통과해야 한다
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
