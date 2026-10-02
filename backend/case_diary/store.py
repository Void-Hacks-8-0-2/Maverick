"""
Case Diary Thread-Safe In-Memory Store for Operation 'ABHEDYA-CHAKRA'
Step 8: Process-local diary storage — mirrors the CaseFileStore pattern.

LIMITATION: Case-diary metadata and generated artifacts are maintained in
process-local storage and are not persistent across backend restarts.
"""

import threading
from typing import Dict, Optional

from backend.case_diary.models import CaseDiary


class CaseDiaryStore:
    """Thread-safe in-process store for generated case diaries."""

    def __init__(self):
        self._lock = threading.Lock()
        self._diaries: Dict[str, CaseDiary] = {}

    def save(self, diary: CaseDiary) -> None:
        with self._lock:
            self._diaries[diary.case_diary_id] = diary

    def get(self, diary_id: str) -> Optional[CaseDiary]:
        with self._lock:
            return self._diaries.get(diary_id)

    def update_narrative(
        self,
        diary_id: str,
        narrative: str,
        narrative_metadata,
        updated_at: str,
    ) -> Optional[CaseDiary]:
        with self._lock:
            diary = self._diaries.get(diary_id)
            if diary is None:
                return None
            diary.ai_narrative = narrative
            diary.narrative_metadata = narrative_metadata
            diary.updated_at = updated_at
            self._diaries[diary_id] = diary
            return diary

    def update_investigator_notes(
        self,
        diary_id: str,
        notes: str,
        updated_at: str,
    ) -> Optional[CaseDiary]:
        with self._lock:
            diary = self._diaries.get(diary_id)
            if diary is None:
                return None
            diary.investigator_notes = notes
            diary.updated_at = updated_at
            self._diaries[diary_id] = diary
            return diary

    def exists(self, diary_id: str) -> bool:
        with self._lock:
            return diary_id in self._diaries

    def list_ids(self) -> list:
        with self._lock:
            return list(self._diaries.keys())


# Global singleton — mirrors CASE_FILE_STORE pattern
CASE_DIARY_STORE = CaseDiaryStore()
