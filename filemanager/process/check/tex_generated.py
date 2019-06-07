"""Check for TeX-generated files."""

import os
import re
from arxiv.base import logging

from ...domain import FileType, UploadedFile, UploadWorkspace
from .base import BaseChecker

logger = logging.getLogger(__name__)


class RemoveTeXGeneratedFiles(BaseChecker):
    """
    Check for TeX processed output files (log, aux, blg, dvi, ps, pdf, etc).

    Detect naming conflict, warn, remove offending files.
    """

    TEX_PRODUCED = re.compile(r'(.+)\.(log|aux|out|blg|dvi|ps|pdf)$',
                              re.IGNORECASE)

    def check(self, workspace: UploadWorkspace, u_file: UploadedFile) -> None:
        """Check for and remove TeX processing files."""
        if self.TEX_PRODUCED.search(u_file.name):
            base_path, name = os.path.split(u_file.path)
            base, _ = os.path.splitext(name)


            tex_file = os.path.join(base_path, f'{base}.tex')
            ucase_tex_file = os.path.join(base_path, f'{base}.TEX')
            if workspace.exists(tex_file, ucase_tex_file):
                # Potential conflict / corruption by including TeX generated
                # files in submission.
                workspace.remove(u_file,
                                 f"Removed file '{u_file.name}' due to name"
                                 " conflict.")


class DisallowDVIFiles(BaseChecker):
    """
    Check for DVI files in the source, and generate an error if found.

    If dvi file is present we ask for TeX source. Do we need to do this is TeX
    was also included???????
    """

    ERROR_MSG = ('%s is a TeX-produced DVI file. Please submit the TeX source'
                 ' instead.')

    def check_DVI(self, workspace: UploadWorkspace,
                  u_file: UploadedFile) -> None:
        if not u_file.is_ancillary:
            workspace.add_error(u_file, self.ERROR_MSG % u_file.name)