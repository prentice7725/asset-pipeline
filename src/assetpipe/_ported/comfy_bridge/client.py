from __future__ import annotations

import json
import logging
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..errors import ExternalServiceError

logger = logging.getLogger(__name__)


class ComfyClient:
    def __init__(
        self,
        base_url: str,
        request_timeout: float = 30,
        execution_timeout: float = 1800,
        poll_interval: float = 1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.execution_timeout = execution_timeout
        self.poll_interval = poll_interval

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: bytes | None = None,
        content_type: str | None = None,
        timeout: float | None = None,
    ) -> bytes:
        headers = {"Content-Type": content_type} if content_type else {}
        request = Request(self.base_url + path, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout or self.request_timeout) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ExternalServiceError(f"ComfyUI returned HTTP {exc.code} for {path}: {detail[:1200]}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ExternalServiceError(f"ComfyUI request {method} {path} failed: {exc}") from exc

    def _json(self, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        raw = self._request(
            path,
            method=method,
            payload=payload,
            content_type="application/json" if payload is not None else None,
        )
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExternalServiceError(f"ComfyUI returned invalid JSON for {path}.") from exc

    def check_connection(self) -> dict[str, Any]:
        stats = self._json("/system_stats")
        if not isinstance(stats, dict) or not isinstance(stats.get("system"), dict):
            raise ExternalServiceError("ComfyUI /system_stats response has an unexpected format.")
        return stats

    def list_models(self, folder: str) -> list[str]:
        """Return model filenames from ComfyUI's live model list for one folder."""
        result = self._json(f"/models/{folder}")
        names: list[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, str):
                names.append(value)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for key in ("name", "filename", "models"):
                    if key in value:
                        collect(value[key])

        collect(result)
        return sorted(set(names))

    def upload_image(self, image_path: Path) -> str:
        if not image_path.is_file():
            raise ExternalServiceError(f"Input image does not exist: {image_path}")
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ExternalServiceError(f"Cannot read input image '{image_path}': {exc}") from exc
        boundary = "----pixelpipe" + uuid.uuid4().hex
        filename = f"pixelpipe_{uuid.uuid4().hex}_{image_path.name}"
        content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
        body = prefix + image_bytes + suffix
        # Upload uses multipart rather than the JSON helper.
        raw = self._request(
            "/upload/image",
            method="POST",
            payload=body,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExternalServiceError("ComfyUI returned invalid JSON after image upload.") from exc
        uploaded = result.get("name") if isinstance(result, dict) else None
        if not isinstance(uploaded, str) or not uploaded:
            raise ExternalServiceError(f"ComfyUI did not confirm the uploaded image: {result}")
        subfolder = result.get("subfolder", "")
        return f"{subfolder}/{uploaded}" if subfolder else uploaded

    def queue_prompt(self, prompt: dict[str, Any], client_id: str) -> str:
        result = self._json("/prompt", method="POST", body={"prompt": prompt, "client_id": client_id})
        if not isinstance(result, dict):
            raise ExternalServiceError(f"ComfyUI returned an unexpected queue response: {result}")
        if result.get("node_errors"):
            raise ExternalServiceError(f"ComfyUI rejected workflow nodes: {result['node_errors']}")
        prompt_id = result.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ExternalServiceError(f"ComfyUI did not return a prompt id: {result}")
        return prompt_id

    def wait_for_outputs(self, prompt_id: str, output_nodes: tuple[str, ...]) -> list[dict[str, Any]]:
        deadline = time.monotonic() + self.execution_timeout
        last_state: str | None = None
        while time.monotonic() < deadline:
            history = self._json(f"/history/{prompt_id}")
            entry = history.get(prompt_id) if isinstance(history, dict) else None
            if isinstance(entry, dict):
                status = entry.get("status", {})
                status_str = status.get("status_str") if isinstance(status, dict) else None
                messages = status.get("messages", []) if isinstance(status, dict) else []
                if status_str and status_str != last_state:
                    logger.info("ComfyUI prompt %s status: %s", prompt_id, status_str)
                    last_state = status_str
                if status_str in {"error", "failed"}:
                    details = json.dumps(messages, ensure_ascii=False)
                    raise ExternalServiceError(f"ComfyUI execution failed for prompt {prompt_id}: {details[:2000]}")
                if isinstance(status, dict) and status.get("completed") is True:
                    outputs = entry.get("outputs", {})
                    collected: list[dict[str, Any]] = []
                    selected_nodes = output_nodes or tuple(outputs.keys())
                    for node_id in selected_nodes:
                        node_output = outputs.get(node_id, {}) if isinstance(outputs, dict) else {}
                        if not isinstance(node_output, dict):
                            continue
                        for output_key in ("images", "gifs", "videos", "audio"):
                            assets = node_output.get(output_key, [])
                            for asset in assets if isinstance(assets, list) else []:
                                if isinstance(asset, dict) and isinstance(asset.get("filename"), str):
                                    collected.append(asset)
                    if not collected:
                        raise ExternalServiceError(
                            f"ComfyUI prompt {prompt_id} completed but produced no images at the configured output nodes."
                        )
                    return collected
            time.sleep(self.poll_interval)
        raise ExternalServiceError(
            f"ComfyUI prompt {prompt_id} did not finish within {self.execution_timeout:g} seconds."
        )

    def download_image(self, image: dict[str, Any], destination: Path) -> None:
        self.download_asset(image, destination)
        if not destination.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ExternalServiceError(f"ComfyUI output '{image['filename']}' was not a PNG image.")

    def download_asset(self, asset: dict[str, Any], destination: Path) -> None:
        params = urlencode(
            {
                "filename": asset["filename"],
                "subfolder": asset.get("subfolder", ""),
                "type": asset.get("type", "output"),
            }
        )
        data = self._request(f"/view?{params}")
        suffix = destination.suffix.lower()
        if not data:
            raise ExternalServiceError(f"ComfyUI output '{asset['filename']}' was empty.")
        if suffix == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ExternalServiceError(f"ComfyUI output '{asset['filename']}' was not a PNG image.")
        if suffix == ".mp4" and b"ftyp" not in data[:32]:
            raise ExternalServiceError(f"ComfyUI output '{asset['filename']}' did not contain an MP4 file signature.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
