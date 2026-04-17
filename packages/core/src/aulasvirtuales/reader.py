"""Read content from non-downloadable Moodle resource types."""

import httpx

from aulasvirtuales.models import Resource, ResourceContent
from aulasvirtuales.parsers import parse_page_content, parse_url_redirect, strip_html

READABLE_MODULES = {"url", "page", "label"}


def read_resource(http: httpx.Client, resource: Resource) -> ResourceContent:
    """Return the content of a non-downloadable resource.

    Args:
        http: Authenticated HTTP client.
        resource: The resource to read. Must be url, page, or label type.

    Returns:
        ResourceContent with the extracted content.

    Raises:
        ValueError: If the module type is not supported or the URL is missing.
    """
    if resource.module == "label":
        return _read_label(resource)
    if resource.module == "url":
        return _read_url(http, resource)
    if resource.module == "page":
        return _read_page(http, resource)
    raise ValueError(
        f"Module type '{resource.module}' is not supported by read_resource(). "
        f"Readable types: {sorted(READABLE_MODULES)}"
    )


def _read_label(resource: Resource) -> ResourceContent:
    # Moodle puts label HTML in cm["name"]; cm["description"] may be absent
    content = resource.description or resource.name or ""
    return ResourceContent(
        resource_id=resource.id,
        module="label",
        content=strip_html(content),
    )


def _read_url(http: httpx.Client, resource: Resource) -> ResourceContent:
    if not resource.url:
        raise ValueError(f"Resource {resource.id} has no url.")
    response = http.get(resource.url, follow_redirects=True)
    external_url = parse_url_redirect(response.text)
    if not external_url:
        raise ValueError(f"Could not extract redirect URL from resource {resource.id}.")
    return ResourceContent(
        resource_id=resource.id,
        module="url",
        content=external_url,
    )


def _read_page(http: httpx.Client, resource: Resource) -> ResourceContent:
    if not resource.url:
        raise ValueError(f"Resource {resource.id} has no url.")
    response = http.get(resource.url, follow_redirects=True)
    return ResourceContent(
        resource_id=resource.id,
        module="page",
        content=parse_page_content(response.text),
    )
