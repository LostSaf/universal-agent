"""
tools/tools.py — All tools available to the universal agent
"""

import os
import json
import subprocess
import tempfile
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime


# ── Tool implementations ──────────────────────────────────────────────────────

def fetch_page(url: str) -> dict:
    """Fetch a URL and return cleaned text + links."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; UniversalAgent/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        text = "\n".join(
            line for line in soup.get_text(separator="\n", strip=True).splitlines()
            if line.strip()
        )[:8000]
        links = [
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if urlparse(urljoin(url, a["href"])).scheme in ("http", "https")
        ][:20]
        return {"url": url, "content": text, "links": links}
    except Exception as e:
        return {"url": url, "error": str(e)}


def search_web(query: str) -> dict:
    """Search DuckDuckGo and return results."""
    try:
        params = {"q": query, "format": "json", "no_html": 1}
        resp = requests.get(
            "https://api.duckduckgo.com/", params=params,
            headers={"User-Agent": "UniversalAgent/1.0"}, timeout=10
        )
        data = resp.json()
        results = []
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", "")
            })
        for topic in data.get("RelatedTopics", [])[:6]:
            if "Text" in topic and "FirstURL" in topic:
                results.append({
                    "title": topic["Text"][:80],
                    "snippet": topic["Text"],
                    "url": topic["FirstURL"]
                })
        return {"query": query, "results": results or [{"snippet": "No results. Try fetch_page with a direct URL."}]}
    except Exception as e:
        return {"query": query, "error": str(e)}


def run_code(code: str, language: str = "python") -> dict:
    """Execute code in a subprocess and return stdout/stderr."""
    try:
        suffix = ".py" if language == "python" else ".sh"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(code)
            tmp_path = f.name
        cmd = ["python3", tmp_path] if language == "python" else ["bash", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        os.unlink(tmp_path)
        return {
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000],
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Code execution timed out (15s limit)"}
    except Exception as e:
        return {"error": str(e)}


def read_file(path: str) -> dict:
    """Read a local file and return its contents."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(8000)
        return {"path": path, "content": content}
    except Exception as e:
        return {"path": path, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to a local file (creates or overwrites)."""
    try:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"path": path, "bytes_written": len(content)}
    except Exception as e:
        return {"path": path, "error": str(e)}


def list_files(directory: str = ".") -> dict:
    """List files in a directory."""
    try:
        entries = []
        for name in sorted(os.listdir(directory)):
            full = os.path.join(directory, name)
            entries.append({
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None
            })
        return {"directory": directory, "entries": entries}
    except Exception as e:
        return {"directory": directory, "error": str(e)}


def get_datetime() -> dict:
    """Return the current date and time."""
    now = datetime.now()
    return {
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A")
    }


# ── Tool definitions for Claude API ──────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": "Search the web using DuckDuckGo. Use to discover relevant URLs and quick facts before fetching full pages.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"]
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch a web page and extract its readable content and links. Use after search_web to read full articles or pages.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full URL to fetch"}},
            "required": ["url"]
        }
    },
    {
        "name": "run_code",
        "description": "Execute Python or bash code locally and return stdout/stderr. Use for calculations, data processing, or generating files programmatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to execute"},
                "language": {"type": "string", "enum": ["python", "bash"], "description": "Language (default: python)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a local file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path to read"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a local file with the given content. Use to save results, reports, or generated data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "List files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"directory": {"type": "string", "description": "Directory path (default: current dir)"}},
            "required": []
        }
    },
    {
        "name": "get_datetime",
        "description": "Get the current date and time.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(name: str, inputs: dict) -> str:
    fn_map = {
        "search_web": lambda i: search_web(i["query"]),
        "fetch_page": lambda i: fetch_page(i["url"]),
        "run_code": lambda i: run_code(i["code"], i.get("language", "python")),
        "read_file": lambda i: read_file(i["path"]),
        "write_file": lambda i: write_file(i["path"], i["content"]),
        "list_files": lambda i: list_files(i.get("directory", ".")),
        "get_datetime": lambda i: get_datetime(),
    }
    fn = fn_map.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(fn(inputs), ensure_ascii=False)
