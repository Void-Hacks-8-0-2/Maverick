"""
Step 9: Process-Local Storage for Legal Freeze Drafts
Operation 'ABHEDYA-CHAKRA'

PERSISTENCE NOTICE:
Legal draft metadata and generated artifacts are maintained in process-local storage
and are not persistent across backend restarts.
"""

from typing import Dict, List, Optional
from threading import Lock

from backend.legal_freeze.models import LegalDraftPackage


class LegalDraftStore:
    """Thread-safe, process-local storage for legal draft packages and generated binary artifacts."""

    def __init__(self):
        self._lock = Lock()
        self._packages: Dict[str, LegalDraftPackage] = {}
        self._pdf_artifacts: Dict[str, bytes] = {}
        self._json_artifacts: Dict[str, bytes] = {}

    def save(
        self,
        package: LegalDraftPackage,
        pdf_bytes: bytes,
        json_bytes: bytes,
    ) -> None:
        with self._lock:
            self._packages[package.package_id] = package
            self._pdf_artifacts[package.package_id] = pdf_bytes
            self._json_artifacts[package.package_id] = json_bytes

    def get(self, package_id: str) -> Optional[LegalDraftPackage]:
        with self._lock:
            return self._packages.get(package_id)

    def get_pdf(self, package_id: str) -> Optional[bytes]:
        with self._lock:
            return self._pdf_artifacts.get(package_id)

    def get_json(self, package_id: str) -> Optional[bytes]:
        with self._lock:
            return self._json_artifacts.get(package_id)

    def list_by_account(self, account: str) -> List[LegalDraftPackage]:
        clean_acc = account.strip().upper()
        with self._lock:
            return [
                pkg for pkg in self._packages.values()
                if pkg.subject_account == clean_acc
            ]

    def list_all(self) -> List[LegalDraftPackage]:
        with self._lock:
            return list(self._packages.values())

    def clear(self) -> None:
        with self._lock:
            self._packages.clear()
            self._pdf_artifacts.clear()
            self._json_artifacts.clear()


# Global in-memory singleton
LEGAL_DRAFT_STORE = LegalDraftStore()
