"""Various format-specific cleanup routines."""

import os
import re
import mmap
import struct
from typing import Union, Tuple

from arxiv.base import logging

from ...domain import FileType, UserFile, Workspace, Code
from ..util.unmacify import unmacify
from .base import BaseChecker
from .file_type import InferFileType

logger = logging.getLogger(__name__)

# Types of embedded content
PHOTOSHOP = 'Photoshop'
PREVIEW = 'Preview'
THUMBNAIL = 'Thumbnail'

EOF_MARKER = re.compile(br'^%%EOF$')
"""Marker for end of Postscript file."""

LB_MARKER = re.compile(rb'^(II\*\000|MM\000\*)')
"""Marker for TIFF image - little or big endian."""

# TODO: This needs more context. -- Erick 2019-06-07
PATTERN = re.compile(rb'Thumbnail:|BeginPreview|BeginPhotoshop|'
                     rb'BeginFont|BeginResource: font',
                     re.DOTALL | re.IGNORECASE | re.MULTILINE)
"""[ needs info ]"""

# TODO: This needs more context. -- Erick 2019-06-07
PS_BEGIN = re.compile(b'^%!PS-')
"""[ needs info ]"""


# Error codes and message.
BACKUP_FILE: Code = 'backup_file'

NONCOMPLIANT_TIFF: Code = 'noncompliant_tiff'
NONCOMPLIANT_TIFF_MESSAGE = "Non-compliant attached TIFF removed from '%s'"

POSTSCRIPT_HEADER_REPAIRED: Code = 'postscript_header_repaired'
POSTSCRIPT_HEADER_MESSAGE = ("File '%s' did not have proper Postscript header,"
                             " repaired to '%s'.")

POSTSCRIPT_PREVIEW_STRIP_FAILED: Code = 'postscript_preview_stripping_failed'
POSTSCRIPT_PREVIEW_STRIPPED: Code = 'postscript_preview_stripped'

POSTSCRIPT_REPAIRED: Code = 'postscript_file_repaired'
POSTSCRIPT_REPAIRED_MESSAGE = "Repaired Postscript file '%s': %s"
POSTSCRIPT_REPAIR_ATTEMPTED_MESSAGE = \
    "Attempted repairs on Postscript file '%s': %s"


