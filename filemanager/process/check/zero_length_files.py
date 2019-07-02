"""Check for and remove zero-length files."""

import os

from arxiv.base import logging

from ...domain import FileType, UploadedFile, CheckableWorkspace
from .base import BaseChecker


logger = logging.getLogger(__name__)


class ZeroLengthFileChecker(BaseChecker):
    """Checks for and removes zero-length files."""

    ZERO_LENGTH_MSG = f"File '%s' is empty (size is zero)."

    def check(self, workspace: CheckableWorkspace, u_file: UploadedFile) \
            -> UploadedFile:
        """Determine wether a file is zero-length, and remove it if so."""
        if u_file.is_empty:
            workspace.add_warning(u_file, self.ZERO_LENGTH_MSG % u_file.name,
                                  is_persistant=False)
            workspace.remove(u_file,
                             f"Removed file '{u_file.name}' [file is empty].")
        return u_file
