"""Secure temporary storage for uploaded files.

WHY THIS FILE EXISTS
    Between "upload received" and "analysis finished", the file has to
    live SOMEWHERE on disk. That somewhere must be private, must never
    reuse the patient's own filename (filenames are PHI — people name
    files "ramesh_hiv_report.pdf"), and must be deleted afterwards no
    matter what happened — crash included. Leftover temp files containing
    medical documents are a data breach waiting for a janitor.

HOW A CONTEXT MANAGER GUARANTEES CLEANUP
    Any object with __enter__ and __exit__ methods can be used in a
    `with` block:

        with SecureUploadDir() as upload_dir:
            stored = upload_dir.store(some_path)
            ...work with stored...
        # <- directory is ALREADY gone here, even if ... raised!

    Python calls __enter__ going in, and GUARANTEES __exit__ runs on the
    way out — normal exit, `return`, or an exception flying through.
    That guarantee is the entire point: cleanup cannot be forgotten,
    because it is not the caller's job.
"""

import shutil
import tempfile
import uuid
from pathlib import Path


class SecureUploadDir:
    """A private, self-destructing directory for one upload session."""

    def __init__(self) -> None:
        # The directory is NOT created here — only in __enter__. Creating
        # resources in __enter__ keeps "object exists" separate from
        # "resource is live", so a SecureUploadDir that was never entered
        # never touches the disk.
        self._path: Path | None = None

    def __enter__(self) -> "SecureUploadDir":
        # mkdtemp creates a directory only THIS user can read (mode 700)
        # with an unpredictable name — private by construction.
        self._path = Path(tempfile.mkdtemp(prefix="mediscan_"))
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # The three arguments describe any exception currently flying
        # (all None on a clean exit). We clean up IDENTICALLY either way,
        # and by not returning True we let any exception continue on to
        # the caller — cleanup must never swallow errors.
        if self._path is not None:
            shutil.rmtree(self._path, ignore_errors=True)
            self._path = None

    @property
    def path(self) -> Path:
        """The live directory. Using it outside `with` is a bug — say so."""
        if self._path is None:
            raise RuntimeError(
                "SecureUploadDir used outside its 'with' block "
                "(the directory does not exist yet, or was already cleaned up)"
            )
        return self._path

    def store(self, source: Path) -> Path:
        """Copy a validated upload into the secure directory.

        The stored name is a random UUID + the original EXTENSION only.
        The user's filename never survives into our storage layer (PHI),
        but the extension is kept so later stages can still route by type.
        """
        destination = self.path / f"{uuid.uuid4().hex}{source.suffix.lower()}"
        shutil.copy2(source, destination)  # copy2 = contents + timestamps
        return destination