class UnMacify(BaseChecker):
    """UnMac-ifies files."""

    def check_HTML(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """UnMac-ify HTML files."""
        unmacify(workspace, u_file)
        return u_file

    def check_PC(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """UnMac-ify PC files."""
        unmacify(workspace, u_file)
        return u_file

    def check_MAC(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """UnMac-ify mac files."""
        unmacify(workspace, u_file)
        return u_file

    def check(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """If file is identified as core TeX type then we need to unmacify."""
        if u_file.file_type.is_tex_type:
            unmacify(workspace, u_file)
            # TODO: Check if TeX source file contains raw Postscript
            _extract_uu(workspace, u_file)
        return u_file


# TODO: this needs more context -- Erick 2019-06-07
class RepairDOSEPSFiles(BaseChecker):
    """Repair DOS EPS files."""

    FAILED_STRIP_PREVIEW: Code = 'strip_preview_failed'
    FAILED_STRIP_PREVIEW_MESSAGE = "Failed to strip TIFF preview"
    LEADING_PREVIEW_MESSAGE = "Leading TIFF preview stripped."
    LEADING_PREVIEW_STRIPPED: Code = 'leading_tiff_preview_stripped'
    TRAILING_PREVIEW_MESSAGE = "Trailing TIFF preview stripped."
    TRAILING_PREVIEW_STRIPPED: Code = 'trailing_tiff_preview_stripped'

    def check_DOS_EPS(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """[ needs info ]"""
        u_file, fixed = _repair_dos_eps(workspace, u_file)
        if fixed:
            # stripped TIFF
            if 'leading' in fixed:
                workspace.add_warning(u_file, self.LEADING_PREVIEW_STRIPPED,
                                      self.LEADING_PREVIEW_MESSAGE)
            if 'trailing' in fixed:
                workspace.add_warning(u_file, self.TRAILING_PREVIEW_STRIPPED,
                                      self.TRAILING_PREVIEW_MESSAGE)
        else:
            workspace.add_warning(u_file, self.FAILED_STRIP_PREVIEW,
                                  self.FAILED_STRIP_PREVIEW_MESSAGE)
            u_file, _ = _repair_postscript(workspace, u_file)
        return u_file


# TODO: this needs more context -- Erick 2019-06-07
# TODO: Sets type to postscript regardless of what happens in check_postscript.
# Should we at least warn? Or should we try to check to see if type failed
# turned to postscript after fixing up file in check_postscript?
# TODO: Find example and test.
class CleanupPostScript(BaseChecker):
    """Checks and cleanup for postscript files."""

    PS = re.compile(r'\.e?psi?$', re.IGNORECASE)

    def check_POSTSCRIPT(self, workspace: Workspace,
                         u_file: UserFile) -> UserFile:
        """
        [ needs info ]

        Check postscript for unwanted inclusions and inspect unidentified files
        that appear to be Postscript.
        """
        unmacify(workspace, u_file)
        return _check_postscript(workspace, u_file, "")

    def check_PS_PC(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        """
        Repair poscript for PS PC files.

        Seeing very few of this type in recent submissions.
        leer.eps header repaired to: %!PS-Adobe-2.0 EPSF-2.0
        """
        u_file, _ = _repair_postscript(workspace, u_file)
        return u_file

    def check_FAILED(self, workspace: Workspace, u_file: UserFile) \
            -> UserFile:
        if self.PS.search(u_file.name):
            u_file = _check_postscript(workspace, u_file, "")
        return u_file


# TODO: looks like the strip_tiff case is not fully implemented here.
# -- Erick 2019-06-07
def _check_postscript(workspace: Workspace, u_file: UserFile,
                      tiff_flag: Union[str, None]) -> UserFile:
    """
    Check Postscript file for unwanted inclusions.

    Calls 'strip_preview' to preview, thumbnails, and photoshop.

    Calls 'strip_tif' to remove non-compliant embedded TIFF bitmaps.

    This set of routines (strip_preview, strip_tiff) may modify file by
    removing offending preview/thumbnail/photoshop/tiff bitmap.

    This routine also deals with detecting imbedded fonts in Postscript
    files.

    """
    # This code had the incorrect type specified and never actually ran.
    # Cleans up Postscript files file extraneous characters that cause
    # failure to identify file as Postscript.
    if u_file.file_type == FileType.FAILED:
        # This code has been not executing for many years. May have
        # resulted in more admin interventions to manually fix.
        u_file, hdr = _repair_postscript(workspace, u_file)
        workspace.add_warning(u_file, POSTSCRIPT_HEADER_REPAIRED,
                              POSTSCRIPT_HEADER_MESSAGE % (u_file.path, hdr))

    # Determine whether Postscript file contains preview, photoshop. fonts,
    # or resource.

    # Scan Postscript file
    workspace.log.info(f"Check Postscript: '{u_file.name}'")

    # Check whether file contains '\r\n' sequence
    with workspace.open(u_file, 'rb', buffering=0) as f, \
            mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as s:

        # Search file for embedded preview markers.
        # Typeshed incorrectly restricts arguments to ``re`` functions to
        # ``AnyStr`` (just bytes and str). Looks like there is a PR that tries
        # to fix this, but unclear whether/when it will be merged:
        # https://github.com/python/typeshed/pull/3014
        results = PATTERN.findall(s)    # type: ignore

        if results:
            for match in results:
                if match == b'BeginPhotoshop':
                    u_file = _strip_preview(workspace, u_file, PHOTOSHOP)
                elif match == b'BeginPreview':
                    u_file = _strip_preview(workspace, u_file, PREVIEW)
                elif match == b'Thumbnail:':
                    u_file = _strip_preview(workspace, u_file, THUMBNAIL)

    # TODO: Scan Postscript file for embedded fonts - need seperate ticket
    # We warn when user includes standard system fonts in their
    # Postscript files.
    # TODO: Check for TIFF (need another ticket to tackle this task)
    tiff_found = 0  # Some search of file for TIFF markers
    if tiff_found:
        u_file = _strip_tiff(workspace, u_file)
    return u_file


CASE_1 = re.compile(rb'^\%*\004\%\!')
CASE_2 = re.compile(rb'^\%\%\!')
CASE_3 = re.compile(rb'.*(%!PS-Adobe-)')
HEADER_END = re.compile(b'^%!')


def _repair_postscript(workspace: Workspace, u_file: UserFile) \
        -> Tuple[UserFile, bytes]:
    """
    Repair simple corruptions at the beginning of Postscript file.

    When repairs are made existing file is replacing with repaired file.

    """
    # Check first 10 lines of Postscript file for corrupted statements
    new_path = f'{u_file.path}.fixed'
    new_file = workspace.create(new_path, file_type=u_file.file_type)

    orig_type = u_file.file_type
    first_line = b"%!\n"

    with workspace.open(u_file, 'rb', buffering=0) as infile, \
            workspace.open(new_file, 'wb', buffering=0) as outfile:

        line = b''
        fixed = False
        stripped = b""
        message = ""

        # Read each line
        for line_no, line in enumerate(infile):
            # line_no = line_no + 1

            # Attempt to identify problems and repair.
            if CASE_1.search(line):  # Special character 004.
                fixed = True
                line = CASE_1.sub(br'%!', line)
                message = ' '.join([message,
                                    "Removed carriage return from PS"
                                    "header."])

            if CASE_2.search(line):  # Extra '%' in header.
                fixed = True
                line = CASE_2.sub(br'%!', line)
                message = ' '.join([message,
                                    "Removed extra '%' from PS header."])

            if CASE_3.search(line):  # Characters in front of PS tag.
                fixed = True
                line = CASE_3.sub(br'\1', line)
                message = ' '.join([message,
                                    "Removed extraneous characters before"
                                    " PS header."])

            # QUESTION: shouldn't this do more than break if line_no > 10?
            if HEADER_END.search(line) or line_no > 10:
                # We can stop searching. If we haven't made any fixes then
                # quit.
                break

            # Keep track of what we are stripping off the front
            stripped = stripped + line

        # Done with initial cleanup
        if HEADER_END.search(line):
            if stripped:    # Save stripped content
                cleaned_filepath = f'{u_file.path}.cleaned'
                cleaned_file = workspace.create(cleaned_filepath,
                                                file_type=u_file.file_type)
                with workspace.open(cleaned_file, 'wb', buffering=0) \
                        as cleanfile:
                    cleanfile.write(stripped)
                message = ' '.join([message,
                                    "Removed extraneous lines in front of"
                                    " PS header."])

            # We are at start of Postscript file.
            outfile.write(line)
            first_line = line
        else:
            infile.seek(0, 0)   # Reset to beginnng of broken file.
            outfile.write(b"%!\n")  # Otherwise insert start indicator.

        for line in infile:     # Write out the rest of file
            outfile.write(line)

    if fixed:       # Move repaired file into place.
        new_file = workspace.replace(u_file, new_file)

        # Check that type of file has changed to 'postscript' (new) This
        # also sets file_type correctly for subsequent processing.
        InferFileType().check_UNKNOWN(workspace, new_file)
        check_type = new_file.file_type

        # Make note of the repair.
        if orig_type != check_type and check_type == FileType.POSTSCRIPT:
            lm = POSTSCRIPT_REPAIRED_MESSAGE % (new_file.name, message)
        else:
            lm = POSTSCRIPT_REPAIR_ATTEMPTED_MESSAGE % (new_file.name, message)

        workspace.add_warning(new_file, POSTSCRIPT_REPAIRED, lm)
        return new_file, first_line[0:75]

    workspace.delete(new_file)  # Cleanup.
    return u_file, first_line[0:75]


def _strip_preview(workspace: Workspace, u_file: UserFile,
                   what_to_strip: str) -> UserFile:
    """
    Remove embedded preview from Postscript file.

    Parameters
    ----------
    workspace : :class:`.Workspace`
        The upload workspace in which we are working.
    u_file : :class:`.UserFile`
        The file from which to strip embedded TIFF bitmaps.
    what_to_strip : str
        The type of inclusion that we are seeking to remove [Thumbnail,
        Preview, Photoshop]

    """
    workspace.log.info(f"Strip embedded '{what_to_strip}' from file"
                  f" '{u_file.name}'.")

    # Set start and end delimiters of preview.
    # TODO: we could even define these earlier, outside method scope.
    if what_to_strip == PHOTOSHOP:
        start_re = re.compile(b'^%BeginPhotoshop')
        end_re = re.compile(b'^%EndPhotoshop')
    elif what_to_strip == PREVIEW:
        start_re = re.compile(b'^%%BeginPreview')
        end_re = re.compile(b'^%%EndPreview')
    elif what_to_strip == THUMBNAIL:
        start_re = re.compile(b'Thumbnail')
        # Removed the ``^`` from ``^%%EndData``, since the examples have
        # %%EndData inline.
        end_re = re.compile(b'%%EndData')

    # Open a file to store stripped contents
    new_path = f'{u_file.path}.stripped'
    new_file = workspace.create(new_path, file_type=u_file.file_type)

    workspace.log.info(f"File: {u_file.name} in dir {u_file.dir} save to "
                  f"{new_file.name} at {u_file.path}")
    # Default is to retain all lines
    retain = True
    strip_warning = ''

    with workspace.open(u_file, 'rb') as infile, \
            workspace.open(new_file, 'wb') as outfile:

        for line_no, line in enumerate(infile):
            # Check line for start pattern
            if retain and start_re.search(line):
                strip_warning = (
                    f"Unnecessary {what_to_strip} removed from"
                    f" '{u_file.name}' from line {line_no + 1}"
                )
                retain = False

            if retain:
                outfile.write(line)

            # Check for end pattern
            if not retain and end_re.search(line):
                strip_warning = " ".join([strip_warning,
                                          f"to line {line_no + 1},"])
                retain = True
                # Handle bug in certain files
                # AI bug %%EndData^M%%EndComments
                if re.search(b'.*\r%/%', line):
                    outfile.write(line)

    # Generate some warnings
    if retain and strip_warning:
        orig_size = u_file.size_bytes
        strip_size = workspace.get_size_bytes(new_file)
        new_file = workspace.replace(u_file, new_file)

        msg = (f"reduced from {orig_size} bytes to {strip_size} bytes "
               "(see http://arxiv.org/help/sizes)")
        workspace.add_warning(new_file, POSTSCRIPT_PREVIEW_STRIPPED,
                              '%s %s' % (strip_warning, msg))
        return new_file

    if strip_warning:
        msg = f"{u_file.name} had unpaired {end_re.pattern}"
        strip_warning = ' '.join([strip_warning, msg])

    workspace.delete(new_file)  # Delete failed attempt to strip Postscript.
    workspace.add_warning(u_file, POSTSCRIPT_PREVIEW_STRIP_FAILED,
                          strip_warning)
    return u_file


def _strip_tiff(workspace: Workspace, u_file: UserFile) \
        -> UserFile:
    """
    Strip non-compliant embedded TIFF bitmaps from Postscript file.

    Parameters
    ----------
    workspace : :class:`.Workspace`
        The upload workspace in which we are working.
    u_file : :class:`.UserFile`
        The file from which to strip embedded TIFF bitmaps.

    Returns
    -------
    :class:`.UserFile`

    """
    workspace.log.info(f"checking '{u_file.path}' for TIFF")
    # Check for embedded TIFF and truncate file if we find one.
    # Adobe_level2_AI5 / terminate get exec
    # %%EOF
    # II *???

    with workspace.open(u_file, 'rb+', buffering=0) as infile:
        lastnw = ""
        end = 0
        for line in infile:
            if EOF_MARKER.search(line):     # Find Postscript EOF
                pos = infile.tell()
                next_bytes = infile.readline(4)

                # Locate start of TIFF
                if LB_MARKER.search(next_bytes):
                    end = pos
                break   # all set, we are done

            # Find TIFF marker
            if LB_MARKER.search(line):
                offset = len(line)
                end = infile.tell() - offset
                infile.seek(end, 1)

                workspace.log.info(f"No %%EOF, but truncate at {end} bytes, "
                              f"lastnonwhitespace was {lastnw} untruncated"
                              f" version moved to $scratch_file")

            # In the exception case, where Postscript %%EOF marker is not
            # detected before we detect TIFF bitmap, we will log last line
            # containing stuff before TIFF bitmap. TIFF is stripped.
            if re.search(rb'\S', line):
                lastnw = line

        if end:     # Truncate file after EOF marker
            infile.truncate(end)
            workspace.add_warning(u_file, NONCOMPLIANT_TIFF,
                                  NONCOMPLIANT_TIFF_MESSAGE % u_file.name)
    return u_file


# TODO: this is a pretty big method; could use some refactoring.
# -- Erick 2019-06-07
def _repair_dos_eps(workspace: Workspace,
                    u_file: UserFile) -> Tuple[UserFile, str]:
    """
    Look for leading/trailing TIFF bitmaps and remove them.

    ADD MORE HERE

    Parameters
    ----------
    file_obj : File
        File we are repairing.

    Returns
    -------
    str
        String message indicates that something was done and message
        details what was done.

    Notes
    -----
    DOS EPS Binary File Header

    0-3   Must be hex C5D0D3C6 (byte 0=C5).
    4-7   Byte position in file for start of PostScript language code
          section.
    8-11  Byte length of PostScript language section
    12-15 Byte position in file for start of Metafile screen
          representation.
    16-19 Byte length of Metafile section (PSize).
    20-23 Byte position of TIFF representation.
    24-27 Byte length of TIFF section.

    """
    with workspace.open(u_file, 'r+b', buffering=0) as infile:
        infile.seek(4, 0)   # Read past ESP file marker (C5D0D3C6)

        # Read header bytes we are interested in.
        header = infile.read(24)
        pb = struct.pack('24s', header)

        # Extract offsets/lengths for Postscript and TIFF.
        psoffset, pslength, _, _, tiffoffset, tifflength \
            = struct.unpack('6i', pb)

        #(f"psoffset:{psoffset} len:{pslength} tiffoffset:{tiffoffset}"
        # f"len:{tifflength}")

        if psoffset <= 0 or pslength <= 0 or tiffoffset <= 0 \
                or tifflength <= 0:
            # Encapsulated Postscript does not contain embedded TIFF.
            logger.debug('Encapsulated Postscript does not contain embedded'
                         ' TIFF.')
            return u_file, ""

        # Extract Postscript.
        if psoffset > tiffoffset:
            # Postscript follows TIFF so we will seek to Postscript and
            # extract (eliminate header and TIFF).
            infile.seek(psoffset, 0)    # Seek to postscript.
            first_line = infile.readline()  # Look for start of Postscript.

            if not PS_BEGIN.search(first_line):
                workspace.log.info(f"{u_file.path}: Couldn't find "
                              f"beginning of Postscript section")
                return u_file, ""

            new_path = f'{u_file.path}.fixed'
            new_file = workspace.create(new_path,
                                        file_type=u_file.file_type)

            with workspace.open(new_file, 'wb', buffering=0) as outfile:
                outfile.write(first_line)   # write out first line
                for line in infile:
                    outfile.write(line)

            # Move repaired file into place.
            new_file = workspace.replace(u_file, new_file)

            # Indicate we stripped header and leading TIFF
            return new_file, f"stripped {psoffset} leading bytes"

        elif psoffset < tiffoffset:
            # truncate the trailing TIFF image
            # strip off eps header leaving Postscript
            # save a copy of original file before we hack it to death
            backup_path = f'{u_file.path}.original'
            backup_file = workspace.copy(u_file, backup_path)

            # Let's get rid of TIFF first
            infile.seek(tiffoffset, 0)
            offset = infile.tell()
            infile.truncate(offset)     # truncate TIFF
            infile.seek(psoffset, 0)    # Seek to postscript
            first_line = infile.readline()  # Look for start of Postscript.

            if not PS_BEGIN.search(first_line):
                workspace.log.info(f"{u_file.path}: Couldn't find beginning of"
                              " Postscript section")

                workspace.delete(backup_file)  # Delete backup file.
                return u_file, ""

            fixed_file = workspace.create(f'{u_file.path}.fixed',
                                          file_type=u_file.file_type)

            with workspace.open(fixed_file, 'wb', buffering=0) as outfile:
                outfile.write(first_line)
                for line in infile:
                    outfile.write(line)

            # Move repaired file into place.
            fixed_file = workspace.replace(u_file, fixed_file)

            # Add warning about backup file we created.
            msg = (f"Modified file {u_file.public_path}."
                   f"Saving original to {backup_file.public_path}."
                   f"You may delete this file.")
            workspace.add_warning(backup_file, BACKUP_FILE, msg)

            # Indicate we stripped header and trailing TIFF.
            ret_msg = (f"stripped trailing tiff at {tiffoffset} bytes "
                       f"and {psoffset} leading bytes")
            return fixed_file, ret_msg
        return u_file, ""


# TODO: implement this!
def _extract_uu(workspace: Workspace, u_file: UserFile) -> None:
    """Extract uuencode content from file."""
    workspace.log.info(f'Looking for uu attachment in {u_file.name} of type'
                  f' {u_file.file_type.value}.')
    workspace.log.info("I'm sorry Dave I'm afraid I can't do that. uu extract not"
                  " implemented YET.")
