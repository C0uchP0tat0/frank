import logging
import json, os
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

@dataclass
class InterviewState:
    vacancy_key: Optional[str] = None
    q_index: int = 0
    answers: List[str] = field(default_factory=list)
    history: List[Dict[str, str]] = field(default_factory=list)
    
    followup_polls: List[str] = field(default_factory=list)
    followup_answers: List[Dict[str, Any]] = field(default_factory=list)
    followup_meta: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_clarification: Optional[Dict[str, Any]] = None

    pending_followup_qindex: Optional[int] = None
    pending_followup_text: Optional[str] = None
    
    # Новые поля для обратной связи
    feedback_requested: bool = False
    feedback_text: Optional[str] = None
    feedback_audio: Optional[str] = None  # Добавляем поле для аудио файла
    
    # Поле для кэширования результатов анализа
    cached_analysis: Optional[Dict[str, Any]] = None

    hr_candidates: List[Dict[str, Any]] = field(default_factory=list)
    
    # Поле для хранения загруженных файлов резюме
    file_resumes: Dict[str, Dict[str, Any]] = field(default_factory=dict)

USER_STATES: Dict[int, InterviewState] = {}
STATE_DIR = "state"

def _user_state_path(uid: int) -> str:
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, f"user_{uid}.json")

def load_state():
    try:
        if not os.path.isdir(STATE_DIR):
            return
        for name in os.listdir(STATE_DIR):
            if not name.startswith("user_") or not name.endswith(".json"):
                continue
            try:
                uid = int(name.split("_", 1)[1].split(".json")[0])
            except Exception:
                continue
            data = json.load(open(os.path.join(STATE_DIR, name), "r", encoding="utf-8"))
            # Фильтруем только известные поля для совместимости
            known_fields = {
                'vacancy_key', 'q_index', 'answers', 'history', 'followup_polls', 
                'followup_answers', 'followup_meta', 'pending_clarification',
                'pending_followup_qindex', 'pending_followup_text', 'feedback_requested',
                'feedback_text', 'feedback_audio', 'cached_analysis', 'hr_candidates', 'file_resumes'
            }
            filtered_data = {k: v for k, v in data.items() if k in known_fields}
            USER_STATES[uid] = InterviewState(**filtered_data)
    except Exception:
        logging.exception("Не удалось загрузить состояние")

def save_state(uid: Optional[int] = None):
    try:
        if uid is not None:
            s = USER_STATES.get(uid)
            if s is None:
                return
            with open(_user_state_path(uid), "w", encoding="utf-8") as f:
                json.dump(s.__dict__, f, ensure_ascii=False, indent=2)
            return
        # if uid не указан — сохранить всех (совместимо с текущими вызовами)
        for u, s in USER_STATES.items():
            with open(_user_state_path(u), "w", encoding="utf-8") as f:
                json.dump(s.__dict__, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Не удалось сохранить состояние")