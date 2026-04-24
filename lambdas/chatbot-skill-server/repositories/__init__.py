"""
Smart Scan 챗봇 스킬 서버 데이터 접근 계층

카카오톡 챗봇에서 데이터 조작을 위한 리포지토리 모듈들을 제공합니다.
FastAPI 백엔드 호출을 통해 아이템, 태그, 사용자 관리 기능을 수행합니다.

제공 리포지토리:
- item_repository: 아이템 데이터 조작 (HTTP 클라이언트)
- tag_repository: RFID 태그 데이터 조작
- user_repository: 사용자 데이터 조작

모든 리포지토리는 SmartScan FastAPI 백엔드와 HTTP 통신으로 작동합니다.
"""