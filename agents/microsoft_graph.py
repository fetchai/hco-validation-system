import base64
import os
from typing import Any, Dict, Optional, List
from urllib.parse import urlparse, parse_qs, quote

import requests


GRAPH_TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_DEVICE_CODE_URL_TMPL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _normalize_drive_item_id(item_id: Optional[str], drive_id: Optional[str] = None) -> Optional[str]:
    if not item_id:
        return item_id
    if "!" in item_id:
        left, right = item_id.split("!", 1)
        if drive_id is None or left.lower() == drive_id.lower():
            return right
    return item_id


def _strip_composite_item_id(item_id: Optional[str]) -> Optional[str]:
    if not item_id:
        return item_id
    if "!" in item_id:
        return item_id.split("!", 1)[1]
    return item_id


class GraphConfigError(RuntimeError):
    pass


def _base64url(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8").replace("+", "-").replace("/", "_").rstrip("=")


def share_url_to_share_id(share_url: str) -> str:
    """
    Convert a sharing URL into a Microsoft Graph shareId.
    Per Microsoft Graph docs: shareId = "u!" + base64url(shareUrl)
    """
    if not share_url:
        raise ValueError("share_url is required")
    # 1drv.ms short links sometimes fail with /shares resolution unless expanded first.
    try:
        parsed = urlparse(share_url)
        if parsed.netloc.lower().endswith("1drv.ms"):
            # Follow redirects to the final onedrive.live.com/ share URL
            resp = requests.get(share_url, allow_redirects=True, timeout=15)
            if resp.url:
                share_url = resp.url
    except Exception:
        # If expansion fails, fall back to the original URL
        pass
    return "u!" + _base64url(share_url.encode("utf-8"))


def get_app_access_token() -> str:
    # Prefer MS_* env vars (new), but also support AZURE_* (common existing setups)
    tenant_id = os.getenv("MS_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("MS_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("MS_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET")

    if not tenant_id or not client_id or not client_secret:
        raise GraphConfigError(
            "Missing MS_TENANT_ID/MS_CLIENT_ID/MS_CLIENT_SECRET (or AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET) for Graph client-credentials auth"
        )

    token_url = GRAPH_TOKEN_URL_TMPL.format(tenant_id=tenant_id)
    resp = requests.post(
        token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Token response missing access_token: {data}")
    return token


def get_delegated_access_token_from_refresh_token() -> str:
    """
    Personal OneDrive (Microsoft account) does NOT support app-only (client credentials) Graph calls.
    For personal accounts, use delegated auth + refresh token.

    Env supported:
    - MS_TENANT_ID or AZURE_TENANT_ID: for personal accounts set to 'consumers'
    - MS_CLIENT_ID or AZURE_CLIENT_ID
    - MS_CLIENT_SECRET or AZURE_CLIENT_SECRET (optional for public clients)
    - MS_REFRESH_TOKEN (or AZURE_REFRESH_TOKEN)
    """
    tenant_id = os.getenv("MS_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "consumers"
    client_id = os.getenv("MS_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
    refresh_token = os.getenv("MS_REFRESH_TOKEN") or os.getenv("AZURE_REFRESH_TOKEN")

    if not client_id or not refresh_token:
        raise GraphConfigError("Missing MS_CLIENT_ID/AZURE_CLIENT_ID or MS_REFRESH_TOKEN/AZURE_REFRESH_TOKEN for delegated auth")

    def _try_refresh(authority_tenant: str) -> str:
        token_url = GRAPH_TOKEN_URL_TMPL.format(tenant_id=authority_tenant)
        data = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            # v2 endpoint allows scope, but refresh tokens usually carry scopes; keep minimal
            "scope": "offline_access Files.ReadWrite",
        }
        # IMPORTANT:
        # For PERSONAL Microsoft accounts ("consumers") you almost always use a PUBLIC client.
        # In that case, sending a client_secret can cause 400 invalid_client.
        # Only include client_secret if explicitly requested.
        include_secret = (os.getenv("MS_DELEGATED_INCLUDE_CLIENT_SECRET") or "").strip().lower() in ("1", "true", "yes")
        if include_secret:
            client_secret = os.getenv("MS_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET")
            if client_secret:
                data["client_secret"] = client_secret

        resp = requests.post(token_url, data=data, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # Surface the real AAD error, it usually contains "invalid_grant"/"invalid_client" with explanation.
            body: Any
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise RuntimeError(f"Delegated token refresh failed: status={resp.status_code} body={body}") from e
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Refresh token flow missing access_token: {payload}")
        return token

    # First attempt: use configured tenant id
    try:
        return _try_refresh(tenant_id)
    except RuntimeError as e:
        msg = str(e)
        if "AADSTS7000012" not in msg:
            raise

        # Try common alternative authorities if tenant mismatch.
        retry_order = []
        if tenant_id != "consumers":
            retry_order.append("consumers")
        if tenant_id != "common":
            retry_order.append("common")

        last_err: Optional[Exception] = e
        for alt in retry_order:
            try:
                return _try_refresh(alt)
            except Exception as e2:
                last_err = e2
        raise last_err  # type: ignore[misc]


def get_access_token() -> str:
    """
    Prefer delegated auth when a refresh token is provided (supports personal accounts).
    Otherwise fall back to app-only client credentials (work/school accounts).
    """
    if os.getenv("MS_REFRESH_TOKEN") or os.getenv("AZURE_REFRESH_TOKEN"):
        return get_delegated_access_token_from_refresh_token()
    return get_app_access_token()


def start_device_code_flow(
    *,
    scopes: str = "offline_access Files.ReadWrite",
) -> Dict[str, Any]:
    """
    Start device code flow. Useful to bootstrap MS_REFRESH_TOKEN for personal accounts.
    """
    tenant_id = os.getenv("MS_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "consumers"
    client_id = os.getenv("MS_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
    if not client_id:
        raise GraphConfigError("Missing MS_CLIENT_ID/AZURE_CLIENT_ID for device code flow")
    url = GRAPH_DEVICE_CODE_URL_TMPL.format(tenant_id=tenant_id)
    resp = requests.post(url, data={"client_id": client_id, "scope": scopes}, timeout=30)
    resp.raise_for_status()
    return resp.json()



def graph_request(
    method: str,
    url: str,
    token: str,
    *,
    json: Any = None,
    data: Any = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
) -> requests.Response:
    hdrs = {"Authorization": f"Bearer {token}"}
    if headers:
        hdrs.update(headers)
    resp = requests.request(method, url, headers=hdrs, json=json, data=data, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        body: Any
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise requests.HTTPError(
            f"Microsoft Graph request failed: method={method} url={url} status={resp.status_code} body={body}",
            response=resp,
        ) from e
    return resp


def _search_drive_item_by_filename(drive_id: str, filename: str, token: str) -> Dict[str, Any]:
    """
    Search a drive for a file by name. Returns the first best match.
    """
    if not drive_id or not filename:
        raise ValueError("drive_id and filename are required")
    url = f"{GRAPH_BASE}/drives/{drive_id}/root/search(q='{filename}')?$select=id,name,webUrl,parentReference"
    resp = graph_request("GET", url, token)
    data = resp.json() or {}
    items = data.get("value") or []
    if not items:
        raise RuntimeError(f"Could not find any file named like '{filename}' in drive '{drive_id}'")
    # Prefer exact name match
    for it in items:
        if isinstance(it, dict) and (it.get("name") or "").lower() == filename.lower():
            return it
    return items[0]


def _search_child_item_by_filename(drive_id: str, parent_item_id: str, filename: str, token: str) -> Dict[str, Any]:
    """
    Search under a specific folder/item for a file by name.
    Returns the first best match.
    """
    if not drive_id or not parent_item_id or not filename:
        raise ValueError("drive_id, parent_item_id and filename are required")
    parent_item_id = _normalize_drive_item_id(parent_item_id, drive_id)
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{parent_item_id}/search(q='{filename}')?$select=id,name,webUrl,parentReference"
    resp = graph_request("GET", url, token)
    data = resp.json() or {}
    items = data.get("value") or []
    if not items:
        raise RuntimeError(
            f"Could not find any file named like '{filename}' under item '{parent_item_id}' in drive '{drive_id}'"
        )
    for it in items:
        if isinstance(it, dict) and (it.get("name") or "").lower() == filename.lower():
            return it
    return items[0]


def _ensure_folder_item_id(drive_item: Dict[str, Any], drive_id: str) -> str:
    """Ensure we return a folder item id. If the share URL resolves to a file, use its parentReference.id."""
    # NOTE: For shared links, Graph frequently returns composite ids like "{driveId}!{itemId}".
    # These composite ids are valid in /drives/{driveId}/items/{id} endpoints, while stripping the prefix
    # can produce 404 itemNotFound. So we keep the id exactly as returned.
    item_id = drive_item.get("id")
    if drive_item.get("folder") is not None:
        if not item_id:
            raise RuntimeError(f"Folder driveItem missing id: {drive_item}")
        return item_id
    parent = drive_item.get("parentReference") or {}
    parent_id = parent.get("id")
    if not parent_id:
        raise RuntimeError(f"DriveItem is not a folder and parentReference.id missing: {drive_item}")
    return parent_id


def resolve_share_url(share_url: str, token: str) -> Dict[str, Any]:
    """
    Resolve a "share URL" to a driveItem.

    Supports:
    - Real sharing links (e.g. 1drv.ms / Share -> Copy link) via /shares/{shareId}/driveItem
    - Excel web "open" links like:
        https://excel.cloud.microsoft/open/onedrive/?docId=...&driveId=...
      These are NOT share links, so /shares will 400. For these we attempt a /drives/{driveId}/items/{itemId} lookup.
    """
    if not share_url:
        raise ValueError("share_url is required")

    parsed = urlparse(share_url)
    qs = parse_qs(parsed.query or "")

    # Excel web "open" links: try driveId + docId item lookup
    if "excel.cloud.microsoft" in (parsed.netloc or "") and ("/open/onedrive" in (parsed.path or "")):
        drive_id = (qs.get("driveId") or [None])[0]
        doc_id = (qs.get("docId") or [None])[0]
        if drive_id and doc_id and "!" in doc_id:
            # docId format observed: <driveId>!<itemId>
            _, item_id = doc_id.split("!", 1)
            item_id = _normalize_drive_item_id(item_id, drive_id)
            url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}?$select=id,name,webUrl,parentReference,folder,file"
            try:
                resp = graph_request("GET", url, token)
                return resp.json()
            except requests.HTTPError as e:
                # Often the "itemId" in excel.cloud links is not a driveItem id → 404.
                # Some tenants also return 400 for non-driveItem IDs.
                if getattr(e.response, "status_code", None) in (400, 404):
                    excel_filename = (
                        os.getenv("HCO_EXCEL_FILE_NAME")
                        or os.getenv("EXCEL_FILE_NAME")
                        or os.getenv("MS_EXCEL_FILE_NAME")
                    )
                    if excel_filename:
                        return _search_drive_item_by_filename(drive_id, excel_filename, token)
                    # Fall back to treating the URL as a share link.
                    # (Some environments mistakenly pass excel.cloud "open" links where a share link is expected.)
                    try:
                        share_id = share_url_to_share_id(share_url)
                        share_url_api = f"{GRAPH_BASE}/shares/{share_id}/driveItem?$select=id,name,webUrl,parentReference,folder,file"
                        resp2 = graph_request("GET", share_url_api, token)
                        return resp2.json()
                    except Exception:
                        pass
                raise

        raise RuntimeError(
            "Excel link not resolvable. Please use a real OneDrive 'Share -> Copy link' URL for the Excel file, "
            "or set EXCEL_FILE_NAME (or HCO_EXCEL_FILE_NAME) to the workbook filename so the backend can search it."
        )

    # Default: treat as share link
    share_id = share_url_to_share_id(share_url)
    url = f"{GRAPH_BASE}/shares/{share_id}/driveItem?$select=id,name,webUrl,parentReference,folder,file"
    resp = graph_request("GET", url, token)
    item = resp.json()

    # If callers provide an Excel folder share link instead of a workbook link, help them out.
    # If this is a folder and an Excel filename is configured, try to locate that workbook.
    try:
        if isinstance(item, dict) and item.get("folder") is not None:
            excel_filename = (
                os.getenv("HCO_EXCEL_FILE_NAME")
                or os.getenv("EXCEL_FILE_NAME")
                or os.getenv("MS_EXCEL_FILE_NAME")
            )
            parent = item.get("parentReference") or {}
            drive_id = parent.get("driveId")
            if drive_id and excel_filename:
                folder_item_id = _normalize_drive_item_id(item.get("id"), drive_id)
                if folder_item_id:
                    return _search_child_item_by_filename(drive_id, folder_item_id, excel_filename, token)
    except Exception:
        pass

    return item


def upload_bytes_to_shared_folder(
    folder_share_url: str,
    filename: str,
    content: bytes,
    token: str,
    *,
    content_type: str = "application/octet-stream",
) -> Dict[str, Any]:
    """
    Uploads a file into a shared OneDrive/SharePoint folder using an app token.
    """
    folder_item = resolve_share_url(folder_share_url, token)
    parent = folder_item.get("parentReference") or {}
    drive_id = parent.get("driveId")
    if not drive_id:
        raise RuntimeError(f"Could not resolve driveId from folder share URL: {folder_item}")
    folder_item_id = _ensure_folder_item_id(folder_item, drive_id)
    if not drive_id or not folder_item_id:
        raise RuntimeError(f"Could not resolve driveId/itemId from folder share URL: {folder_item}")

    # Path-based addressing is sensitive to reserved URL characters.
    safe_filename = quote(filename, safe="")

    # Some shared folder resolutions can return composite IDs. We try the normalized folder item id first,
    # then retry with the raw id (if different) when Graph responds with a 400.
    raw_folder_id: Optional[str] = None
    try:
        if folder_item.get("folder") is not None:
            raw_folder_id = folder_item.get("id")
        else:
            raw_folder_id = (folder_item.get("parentReference") or {}).get("id")
    except Exception:
        raw_folder_id = None

    candidate_folder_ids = [folder_item_id]
    if raw_folder_id and raw_folder_id != folder_item_id:
        candidate_folder_ids.append(raw_folder_id)

    last_err: Optional[Exception] = None
    resp: Optional[requests.Response] = None
    for idx, candidate_id in enumerate(candidate_folder_ids):
        # Preflight: ensure the folder item exists and is accessible.
        # This makes misconfigured share URLs / invalid IDs fail with a clearer error before upload.
        folder_meta_url = f"{GRAPH_BASE}/drives/{drive_id}/items/{candidate_id}?$select=id,name,folder,webUrl,parentReference"
        graph_request("GET", folder_meta_url, token)
        put_url = f"{GRAPH_BASE}/drives/{drive_id}/items/{candidate_id}:/{safe_filename}:/content"
        try:
            resp = graph_request(
                "PUT",
                put_url,
                token,
                data=content,
                headers={"Content-Type": content_type},
                timeout=120,
            )
            last_err = None
            break
        except Exception as e:
            last_err = e
            # Only retry on the second candidate when it looks like a bad request.
            if idx == (len(candidate_folder_ids) - 1):
                break

    if last_err is not None or resp is None:
        raise last_err  # type: ignore[misc]

    upload_result = resp.json()
    
    # Get the item metadata with download URL
    item_id = _normalize_drive_item_id(upload_result.get("id"), drive_id)
    if item_id:
        try:
            metadata_url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}?$select=id,webUrl,@microsoft.graph.downloadUrl,parentReference"
            metadata_resp = graph_request("GET", metadata_url, token)
            metadata = metadata_resp.json()
            # Merge download URL into upload result
            download_url = metadata.get("@microsoft.graph.downloadUrl")
            if download_url:
                upload_result["@microsoft.graph.downloadUrl"] = download_url
        except Exception:
            # If we can't get download URL, continue with what we have
            pass
    
    return upload_result


def get_shared_folder_file_web_url(folder_share_url: str, filename: str, token: str) -> str:
    """
    Return a download URL for a file inside a shared folder, addressed by filename.
    Tries to get a direct download URL first, falls back to webUrl.
    """
    folder_item = resolve_share_url(folder_share_url, token)
    parent = folder_item.get("parentReference") or {}
    drive_id = parent.get("driveId")
    if not drive_id:
        raise RuntimeError(f"Could not resolve driveId from folder share URL: {folder_item}")
    folder_item_id = _ensure_folder_item_id(folder_item, drive_id)

    # Path-based addressing requires a trailing ":" to return metadata.
    # Request both downloadUrl and webUrl
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_item_id}:/{filename}:?$select=id,webUrl,@microsoft.graph.downloadUrl,name,parentReference"
    resp = graph_request("GET", url, token)
    data = resp.json() or {}
    
    # Try direct download URL first (if available)
    download_url = data.get("@microsoft.graph.downloadUrl")
    if download_url:
        return download_url
    
    # Fallback to webUrl
    web_url = data.get("webUrl")
    if web_url:
        return web_url
    
    # Last resort: try to construct download URL from item ID
    item_id = _normalize_drive_item_id(data.get("id"), drive_id)
    if item_id:
        try:
            return get_direct_download_url(drive_id, item_id, token)
        except Exception:
            pass
    
    raise RuntimeError("Could not resolve download URL for file in shared folder")


def get_direct_download_url(drive_id: str, item_id: str, token: str) -> str:
    """
    Get a direct download URL for a file in OneDrive.
    This URL can be used to download the file directly without authentication.
    """
    item_id = _normalize_drive_item_id(item_id, drive_id)
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}?$select=@microsoft.graph.downloadUrl,webUrl"
    resp = graph_request("GET", url, token)
    data = resp.json() or {}

    download_url = data.get("@microsoft.graph.downloadUrl")
    if download_url:
        return download_url

    web_url = data.get("webUrl")
    if web_url:
        return web_url

    return f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"


def get_download_url_from_upload_result(upload_result: Dict[str, Any], token: str) -> str:
    """
    Extract a direct download URL from an upload result.
    Tries @microsoft.graph.downloadUrl first, then constructs from item metadata.
    """
    if not isinstance(upload_result, dict):
        raise ValueError("upload_result must be a dict")

    download_url = upload_result.get("@microsoft.graph.downloadUrl")
    if download_url:
        return download_url

    parent_ref = upload_result.get("parentReference") or {}
    drive_id = parent_ref.get("driveId")
    item_id = _normalize_drive_item_id(upload_result.get("id"), drive_id)

    if drive_id and item_id:
        try:
            return get_direct_download_url(drive_id, item_id, token)
        except Exception:
            pass

    web_url = upload_result.get("webUrl")
    if web_url:
        return web_url

    raise RuntimeError("Could not determine download URL from upload result")


def get_excel_table_column_names(
    excel_share_url: str,
    table_name: str,
    token: str,
) -> List[str]:
    """
    Return the column names for a table in a shared workbook.
    """
    item = resolve_share_url(excel_share_url, token)
    parent = item.get("parentReference") or {}
    drive_id = parent.get("driveId")
    item_id = item.get("id")
    if not drive_id or not item_id:
        raise RuntimeError(f"Could not resolve driveId/itemId from excel share URL: {item}")

    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}/columns?$select=name"
    try:
        resp = graph_request("GET", url, token)
        data = resp.json() or {}
        cols = data.get("value") or []
        return [c.get("name") for c in cols if isinstance(c, dict) and c.get("name")]
    except requests.HTTPError as e:
        # Fallback: some share links yield driveItem IDs that are not usable via /drives/{driveId}/items/{itemId}.
        if getattr(e.response, "status_code", None) in (400, 404):
            try:
                share_id = share_url_to_share_id(excel_share_url)
                url_share = f"{GRAPH_BASE}/shares/{share_id}/driveItem/workbook/tables/{table_name}/columns?$select=name"
                resp_share = graph_request("GET", url_share, token)
                data_share = resp_share.json() or {}
                cols_share = data_share.get("value") or []
                return [c.get("name") for c in cols_share if isinstance(c, dict) and c.get("name")]
            except Exception:
                pass

        # Commonly happens when the resolved driveItem is a folder/non-workbook.
        if getattr(e.response, "status_code", None) in (400, 404):
            excel_filename = (
                os.getenv("HCO_EXCEL_FILE_NAME")
                or os.getenv("EXCEL_FILE_NAME")
                or os.getenv("MS_EXCEL_FILE_NAME")
            )
            if excel_filename:
                found = _search_drive_item_by_filename(drive_id, excel_filename, token)
                found_id = found.get("id")
                if found_id:
                    url2 = f"{GRAPH_BASE}/drives/{drive_id}/items/{found_id}/workbook/tables/{table_name}/columns?$select=name"
                    resp2 = graph_request("GET", url2, token)
                    data2 = resp2.json() or {}
                    cols2 = data2.get("value") or []
                    return [c.get("name") for c in cols2 if isinstance(c, dict) and c.get("name")]
        raise


def append_row_to_shared_excel_table(
    excel_share_url: str,
    table_name: str,
    values: List[Any],
    token: str,
) -> Dict[str, Any]:
    """
    Append a row to an Excel table in a shared workbook.

    IMPORTANT: the workbook must contain a table with name `table_name`.
    Recommended: create a table named 'Certificates' with headers (example):
    certificate_id, certificate_no, issue_date, company_reg_no, company_name, certificate_url
    """
    item = resolve_share_url(excel_share_url, token)
    parent = item.get("parentReference") or {}
    drive_id = parent.get("driveId")
    item_id = item.get("id")
    if not drive_id or not item_id:
        raise RuntimeError(f"Could not resolve driveId/itemId from excel share URL: {item}")

    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}/rows/add"
    body = {"index": None, "values": [values]}
    try:
        resp = graph_request("POST", url, token, json=body, headers={"Content-Type": "application/json"})
        return resp.json()
    except requests.HTTPError as e:
        if getattr(e.response, "status_code", None) in (400, 404):
            share_id = share_url_to_share_id(excel_share_url)
            url_share = f"{GRAPH_BASE}/shares/{share_id}/driveItem/workbook/tables/{table_name}/rows/add"
            resp2 = graph_request("POST", url_share, token, json=body, headers={"Content-Type": "application/json"})
            return resp2.json()
        raise


def get_excel_table_rows(
    excel_share_url: str,
    table_name: str,
    token: str,
    *,
    top: int = 5000,
) -> List[List[Any]]:
    """
    Fetch rows from an Excel table in a shared workbook.

    Returns a list of row arrays (values only).
    """
    item = resolve_share_url(excel_share_url, token)
    parent = item.get("parentReference") or {}
    drive_id = parent.get("driveId")
    item_id = item.get("id")
    if not drive_id or not item_id:
        raise RuntimeError(f"Could not resolve driveId/itemId from excel share URL: {item}")

    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}/rows?$top={top}&$select=values"
    try:
        resp = graph_request("GET", url, token)
        data = resp.json() or {}
    except requests.HTTPError as e:
        if getattr(e.response, "status_code", None) in (400, 404):
            share_id = share_url_to_share_id(excel_share_url)
            url_share = f"{GRAPH_BASE}/shares/{share_id}/driveItem/workbook/tables/{table_name}/rows?$top={top}&$select=values"
            resp2 = graph_request("GET", url_share, token)
            data = resp2.json() or {}
        else:
            raise
    out: List[List[Any]] = []
    for r in data.get("value") or []:
        if isinstance(r, dict):
            vals = r.get("values")
            # Graph returns values as [[...]] per row
            if isinstance(vals, list) and vals and isinstance(vals[0], list):
                out.append(vals[0])
    return out


def find_row_in_excel_table_by_column_value(
    excel_share_url: str,
    table_name: str,
    *,
    column_name: str,
    match_value: Any,
    token: str,
    top: int = 5000,
) -> Optional[Dict[str, Any]]:
    """
    Find the first row in an Excel table where `column_name` equals `match_value`.
    Returns a dict of {columnName: cellValue} or None.
    Excel date serial numbers are automatically converted to YYYY-MM-DD format.
    """
    from datetime import datetime, timedelta
    
    def convert_excel_date(value: Any) -> Any:
        """Convert Excel serial date number to YYYY-MM-DD string."""
        if isinstance(value, (int, float)) and value > 30000:  # Likely an Excel date serial
            try:
                excel_epoch = datetime(1899, 12, 30)
                date_obj = excel_epoch + timedelta(days=int(value))
                return date_obj.strftime('%Y-%m-%d')
            except Exception:
                return value
        return value
    
    cols = get_excel_table_column_names(excel_share_url, table_name, token)
    col_idx: Optional[int] = None
    for i, c in enumerate(cols):
        if isinstance(c, str) and c.strip().lower() == column_name.strip().lower():
            col_idx = i
            break
    if col_idx is None:
        return None

    def norm(v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    wanted = norm(match_value)
    for row in get_excel_table_rows(excel_share_url, table_name, token, top=top):
        if col_idx >= len(row):
            continue
        if norm(row[col_idx]) == wanted:
            # Map in the same order as table columns, converting Excel dates
            result: Dict[str, Any] = {}
            for i, col in enumerate(cols):
                if col:
                    cell_value = row[i] if i < len(row) else None
                    # Convert Excel dates for date-related columns
                    if col and 'date' in str(col).lower():
                        cell_value = convert_excel_date(cell_value)
                    result[str(col)] = cell_value
            return result
    return None


