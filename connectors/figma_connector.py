"""
Figma Connector - extracts full wireframe context from Figma designs
Handles frames, components, text labels, annotations, flow descriptions
"""
import re
import json
import hashlib
from pathlib import Path
import requests
from typing import Optional


class FigmaConnector:
    BASE_URL = "https://api.figma.com/v1"
    _CACHE_DIR = Path(".figma_cache")

    def __init__(self, access_token: str):
        self.headers = {"X-Figma-Token": access_token}

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
        """
        Extract file_key and optional node_id from a Figma URL.
        Supports:
          - figma.com/design/<key>/Name?node-id=1-2   → specific frame
          - figma.com/design/<key>/Name               → whole file
        """
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
            "Expected format: https://figma.com/design/<key>/Name?node-id=1-2"
        )

    # ─── API Calls ────────────────────────────────────────────────────────────

    def _get_file(self, file_key: str, depth: int = 3) -> dict:
        url = f"{self.BASE_URL}/files/{file_key}"
        resp = requests.get(url, headers=self.headers, params={"depth": depth})
        resp.raise_for_status()
        return resp.json()

    def _get_file_meta(self, file_key: str) -> dict:
        """Lightweight fetch — only top-level metadata (name, lastModified). Much faster."""
        return self._get_file(file_key, depth=1)

    def _get_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        url = f"{self.BASE_URL}/files/{file_key}/nodes"
        resp = requests.get(url, headers=self.headers, params={"ids": ",".join(node_ids)})
        resp.raise_for_status()
        return resp.json()

    def _get_comments(self, file_key: str) -> list[dict]:
        """Fetch design comments/annotations."""
        url = f"{self.BASE_URL}/files/{file_key}/comments"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("comments", [])
        return []

    # ─── Main Entry Point ─────────────────────────────────────────────────────

    def extract_design_context(self, figma_url: str) -> dict:
        """
        Given a Figma URL, return full wireframe context:
        - File name, last modified
        - All frames / screens found
        - UI component tree with text, types, visibility
        - Designer annotations/comments
        """
        file_key, node_id = self.parse_url(figma_url)

        cached = self._load_cache(file_key, node_id)
        if cached:
            return cached

        comments = self._get_comments(file_key)

        if node_id:
            # Specific frame requested — only fetch lightweight metadata + the node itself
            meta = self._get_file_meta(file_key)
            file_name = meta.get("name", "Unknown")
            last_modified = meta.get("lastModified", "Unknown")
            nodes_data = self._get_nodes(file_key, [node_id])
            node_doc = nodes_data.get("nodes", {}).get(node_id, {}).get("document", {})
            screens = [node_doc] if node_doc else []
            target_name = node_doc.get("name", "Unknown")
        else:
            # Full file needed — fetch at depth=3 to get all frames
            file_data = self._get_file(file_key, depth=3)
            file_name = file_data.get("name", "Unknown")
            last_modified = file_data.get("lastModified", "Unknown")
            document = file_data.get("document", {})
            screens = self._collect_all_frames(document)
            target_name = "Full File"

        result = {
            "file_name": file_name,
            "last_modified": last_modified,
            "file_key": file_key,
            "node_id": node_id,
            "target_name": target_name,
            "screens": [self._parse_screen(s) for s in screens],
            "comments": self._parse_comments(comments),
        }
        self._save_cache(file_key, node_id, result)
        return result

    # ─── Frame / Screen Extraction ────────────────────────────────────────────

    def _collect_all_frames(self, document: dict) -> list[dict]:
        """Collect top-level FRAME nodes across all pages."""
        frames = []
        for page in document.get("children", []):
            for child in page.get("children", []):
                if child.get("type") in ("FRAME", "COMPONENT", "GROUP"):
                    frames.append(child)
        return frames

    def _parse_screen(self, node: dict) -> dict:
        """Parse a single frame/screen into structured data."""
        return {
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "width": node.get("absoluteBoundingBox", {}).get("width"),
            "height": node.get("absoluteBoundingBox", {}).get("height"),
            "background": self._get_fill_color(node),
            "components": self._extract_components(node),
            "all_text": self._collect_all_text(node),
            "interactive_elements": self._find_interactive(node),
        }

    def _extract_components(self, node: dict, depth: int = 0, max_depth: int = 5) -> list:
        """Recursively extract UI components with meaningful info."""
        if depth >= max_depth:
            return []
        result = []
        for child in node.get("children", []):
            node_type = child.get("type", "")
            name = child.get("name", "")
            visible = child.get("visible", True)

            item = {
                "name": name,
                "type": node_type,
                "visible": visible,
            }

            # Capture text content
            if child.get("characters"):
                item["text"] = child["characters"]

            # Capture style hints
            if node_type == "TEXT":
                style = child.get("style", {})
                item["font_size"] = style.get("fontSize")
                item["font_weight"] = style.get("fontWeight")

            # Capture component instance name
            if node_type == "INSTANCE":
                item["component"] = child.get("name", "")

            # Capture interaction hints from name
            name_lower = name.lower()
            if any(k in name_lower for k in ("button", "btn", "cta", "link", "tab", "menu", "icon", "input", "field", "toggle", "checkbox", "radio", "dropdown", "nav")):
                item["is_interactive"] = True

            # Recurse
            if child.get("children"):
                children = self._extract_components(child, depth + 1, max_depth)
                if children:
                    item["children"] = children

            result.append(item)
        return result

    def _collect_all_text(self, node: dict) -> list[str]:
        """Collect all text strings from a node tree."""
        texts = []
        if node.get("characters"):
            texts.append(node["characters"].strip())
        for child in node.get("children", []):
            texts.extend(self._collect_all_text(child))
        return [t for t in texts if t]

    def _find_interactive(self, node: dict) -> list[str]:
        """Find elements that look like interactive UI elements."""
        interactive = []
        keywords = ("button", "btn", "cta", "link", "tab", "nav", "input",
                    "field", "search", "toggle", "checkbox", "radio",
                    "dropdown", "select", "submit", "login", "signup", "back",
                    "next", "continue", "cancel", "close", "open", "upload")

        def walk(n: dict):
            name = n.get("name", "").lower()
            if any(k in name for k in keywords):
                interactive.append(n.get("name", ""))
            for child in n.get("children", []):
                walk(child)

        walk(node)
        return list(dict.fromkeys(interactive))  # deduplicate, preserve order

    def _get_fill_color(self, node: dict) -> Optional[str]:
        fills = node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "SOLID":
                c = fill.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                return f"#{r:02x}{g:02x}{b:02x}"
        return None

    def _parse_comments(self, comments: list) -> list[dict]:
        """Extract designer annotations from Figma comments."""
        return [
            {
                "author": c.get("user", {}).get("handle", ""),
                "text": c.get("message", ""),
                "resolved": c.get("resolved_at") is not None,
            }
            for c in comments
            if c.get("message", "").strip()
        ]

    # ─── Format for LLM Prompt ────────────────────────────────────────────────

    def format_for_prompt(self, ctx: dict) -> str:
        """Convert extracted design context to a rich text prompt."""
        lines = [
            f"FILE: {ctx['file_name']}",
            f"LAST MODIFIED: {ctx['last_modified']}",
            f"TARGET: {ctx['target_name']}",
            f"SCREENS FOUND: {len(ctx['screens'])}",
            "",
        ]

        for i, screen in enumerate(ctx["screens"], 1):
            lines.append(f"── SCREEN {i}: {screen['name']} ({screen['type']}) ──")
            if screen["width"] and screen["height"]:
                lines.append(f"   Size: {int(screen['width'])}×{int(screen['height'])}px")

            # All text found in the screen
            if screen["all_text"]:
                lines.append("   Text content:")
                for t in screen["all_text"][:15]:  # cap to 15 items
                    lines.append(f"     • {t}")

            # Interactive elements
            if screen["interactive_elements"]:
                lines.append("   Interactive elements:")
                for el in screen["interactive_elements"][:10]:
                    lines.append(f"     → {el}")

            # Component structure (top level)
            if screen["components"]:
                lines.append("   Component structure:")
                lines.append(self._format_components(screen["components"], indent=4))

            lines.append("")

        # Designer annotations
        if ctx["comments"]:
            lines.append("── DESIGNER ANNOTATIONS ──")
            for c in ctx["comments"]:
                status = "[resolved]" if c["resolved"] else "[open]"
                lines.append(f"   {status} {c['author']}: {c['text']}")
            lines.append("")

        result = "\n".join(lines)
        # Hard cap: keep prompt fast — truncate to 3000 chars
        if len(result) > 3000:
            result = result[:3000] + "\n...[truncated for speed]"
        return result

    def _format_components(self, components: list, indent: int = 0) -> str:
        lines = []
        prefix = " " * indent
        for c in components:
            visibility = "" if c.get("visible", True) else " [hidden]"
            interactive = " ★" if c.get("is_interactive") else ""
            line = f"{prefix}- [{c['type']}] {c['name']}{visibility}{interactive}"
            if c.get("text"):
                line += f': "{c["text"][:80]}"'
            lines.append(line)
            if c.get("children"):
                lines.append(self._format_components(c["children"], indent + 2))
        return "\n".join(lines)
