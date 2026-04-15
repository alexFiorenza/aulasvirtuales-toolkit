from pathlib import Path
from typing import Protocol

from aulasvirtuales.reporter import ProgressReporter


class ConversionStrategy(Protocol):
    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path: ...


class PdfToMarkdown:
    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path:
        import pymupdf4llm

        md_content = pymupdf4llm.to_markdown(str(input_path))
        out_dir = output_dir or input_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"{input_path.stem}.md"
        md_path.write_text(md_content, encoding="utf-8")
        if reporter:
            reporter.on_step("markdown", md_path)
        return md_path


class DocxToPdf:
    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path:
        from docx2pdf import convert as docx_convert

        out_dir = output_dir or input_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / f"{input_path.stem}.pdf"
        docx_convert(str(input_path), str(pdf_path))
        if reporter:
            reporter.on_step("pdf", pdf_path)
        return pdf_path


class PptxToPdf:
    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path:
        import shutil
        import subprocess

        cmd = shutil.which("libreoffice") or shutil.which("soffice")
        if not cmd:
            raise FileNotFoundError(
                "LibreOffice is required for .pptx to PDF conversion. "
                "Install it with: brew install --cask libreoffice (macOS) "
                "or apt install libreoffice (Linux)"
            )
        out_dir = output_dir or input_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [cmd, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(input_path)],
            check=True,
            capture_output=True,
        )
        pdf_path = out_dir / f"{input_path.stem}.pdf"
        if reporter:
            reporter.on_step("pdf", pdf_path)
        return pdf_path


class DocxToMarkdown:
    """DOCX -> PDF -> Markdown (chained)."""

    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path:
        pdf_path = DocxToPdf().convert(input_path, output_dir, reporter)
        return PdfToMarkdown().convert(pdf_path, output_dir, reporter)


class PptxToMarkdown:
    """PPTX -> PDF -> Markdown (chained via LibreOffice)."""

    def convert(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        reporter: ProgressReporter | None = None,
    ) -> Path:
        pdf_path = PptxToPdf().convert(input_path, output_dir, reporter)
        return PdfToMarkdown().convert(pdf_path, output_dir, reporter)


STRATEGIES: dict[tuple[str, str], ConversionStrategy] = {
    (".pdf", "md"): PdfToMarkdown(),
    (".docx", "md"): DocxToMarkdown(),
    (".pptx", "md"): PptxToMarkdown(),
    (".docx", "pdf"): DocxToPdf(),
    (".pptx", "pdf"): PptxToPdf(),
}


def convert(
    input_path: Path,
    to_format: str,
    output_dir: Path | None = None,
    reporter: ProgressReporter | None = None,
) -> Path:
    """Single entry point — dispatches to the right strategy."""
    ext = input_path.suffix.lower()
    strategy = STRATEGIES.get((ext, to_format))
    if strategy is None:
        raise ValueError(f"Conversion from {ext} to {to_format} is not supported")
    return strategy.convert(input_path, output_dir, reporter)


# ---------------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------------

def pdf_to_markdown(pdf_path: Path) -> str:
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf_path))


def convert_and_save(pdf_path: Path, output_dir: Path | None = None) -> Path:
    return PdfToMarkdown().convert(pdf_path, output_dir)


def docx_to_pdf(docx_path: Path, output_dir: Path | None = None) -> Path:
    return DocxToPdf().convert(docx_path, output_dir)


def pptx_to_pdf(pptx_path: Path, output_dir: Path | None = None) -> Path:
    return PptxToPdf().convert(pptx_path, output_dir)
