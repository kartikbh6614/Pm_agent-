"""
Figma Connector - extracts wireframe context from Figma designs
"""
import re
import json
import time
import hashlib
from pathlib import Path
import requests
from typing import Optional

_SCRIPT_DIR = Path(__file__).parent.parent


class FigmaConnector:
    BASE_URL = "https://api.figma.com/v1"
    _CACHE_DIR = _SCRIPT_DIR / ".figma_cache"

    def __init__(self, access_token: str):
        self.headers = {"X-Figma-Token": access_token}

    # ─── Cache ────────────────────────────────────────────────────────────────

    def _cache_path(self, file_key: str, node_id: Optional[str]) -> Path:
        key = f"{file_key}:{node_id or 'full'}"
        h = hashlib.md5(key.encode()).hexdigest()[:12]
        self._CACHE_DIR.mkdir(exist_ok=True)
        return self._CACHE_DIR / f"{h}.json"

    def _load_cache(self, file_key: str, node_id: Optional[str]) -> Optional[dict]:
        p = self._cache_path(file_key, node_id)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def _save_cache(self, file_key: str, node_id: Optional[str], data: dict) -> None:
        p = self._cache_path(file_key, node_id)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─── URL Parsing ──────────────────────────────────────────────────────────

    def parse_url(self, figma_url: str) -> tuple[str, Optional[str]]:
        node_pattern = r"figma\.com/design/([^/]+)/[^?]+\?node-id=([^&\s]+)"
        file_pattern = r"figma\.com/design/([^/?\s]+)"
        m = re.search(node_pattern, figma_url)
        if m:
            return m.group(1), m.group(2).replace("-", ":")
        m = re.search(file_pattern, figma_url)
        if m:
            return m.group(1), None
        raise ValueError(
            f"Could not parse Figma URL: {figma_url}\n"
            "Expected: https://figma.com/design/<key>/Name?node-id=1-2"
        )

    # ─── API ──────────────────────────────────────────────────────────────────

    def _get(self, url: str, params: dict = None) -> requests.Response:
        """GET with 15s timeout and up to 3 retries on 429."""
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            except requests.exceptions.Timeout:
                raise RuntimeError(
                    "Figma API timed out (15s). Check your internet or use a specific ?node-id= URL."
                )
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 10
                print(f"\n  [Figma] Rate limited — waiting {wait}s (attempt {attempt + 1}/3)...", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("Figma API returned 429 after 3 retries. Wait a minute and try again.")

    def _get_file(self, file_key: str, depth: int = 1) -> dict:
        return self._get(f"{self.BASE_URL}/files/{file_key}", params={"depth": depth}).json()

    def _get_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        return self._get(
            f"{self.BASE_URL}/files/{file_key}/nodes",
            params={"ids": ",".join(node_ids)},
        ).json()

    # ─── Main ─────────────────────────────────────────────────────────────────

    def extract_design_context(self, figma_url: str) -> dict:
        file_key, node_id = self.parse_url(figma_url)

        cached = self._load_cache(file_key, node_id)
        if cached:
            return cached

        if node_id:
            nodes_data = self._get_nodes(file_key, [node_id])
            file_name = nodes_data.get("name", "Unknown")
            last_modified = nodes_data.get("lastModified", "Unknown")
            node_doc = nodes_data.get("nodes", {}).get(node_id, {}).get("document", {})
            screens = [node_doc] if node_doc else []
            target_name = node_doc.get("name", "Unknown")
        else:
            file_data = self._get_file(file_key, depth=1)
            file_name = file_data.get("name", "Unknown")
            last_modified = file_data.get("lastModified", "Unknown")
            frame_ids = self._collect_frame_ids(file_data.get("document", {}))[:4]
            screens = []
            for i in range(0, len(frame_ids), 2):
                batch = frame_ids[i:i + 2]
                try:
                    nd = self._get_nodes(file_key, batch)
                    for fid in batch:
                        doc = nd.get("nodes", {}).get(fid, {}).get("document")
                        if doc:
                            screens.append(doc)
                except Exception:
                    pass
                if i + 2 < len(frame_ids):
                    time.sleep(0.5)
            target_name = "Full File"

        result = {
            "file_name": file_name,
            "last_modified": last_modified,
            "file_key": file_key,
            "node_id": node_id,
            "target_name": target_name,
            "screens": [self._parse_screen(s) for s in screens],
        }
        self._save_cache(file_key, node_id, result)
        return result

    # ─── Extraction ───────────────────────────────────────────────────────────

    def _collect_frame_ids(self, document: dict) -> list[str]:
        ids = []
        for page in document.get("children", []):
            for child in page.get("children", []):
                if child.get("type") in ("FRAME", "COMPONENT", "GROUP"):
                    nid = child.get("id", "")
                    if nid:
                        ids.append(nid)
        return ids

    def _parse_screen(self, node: dict) -> dict:
        return {
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "width": node.get("absoluteBoundingBox", {}).get("width"),
            "height": node.get("absoluteBoundingBox", {}).get("height"),
            "all_text": self._collect_all_text(node),
            "interactive_elements": self._find_interactive(node),
            "components": self._extract_components(node),
        }

    def _extract_components(self, node: dict, depth: int = 0, max_depth: int = 3) -> list:
        if depth >= max_depth:
            return []
        result = []
        for child in node.get("children", []):
            node_type = child.get("type", "")
            name = child.get("name", "")
            item = {"name": name, "type": node_type}
            if child.get("characters"):
                item["text"] = child["characters"]
            name_lower = name.lower()
            if any(k in name_lower for k in ("button", "btn", "cta", "link", "tab", "menu",
                                              "input", "field", "toggle", "nav", "dropdown")):
                item["is_interactive"] = True
            if child.get("children"):
                children = self._extract_components(child, depth + 1, max_depth)
                if children:
                    item["children"] = children
            result.append(item)
        return result

    def _collect_all_text(self, node: dict) -> list[str]:
        texts = []
        if node.get("characters"):
            texts.append(node["characters"].strip())
        for child in node.get("children", []):
            texts.extend(self._collect_all_text(child))
        return [t for t in texts if t]

    def _find_interactive(self, node: dict) -> list[str]:
        interactive = []
        keywords = ("button", "btn", "cta", "link", "tab", "nav", "input", "field",
                    "search", "toggle", "submit", "login", "signup", "back", "next",
                    "continue", "cancel", "close", "upload", "dropdown")

        def walk(n: dict):
            name = n.get("name", "").lower()
            if any(k in name for k in keywords):
                interactive.append(n.get("name", ""))
            for child in n.get("children", []):
                walk(child)

        walk(node)
        return list(dict.fromkeys(interactive))

    def _get_fill_color(self, node: dict) -> Optional[str]:
        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID":
                c = fill.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                return f"#{r:02x}{g:02x}{b:02x}"
        return None

    # ─── Format for LLM ───────────────────────────────────────────────────────

    def format_for_prompt(self, ctx: dict) -> str:
        lines = [
            f"FILE: {ctx['file_name']}",
            f"TARGET: {ctx['target_name']}",
            f"SCREENS: {len(ctx['screens'])}",
            "",
        ]

        for i, screen in enumerate(ctx["screens"], 1):
            lines.append(f"── SCREEN {i}: {screen['name']} ──")
            if screen["width"] and screen["height"]:
                lines.append(f"   Size: {int(screen['width'])}×{int(screen['height'])}px")
            if screen["all_text"]:
                lines.append("   Text:")
                for t in screen["all_text"][:8]:
                    lines.append(f"     • {t}")
            if screen["interactive_elements"]:
                lines.append("   Interactive:")
                for el in screen["interactive_elements"][:6]:
                    lines.append(f"     → {el}")
            if screen["components"]:
                lines.append("   Components:")
                lines.append(self._format_components(screen["components"], indent=4))
            lines.append("")

        result = "\n".join(lines)
        return result[:1500] + "\n...[truncated]" if len(result) > 1500 else result

    def _format_components(self, components: list, indent: int = 0) -> str:
        lines = []
        prefix = " " * indent
        for c in components:
            interactive = " ★" if c.get("is_interactive") else ""
            line = f"{prefix}- [{c['type']}] {c['name']}{interactive}"
            if c.get("text"):
                line += f': "{c["text"][:60]}"'
            lines.append(line)
            if c.get("children"):
                lines.append(self._format_components(c["children"], indent + 2))
        return "\n".join(lines)
