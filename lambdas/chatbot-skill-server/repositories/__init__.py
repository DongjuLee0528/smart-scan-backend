"""
Smart Scan Chatbot Skill Server Data Access Layer

Provides repository modules for data manipulation from the KakaoTalk chatbot.
Performs item, tag, and user management functions through FastAPI backend calls.

Available Repositories:
- item_repository: Item data manipulation (HTTP client)
- tag_repository: RFID tag data manipulation
- user_repository: User data manipulation

All repositories operate through HTTP communication with the SmartScan FastAPI backend.
"""