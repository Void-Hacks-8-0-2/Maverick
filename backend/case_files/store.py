"""
In-Memory Thread-Safe Case File Store for Operation 'ABHEDYA-CHAKRA'
Stores compiled PDF and JSON evidence packages for secure download by Case File ID.
Does NOT expose filesystem paths or write mutable files to unsafe locations.
"""

import threading
from typing import Optional, Dict, Any, Tuple
from backend.case_files.models import CaseFileResponse


class CaseFileStore:
    """Thread-safe store of generated forensic case files and compiled binary artifacts."""
    def __init__(self):
        self._lock = threading.Lock()
        self._responses: Dict[str, CaseFileResponse] = {}
        self._pdf_bytes: Dict[str, bytes] = {}
        self._json_bytes: Dict[str, bytes] = {}

    def save(
        self,
        case_file_id: str,
        response: CaseFileResponse,
        pdf_data: Optional[bytes] = None,
        json_data: Optional[bytes] = None,
    ):
        with self._lock:
            self._responses[case_file_id] = response
            if pdf_data:
                self._pdf_bytes[case_file_id] = pdf_data
            if json_data:
                self._json_bytes[case_file_id] = json_data

    def get_response(self, case_file_id: str) -> Optional[CaseFileResponse]:
        with self._lock:
            return self._responses.get(case_file_id)

    def get_pdf(self, case_file_id: str) -> Optional[bytes]:
        with self._lock:
            return self._pdf_bytes.get(case_file_id)

    def get_json(self, case_file_id: str) -> Optional[bytes]:
        with self._lock:
            return self._json_bytes.get(case_file_id)

    def exists(self, case_file_id: str) -> bool:
        with self._lock:
            return case_file_id in self._responses


# Global singleton instance
CASE_FILE_STORE = CaseFileStore()
