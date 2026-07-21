"""
DTR-N Workspace Manager
نظام إدارة بيئة العمل - الملفات، البناء، المعاينة
"""

import os
import subprocess
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger("dtr-n.workspace")

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/home/runner/workspace"))

# Extensions to language mapping
LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".sh": "bash",
    ".toml": "toml",
    ".sql": "sql",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
}

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "dist", "build",
    ".cache", ".local", "dtr-n",  # ignore cloned repo to avoid recursion
}


class WorkspaceManager:
    def __init__(self):
        self.root = WORKSPACE_ROOT
        self.preview_status = {
            "status": "idle",
            "url": None,
            "logs": [],
            "error": None,
            "project_path": None,
        }
        self._preview_process = None

    def list_files(self, path: Optional[str] = None) -> List[Dict]:
        """قائمة ملفات مساحة العمل"""
        try:
            target = (self.root / path) if path else self.root
            if not target.exists():
                return []

            entries = []
            for item in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                if item.name.startswith(".") or item.name in IGNORED_DIRS:
                    continue

                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item.relative_to(self.root)),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "extension": item.suffix.lstrip(".") if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
                entries.append(entry)
            return entries
        except Exception as e:
            logger.error(f"list_files error: {e}")
            return []

    def read_file(self, path: str) -> Dict:
        """قراءة ملف من مساحة العمل"""
        try:
            target = self.root / path
            if not target.exists() or not target.is_file():
                return {"path": path, "content": "", "language": "text", "size": 0, "error": "File not found"}

            # Limit to 500KB
            size = target.stat().st_size
            if size > 512_000:
                content = target.read_bytes()[:512_000].decode("utf-8", errors="replace") + "\n... (تم اقتطاع الملف)"
            else:
                content = target.read_text(encoding="utf-8", errors="replace")

            language = LANG_MAP.get(target.suffix.lower(), "text")
            return {
                "path": path,
                "content": content,
                "language": language,
                "size": size,
            }
        except Exception as e:
            logger.error(f"read_file error: {e}")
            return {"path": path, "content": "", "language": "text", "size": 0, "error": str(e)}

    def write_file(self, path: str, content: str) -> Dict:
        """كتابة/حفظ ملف في مساحة العمل"""
        try:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"ok": True, "message": f"تم حفظ {path}"}
        except Exception as e:
            logger.error(f"write_file error: {e}")
            return {"ok": False, "message": str(e)}

    async def build_preview(self, project_path: str, build_command: Optional[str] = None, port: Optional[int] = None) -> Dict:
        """بناء مشروع للمعاينة"""
        try:
            target = self.root / project_path
            if not target.exists():
                self.preview_status = {
                    "status": "error",
                    "url": None,
                    "logs": [],
                    "error": f"المسار غير موجود: {project_path}",
                    "project_path": project_path,
                }
                return self.preview_status

            self.preview_status = {
                "status": "building",
                "url": None,
                "logs": [f"[BUILD] بدء بناء {project_path}..."],
                "error": None,
                "project_path": project_path,
            }

            # Detect project type and run appropriate build
            logs = [f"[BUILD] بدء بناء {project_path}..."]

            if (target / "package.json").exists():
                cmd = build_command or "npm run build"
                logs.append(f"[INFO] نوع المشروع: Node.js")
                logs.append(f"[CMD] {cmd}")
                result = subprocess.run(
                    cmd.split(),
                    cwd=str(target),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                logs.extend(result.stdout.split("\n")[-20:])
                if result.returncode == 0:
                    logs.append("[OK] تم البناء بنجاح ✓")
                    self.preview_status = {
                        "status": "ready",
                        "url": f"/preview/{project_path}",
                        "logs": logs,
                        "error": None,
                        "project_path": project_path,
                    }
                else:
                    logs.append(f"[ERROR] {result.stderr[:200]}")
                    self.preview_status = {
                        "status": "error",
                        "url": None,
                        "logs": logs,
                        "error": result.stderr[:500],
                        "project_path": project_path,
                    }

            elif (target / "requirements.txt").exists() or (target / "pyproject.toml").exists():
                logs.append("[INFO] نوع المشروع: Python")
                logs.append("[OK] مشروع Python جاهز للتشغيل")
                self.preview_status = {
                    "status": "ready",
                    "url": f"http://localhost:{port or 8000}",
                    "logs": logs,
                    "error": None,
                    "project_path": project_path,
                }

            elif any(target.glob("*.html")):
                logs.append("[INFO] نوع المشروع: HTML Static")
                logs.append("[OK] موقع ثابت جاهز")
                self.preview_status = {
                    "status": "ready",
                    "url": f"/preview-static/{project_path}",
                    "logs": logs,
                    "error": None,
                    "project_path": project_path,
                }

            else:
                logs.append("[WARN] نوع المشروع غير معروف")
                self.preview_status = {
                    "status": "ready",
                    "url": None,
                    "logs": logs,
                    "error": None,
                    "project_path": project_path,
                }

            return self.preview_status

        except Exception as e:
            logger.error(f"build_preview error: {e}")
            self.preview_status = {
                "status": "error",
                "url": None,
                "logs": [str(e)],
                "error": str(e),
                "project_path": project_path,
            }
            return self.preview_status

    def get_preview_status(self) -> Dict:
        return self.preview_status
