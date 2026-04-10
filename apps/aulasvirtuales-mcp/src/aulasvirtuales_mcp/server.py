import os
import tempfile
from pathlib import Path
from fastmcp import FastMCP

from aulasvirtuales.auth import get_credentials, login, get_token, save_token, is_session_valid
from aulasvirtuales.client import MoodleClient
from aulasvirtuales.downloader import download_file, get_resource_files
from aulasvirtuales.config import get_download_dir

mcp = FastMCP("AulasVirtuales")

def _get_client() -> MoodleClient:
    username = os.environ.get("MOODLE_USERNAME")
    password = os.environ.get("MOODLE_PASSWORD")
    
    token = get_token()
    if token and is_session_valid(token):
        return MoodleClient(token)
    
    if username and password:
        token = login(username, password)
        save_token(token)
        return MoodleClient(token)
        
    creds = get_credentials()
    if creds:
        token = login(creds[0], creds[1])
        save_token(token)
        return MoodleClient(token)
        
    raise RuntimeError(
        "No Moodle credentials found. Please set MOODLE_USERNAME and "
        "MOODLE_PASSWORD environment variables, or run 'aulasvirtuales login' locally via CLI."
    )

@mcp.tool()
def get_courses():
    """List enrolled courses."""
    client = _get_client()
    return client.get_courses()

@mcp.tool()
def get_course_resources(course_id: int):
    """List sections and resources of a course."""
    client = _get_client()
    return client.get_course_contents(course_id)

@mcp.tool()
def get_upcoming_events(course_id: int | None = None):
    """Show upcoming events for a specific course or across all courses."""
    client = _get_client()
    return client.get_upcoming_events(course_id)

@mcp.tool()
def get_grades(course_id: int):
    """Show grades and feedback for a course."""
    client = _get_client()
    return client.get_grades(course_id)

@mcp.tool()
def get_forums(course_id: int):
    """List forums in a course."""
    client = _get_client()
    return client.get_forums(course_id)

@mcp.tool()
def get_forum_discussions(forum_id: int, limit: int = 10):
    """List discussions in a forum."""
    client = _get_client()
    return client.get_forum_discussions(forum_id, limit)

@mcp.tool()
def get_discussion_posts(discussion_id: int):
    """Show messages in a forum discussion."""
    client = _get_client()
    return client.get_discussion_posts(discussion_id)

@mcp.tool()
def download_resource_to_disk(course_id: int, resource_id: int) -> str:
    """Download a resource (file or folder) from a course and save it to the local disk.
    If the MCP server is remote, it will save it on the remote disk.
    If working with an LLM chat context, consider using read_resource_content instead.
    """
    client = _get_client()
    sections = client.get_course_contents(course_id)
    
    resource = None
    for section in sections:
        for r in section.resources:
            if r.id == resource_id:
                resource = r
                break
                
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in course {course_id}.")
        
    if resource.module not in ("resource", "folder"):
        raise ValueError(f"Resource type '{resource.module}' is not downloadable.")
        
    file_urls = get_resource_files(client._http, resource.id, resource.module)
    if not file_urls:
        raise ValueError("No downloadable files found.")
        
    dest_dir = get_download_dir()
    downloaded_paths = []
    for url in file_urls:
        path = download_file(client._http, url, dest_dir)
        downloaded_paths.append(str(path))
        
    return f"Successfully downloaded to {get_download_dir()}:\n" + "\n".join(downloaded_paths)

@mcp.tool()
def read_resource_content(course_id: int, resource_id: int) -> str:
    """Download a resource temporarily and extract its text/markdown content.
    Returns the markdown string instead of persisting the file. This is best for letting the LLM read course documents like PDFs or DOCXs.
    """
    client = _get_client()
    sections = client.get_course_contents(course_id)
    
    resource = None
    for section in sections:
        for r in section.resources:
            if r.id == resource_id:
                resource = r
                break
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in course {course_id}.")
    if resource.module not in ("resource", "folder", "assign"):
         raise ValueError(f"Resource type '{resource.module}' cannot be converted to text.")
         
    file_urls = get_resource_files(client._http, resource.id, resource.module)
    if not file_urls:
        raise ValueError("No downloadable files found for this resource.")
        
    output_parts = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_dir = Path(temp_dir)
        for url in file_urls:
            path = download_file(client._http, url, dest_dir)
            try:
                suffix = path.suffix.lower()
                if suffix == ".pdf":
                    from aulasvirtuales.converter import convert_and_save
                    md_path = convert_and_save(path, dest_dir)
                    output_parts.append(f"--- File: {path.name} ---\n" + md_path.read_text(encoding="utf-8"))
                elif suffix == ".docx":
                    from aulasvirtuales.converter import docx_to_pdf, convert_and_save
                    pdf_path = docx_to_pdf(path, dest_dir)
                    md_path = convert_and_save(pdf_path, dest_dir)
                    output_parts.append(f"--- File: {path.name} ---\n" + md_path.read_text(encoding="utf-8"))
                elif suffix == ".pptx":
                    from aulasvirtuales.converter import pptx_to_pdf, convert_and_save
                    pdf_path = pptx_to_pdf(path, dest_dir)
                    md_path = convert_and_save(pdf_path, dest_dir)
                    output_parts.append(f"--- File: {path.name} ---\n" + md_path.read_text(encoding="utf-8"))
                elif suffix in (".txt", ".md", ".csv", ".json", ".xml", ".html"):
                    output_parts.append(f"--- File: {path.name} ---\n" + path.read_text(encoding='utf-8'))
                else:
                    output_parts.append(f"--- File: {path.name} ---\n[Unsupported format {suffix} - Attempting raw text read]\n" + path.read_text(encoding='utf-8', errors='ignore'))
            except Exception as e:
                output_parts.append(f"[Failed to extract text from {path.name}: {str(e)}]")
                
    return "\n\n".join(output_parts)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
