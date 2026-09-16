import json
import logging
import os
import re
from collections.abc import AsyncIterator, Iterable
from pathlib import PurePosixPath
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger(__name__)

MAX_FILES = 12
MAX_FILE_CHARS = 6_000
MAX_SOURCE_CHARS = 19_000
PROMPT_CHAR_LIMIT = 24_000

MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "go.mod", "cargo.toml",
    "gemfile", "composer.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
}
ENTRYPOINT_NAMES = {
    "main.py", "app.py", "server.py", "index.js", "index.ts", "main.js", "main.ts",
    "main.go", "lib.rs", "main.rs",
}
SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb",
    ".php", ".cs", ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".vue", ".svelte",
}


def parse_github_repo(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip())
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Enter a public GitHub repository URL such as https://github.com/owner/repo.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("The URL must point to a GitHub repository root.")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise ValueError("The GitHub repository URL is incomplete.")
    return owner, repo


def select_files(tree: Iterable[dict], limit: int = MAX_FILES) -> list[dict]:
    blobs = [item for item in tree if item.get("type") == "blob" and item.get("path")]

    def category(item: dict) -> tuple[int, int, str]:
        path = str(item["path"])
        name = PurePosixPath(path).name.lower()
        suffix = PurePosixPath(path).suffix.lower()
        depth = path.count("/")
        size = int(item.get("size") or 0)
        if name.startswith("readme"):
            return 0, depth, path
        if name in MANIFEST_NAMES:
            return 1, depth, path
        if name in ENTRYPOINT_NAMES:
            return 2, depth, path
        if suffix in SOURCE_SUFFIXES:
            return 3, -size, path
        return 9, depth, path

    candidates = [item for item in blobs if category(item)[0] < 9]
    candidates.sort(key=category)
    return candidates[:limit]


def build_roast_prompt(repo: str, files: list[tuple[str, str]]) -> str:
    instructions = (
        f"Roast the public GitHub repository {repo}. Be sharp, funny, specific, and technically correct. "
        "Use short paragraphs. Point to concrete code and explain the real engineering problem behind each joke. "
        "Do not invent files or behavior. End with exactly one final line in the format SCORE: n/10, where n is an integer."
    )
    sections: list[str] = []
    used = 0
    for path, content in files[:MAX_FILES]:
        remaining = MAX_SOURCE_CHARS - used
        if remaining <= 0:
            break
        clipped = content[: min(MAX_FILE_CHARS, remaining)]
        sections.append(f"\n--- {path} ---\n{clipped}")
        used += len(clipped)
    prompt = instructions + "\n\nRepository files:" + "".join(sections)
    return prompt[:PROMPT_CHAR_LIMIT]


def build_fix_prompt(repo: str, roast: str, files: list[tuple[str, str]]) -> str:
    instructions = (
        f"Fix the worst technical problem identified in this roast of {repo}. "
        "Return only a valid unified diff that can be applied with git apply. "
        "Keep the patch focused and do not change unrelated code.\n\nRoast:\n" + roast[:4_000]
    )
    sections: list[str] = []
    used = 0
    source_budget = 17_000
    for path, content in files[:MAX_FILES]:
        remaining = source_budget - used
        if remaining <= 0:
            break
        clipped = content[: min(MAX_FILE_CHARS, remaining)]
        sections.append(f"\n--- {path} ---\n{clipped}")
        used += len(clipped)
    return (instructions + "\n\nRepository files:" + "".join(sections))[:PROMPT_CHAR_LIMIT]


def parse_score(text: str) -> int | None:
    matches = re.findall(r"(?im)^SCORE:\s*(10|[0-9])/10\s*$", text)
    return int(matches[-1]) if matches else None


def llm_base_url() -> str:
    configured = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()
    if endpoint_id:
        return f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1"
    raise RuntimeError("Set LLM_BASE_URL or RUNPOD_ENDPOINT_ID before requesting a roast.")


async def stream_chat(prompt: str) -> AsyncIterator[str]:
    api_key = os.getenv("RUNPOD_API_KEY", "")
    if not api_key:
        raise RuntimeError("RUNPOD_API_KEY is not set.")
    url = f"{llm_base_url()}/chat/completions"
    payload = {
        "model": os.getenv("LLM_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct"),
        "messages": [
            {"role": "system", "content": "You are a concise senior software engineer with a dry sense of humor."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7, "max_tokens": 1_500, "stream": True,
    }
    timeout = httpx.Timeout(180.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST", url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        ) as response:
            if response.is_error:
                body = (await response.aread()).decode(errors="replace")
                raise RuntimeError(f"RunPod returned HTTP {response.status_code}: {body}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                if not data:
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"RunPod returned an invalid stream event: {data}") from exc
                if not isinstance(parsed, dict):
                    continue
                choices = parsed.get("choices")
                if choices == []:
                    logger.info("RunPod stream usage: %s", parsed.get("usage"))
                    continue
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    continue
                choice = choices[0]
                if choice.get("finish_reason") is not None:
                    break
                delta = choice.get("delta")
                if not isinstance(delta, dict):
                    continue
                token = delta.get("content")
                if token:
                    yield token


async def fetch_repository(repo_url: str) -> tuple[str, list[tuple[str, str]]]:
    owner, repo_name = parse_github_repo(repo_url)
    repo = f"{owner}/{repo_name}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        metadata = await client.get(f"https://api.github.com/repos/{repo}")
        if metadata.is_error:
            raise RuntimeError(f"GitHub returned HTTP {metadata.status_code}: {metadata.text}")
        branch = metadata.json()["default_branch"]
        tree_response = await client.get(
            f"https://api.github.com/repos/{repo}/git/trees/{quote(branch, safe='')}", params={"recursive": "1"}
        )
        if tree_response.is_error:
            raise RuntimeError(f"GitHub returned HTTP {tree_response.status_code}: {tree_response.text}")
        chosen = select_files(tree_response.json().get("tree", []))
        files: list[tuple[str, str]] = []
        for item in chosen:
            path = str(item["path"])
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{quote(branch, safe='')}/{quote(path, safe='/')}"
            response = await client.get(raw_url)
            if response.is_success:
                files.append((path, response.text[:MAX_FILE_CHARS]))
        if not files:
            raise RuntimeError("GitHub returned no readable repository files.")
    return repo, files
