from pathlib import Path


def pdf_to_markdown(pdf_path: Path) -> str:
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf_path))


def convert_and_save(pdf_path: Path, output_dir: Path | None = None) -> Path:
    md_content = pdf_to_markdown(pdf_path)
    out_dir = output_dir or pdf_path.parent
    md_path = out_dir / f"{pdf_path.stem}.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")
    return md_path


def docx_to_pdf(docx_path: Path, output_dir: Path | None = None) -> Path:
    """Convert a .docx file to PDF using docx2pdf."""
    from docx2pdf import convert

    out_dir = output_dir or docx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{docx_path.stem}.pdf"
    convert(str(docx_path), str(pdf_path))
    return pdf_path


def pptx_to_pdf(pptx_path: Path, output_dir: Path | None = None) -> Path:
    """Convert a .pptx file to PDF using LibreOffice headless."""
    import shutil
    import subprocess

    cmd = shutil.which("libreoffice") or shutil.which("soffice")
    if not cmd:
        raise FileNotFoundError(
            "LibreOffice is required for .pptx to PDF conversion. "
            "Install it with: brew install --cask libreoffice (macOS) "
            "or apt install libreoffice (Linux)"
        )
    out_dir = output_dir or pptx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [cmd, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
        check=True,
        capture_output=True,
    )
    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    return pdf_path
