"""GitHub API 工具模块."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def fetch_repo_info(owner: str, repo: str) -> dict | None:
    """获取指定 GitHub 仓库的基本信息.

    Args:
        owner: 仓库所有者（用户名或组织名）.
        repo: 仓库名称.

    Returns:
        包含 stars, forks, description, language, topics 的字典；
        若请求失败则返回 None.

    Raises:
        ValueError: 当 owner 或 repo 为空时抛出.
    """
    if not owner or not repo:
        raise ValueError("owner 和 repo 不能为空")

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("获取仓库 %s/%s 失败: %s", owner, repo, e)
        return None

    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "description": data.get("description", ""),
        "language": data.get("language", ""),
        "topics": data.get("topics", []),
    }
