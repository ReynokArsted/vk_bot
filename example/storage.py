from typing import Dict, Any

pending_requests: Dict[str, Dict[str, Any]] = {}
approval_votes: Dict[str, Dict[str, str]] = {}
chat_members: Dict[str, Dict[str, Any]] = {}
current_request: Dict[str, str] = {}
request_images: Dict[str, str] = {}  # Новый словарь для хранения image file_id по request_id
