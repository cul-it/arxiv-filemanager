from enum import Enum


class FileType(Enum):
    """Known file types."""

    UNKNOWN = 'UNKNOWN'
    ABORT = 'ABORT'
    FAILED = 'FAILED'
    ALWAYS_IGNORE = 'ALWAYS_IGNORE'
    INPUT = 'INPUT'
    BIBTEX = 'BIBTEX'
    POSTSCRIPT = 'POSTSCRIPT'
    DOS_EPS = 'DOS_EPS'
    PS_FONT = 'PS_FONT'
    PS_PC = 'PS_PC'
    IMAGE = 'IMAGE'
    ANIM = 'ANIM'
    HTML = 'HTML'
    PDF = 'PDF'
    DVI = 'DVI'
    NOTEBOOK = 'NOTEBOOK'
    ODF = 'ODF'
    DOCX = 'DOCX'
    TEX = 'TEX'
    PDFTEX = 'PDFTEX'
    TEX_priority2 = 'TEX_priority2'
    TEX_AMS = 'TEX_AMS'
    TEX_priority = 'TEX_priority'
    TEX_MAC = 'TEX_MAC'
    LATEX = 'LATEX'
    LATEX2e = 'LATEX2e'
    PDFLATEX = 'PDFLATEX'
    TEXINFO = 'TEXINFO'
    MF = 'MF'
    UUENCODED = 'UUENCODED'
    ENCRYPTED = 'ENCRYPTED'
    PC = 'PC'
    MAC = 'MAC'
    CSH = 'CSH'
    SH = 'SH'
    JAR = 'JAR'
    RAR = 'RAR'
    XLSX = 'XLSX'
    COMPRESSED = 'COMPRESSED'
    ZIP = 'ZIP'
    GZIPPED = 'GZIPPED'
    BZIP2 = 'BZIP2'
    MULTI_PART_MIME = 'MULTI_PART_MIME'
    TAR = 'TAR'
    IGNORE = 'IGNORE'
    README = 'README'
    TEXAUX = 'TEXAUX'
    ABS = 'ABS'
    INCLUDE = 'INCLUDE'

    @property
    def name(self) -> str:
        """Human-readable name of the file type."""
        return FILE_NAMES.get(self, 'unknown')

    @property
    def is_tex_type(self) -> bool:
        """
        Indicate whether this is a TeX type.

        This method does some normalization prior to calling internal routine.
        """
        return self in TEX_TYPES


FILE_NAMES = {
    FileType.UNKNOWN: 'Unknown',
    FileType.ABORT: 'Immediate stop',
    FileType.FAILED: FileType.unknown,
    FileType.ALWAYS_IGNORE: 'Always ignore',
    FileType.INPUT: 'Input for (La)TeX',
    FileType.BIBTEX: FileType.BiBTeX,
    FileType.POSTSCRIPT: FileType.Postscript,
    FileType.DOS_EPS: 'DOS EPS Binary File',
    FileType.PS_FONT: 'Postscript Type 1 Font',
    FileType.PS_PC: '^D%! Postscript',
    FileType.IMAGE: 'Image (gif/jpg etc)',
    FileType.ANIM: 'Animation (mpeg etc)',
    FileType.HTML: FileType.HTML,
    FileType.PDF: FileType.PDF,
    FileType.DVI: FileType.DVI,
    FileType.NOTEBOOK: 'Mathematica Notebook',
    FileType.ODF: 'OpenDocument Format',
    FileType.DOCX: 'Microsoft DOCX',
    FileType.TEX: FileType.TEX,
    FileType.PDFTEX: FileType.PDFTEX,
    FileType.TEX_priority2:
        'TeX (with \\end or \\bye - not starting a line)',
    FileType.TEX_AMS: FileType.AMSTeX,
    FileType.TEX_priority: 'TeX (with \\end or \\bye)',
    FileType.TEX_MAC: 'TeX +macros (harv,lanl..)',
    FileType.LATEX: FileType.LaTeX,
    FileType.LATEX2e: FileType.LATEX2e,
    FileType.PDFLATEX: FileType.PDFLATEX,
    FileType.TEXINFO: FileType.Texinfo,
    FileType.MF: FileType.Metafont,
    FileType.UUENCODED: FileType.UUencoded,
    FileType.ENCRYPTED: FileType.Encrypted,
    FileType.PC: 'PC-ctrl-Ms',
    FileType.MAC: 'MAC-ctrl-Ms',
    FileType.CSH: FileType.CSH,
    FileType.SH: FileType.SH,
    FileType.JAR: 'JAR archive',
    FileType.RAR: 'RAR archive',
    FileType.XLSX: 'Microsoft XLSX',
    FileType.COMPRESSED: 'UNIX-compressed',
    FileType.ZIP: 'ZIP-compressed',
    FileType.GZIPPED: 'GZIP-compressed',
    FileType.BZIP2: 'BZIP2-compressed',
    FileType.MULTI_PART_MIME: FileType.MULTI_PART_MIME,
    FileType.TAR: 'TAR archive',
    FileType.IGNORE: ' user defined IGNORE',
    FileType.README: FileType.override,
    FileType.TEXAUX: 'TeX auxiliary',
    FileType.ABS: FileType.abstract,
    FileType.INCLUDE: ' keep'
}

TEX_TYPES = [
    FileType.LATEX,
    FileType.TEX,
    FileType.TEX_priority,
    FileType.TEX_AMS,
    FileType.TEX_MAC,
    FileType.LATEX2e,
    FileType.TEX_priority2,
    FileType.TEXINFO,
    FileType.PDFLATEX,
    FileType.PDFTEX
]