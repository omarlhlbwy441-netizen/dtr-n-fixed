"""
DTR-N GitHub Manager
نظام إدارة GitHub - استنساخ، إنشاء، رفع، ضبط الإعدادات
"""

import os
import subprocess
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import httpx

logger = logging.getLogger("dtr-n.github")

GITHUB_API = "https://api.github.com"


class GitHubManager:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.user = os.environ.get("GITHUB_USER", "omarlhlbwy441-netizen")
        self.default_repo = os.environ.get("GITHUB_REPO", "omarlhlbwy441-netizen/dtr-n")
        self.base_path = Path("/home/runner/workspace")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    async def list_repos(self) -> List[Dict]:
        """قائمة المستودعات"""
        if not self.token:
            return self._mock_repos()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{GITHUB_API}/user/repos?per_page=50&sort=updated",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    repos = resp.json()
                    return [
                        {
                            "name": r["name"],
                            "full_name": r["full_name"],
                            "description": r.get("description"),
                            "private": r["private"],
                            "url": r["html_url"],
                            "stars": r.get("stargazers_count", 0),
                            "updated_at": r.get("updated_at", ""),
                        }
                        for r in repos
                    ]
        except Exception as e:
            logger.error(f"list_repos error: {e}")
        return self._mock_repos()

    def _mock_repos(self) -> List[Dict]:
        return [
            {
                "name": "dtr-n",
                "full_name": "omarlhlbwy441-netizen/dtr-n",
                "description": "Wolf Engine v1.0 + SIND NEXUS v1.0 - AI Platform",
                "private": False,
                "url": "https://github.com/omarlhlbwy441-netizen/dtr-n",
                "stars": 0,
                "updated_at": datetime.now().isoformat(),
            }
        ]

    async def clone_repo(self, repo_url: str, target_dir: Optional[str] = None) -> Dict:
        """استنساخ مستودع"""
        try:
            # Add token to URL if GitHub
            if "github.com" in repo_url and self.token:
                repo_url = repo_url.replace(
                    "https://github.com",
                    f"https://{self.token}@github.com"
                )

            target = target_dir or repo_url.split("/")[-1].replace(".git", "")
            target_path = self.base_path / "workspace_repos" / target
            target_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["git", "clone", repo_url, str(target_path)],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"تم استنساخ المستودع في {target_path}",
                    "url": str(target_path),
                    "details": {"path": str(target_path), "output": result.stdout},
                }
            else:
                return {
                    "success": False,
                    "message": f"فشل الاستنساخ: {result.stderr[:200]}",
                    "url": None,
                    "details": {"error": result.stderr},
                }
        except Exception as e:
            logger.error(f"clone_repo error: {e}")
            return {"success": False, "message": str(e), "url": None, "details": {}}

    async def create_repo(self, name: str, description: str = "", private: bool = False, init: bool = True) -> Dict:
        """إنشاء مستودع جديد"""
        if not self.token:
            return {"success": False, "message": "لم يتم ضبط GitHub Token", "url": None, "details": {}}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "name": name,
                    "description": description,
                    "private": private,
                    "auto_init": init,
                }
                resp = await client.post(
                    f"{GITHUB_API}/user/repos",
                    headers=self._headers(),
                    json=payload
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    return {
                        "success": True,
                        "message": f"تم إنشاء المستودع {name} بنجاح",
                        "url": data.get("html_url"),
                        "details": {"clone_url": data.get("clone_url"), "id": data.get("id")},
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get("message", "فشل إنشاء المستودع"),
                        "url": None,
                        "details": data,
                    }
        except Exception as e:
            logger.error(f"create_repo error: {e}")
            return {"success": False, "message": str(e), "url": None, "details": {}}

    async def push_files(self, repo: str, commit_message: str, files: List[Dict]) -> Dict:
        """رفع الملفات إلى المستودع"""
        if not self.token:
            return {"success": False, "message": "لم يتم ضبط GitHub Token", "url": None, "details": {}}
        try:
            pushed = 0
            errors = []
            async with httpx.AsyncClient(timeout=60) as client:
                for file_obj in files:
                    file_path = file_obj["path"]
                    content = file_obj["content"]

                    # Get current file SHA if exists
                    sha = await self._get_file_sha(client, repo, file_path)

                    payload = {
                        "message": commit_message,
                        "content": base64.b64encode(content.encode()).decode(),
                    }
                    if sha:
                        payload["sha"] = sha

                    resp = await client.put(
                        f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
                        headers=self._headers(),
                        json=payload
                    )
                    if resp.status_code in (200, 201):
                        pushed += 1
                    else:
                        errors.append(f"{file_path}: {resp.json().get('message', 'unknown')}")

            if pushed > 0:
                return {
                    "success": True,
                    "message": f"تم رفع {pushed} ملف إلى {repo}",
                    "url": f"https://github.com/{repo}",
                    "details": {"pushed": pushed, "errors": errors},
                }
            else:
                return {
                    "success": False,
                    "message": f"فشل رفع الملفات: {'; '.join(errors[:3])}",
                    "url": None,
                    "details": {"errors": errors},
                }
        except Exception as e:
            logger.error(f"push_files error: {e}")
            return {"success": False, "message": str(e), "url": None, "details": {}}

    async def push_current_workspace(self, commit_message: str = "DTR-N: Auto-push updated system") -> Dict:
        """رفع مساحة العمل الحالية إلى GitHub"""
        try:
            ws = self.base_path
            result = subprocess.run(
                ["git", "-C", str(ws), "add", "-A"],
                capture_output=True, text=True, timeout=30
            )
            result2 = subprocess.run(
                ["git", "-C", str(ws), "commit", "-m", commit_message],
                capture_output=True, text=True, timeout=30
            )
            if "nothing to commit" in result2.stdout:
                return {
                    "success": True,
                    "message": "لا يوجد تغييرات جديدة للرفع",
                    "url": f"https://github.com/{self.default_repo}",
                    "details": {},
                }

            # Set remote URL with token
            repo_url = f"https://{self.token}@github.com/{self.default_repo}.git"
            subprocess.run(
                ["git", "-C", str(ws), "remote", "set-url", "origin", repo_url],
                capture_output=True, text=True, timeout=10
            )

            result3 = subprocess.run(
                ["git", "-C", str(ws), "push", "origin", "main"],
                capture_output=True, text=True, timeout=60
            )
            if result3.returncode == 0:
                return {
                    "success": True,
                    "message": f"تم رفع التحديثات إلى {self.default_repo}",
                    "url": f"https://github.com/{self.default_repo}",
                    "details": {"output": result3.stdout},
                }
            else:
                return {
                    "success": False,
                    "message": f"فشل الرفع: {result3.stderr[:200]}",
                    "url": None,
                    "details": {"error": result3.stderr},
                }
        except Exception as e:
            logger.error(f"push_workspace error: {e}")
            return {"success": False, "message": str(e), "url": None, "details": {}}

    async def _get_file_sha(self, client: httpx.AsyncClient, repo: str, file_path: str) -> Optional[str]:
        try:
            resp = await client.get(
                f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
                headers=self._headers()
            )
            if resp.status_code == 200:
                return resp.json().get("sha")
        except Exception:
            pass
        return None
