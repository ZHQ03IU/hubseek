import asyncio
import base64
from typing import Optional
import httpx
from dataclasses import dataclass


@dataclass
class GitHubRepo:
    """GitHub repository data."""
    name: str
    full_name: str
    description: str
    url: str
    stars: int
    forks: int
    language: Optional[str]
    topics: list[str]
    last_update: str
    readme: str
    open_issues: int
    license: Optional[str]


class GitHubClient:
    """GitHub API client with async support."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def build_search_query(
        self,
        keywords: list[str],
        topics: list[str],
        language: Optional[str] = None,
        min_stars: int = 0,
        exclude_keywords: list[str] = None
    ) -> str:
        """
        Build GitHub advanced search query.

        Example output: keyword1+keyword2+topic:topic1+stars:>=100
        """
        parts = []

        # Add keywords (search in readme and description)
        if keywords:
            for keyword in keywords:
                # Clean keyword: remove commas, extra spaces, replace space with +
                clean_keyword = keyword.strip().replace(",", "").replace(" ", "+")
                if clean_keyword:
                    parts.append(clean_keyword)

        # Add topics
        for topic in topics:
            parts.append(f"topic:{topic}")

        # Add language filter
        if language:
            parts.append(f"language:{language}")

        # Add minimum stars filter
        if min_stars > 0:
            parts.append(f"stars:>={min_stars}")

        # Add exclusions
        if exclude_keywords:
            for exclude in exclude_keywords:
                parts.append(f"-{exclude}")

        return "+".join(parts)

    async def search_repos(
        self,
        query: str,
        max_results: int = 20,
        sort: str = "stars",
        order: str = "desc"
    ) -> list[dict]:
        """Search GitHub repositories."""
        # Build URL manually to avoid httpx encoding issues
        url = f"{self.BASE_URL}/search/repositories?q={query}&sort={sort}&order={order}&per_page={max_results}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

    async def get_readme(self, owner: str, repo: str, max_chars: int = 2500) -> str:
        """Get repository README content, truncated to max_chars."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/readme"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()

                # Get content and decode from base64
                content = data.get("content", "")
                if content:
                    decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
                    # Truncate to max_chars
                    return decoded[:max_chars]
                return ""
            except Exception:
                return ""

    async def get_repo_details(
        self,
        owner: str,
        repo: str,
        readme_max_chars: int = 2500
    ) -> GitHubRepo:
        """Get detailed repository information including README."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"

        async with httpx.AsyncClient() as client:
            # Get repo info
            response = await client.get(
                url,
                headers=self.headers,
                timeout=15.0
            )
            response.raise_for_status()
            repo_data = response.json()

        # Get README concurrently
        readme = await self.get_readme(owner, repo, readme_max_chars)

        return GitHubRepo(
            name=repo_data["name"],
            full_name=repo_data["full_name"],
            description=repo_data.get("description", "") or "",
            url=repo_data["html_url"],
            stars=repo_data["stargazers_count"],
            forks=repo_data["forks_count"],
            language=repo_data.get("language"),
            topics=repo_data.get("topics", []),
            last_update=repo_data["pushed_at"],
            readme=readme,
            open_issues=repo_data["open_issues_count"],
            license=repo_data.get("license", {}).get("spdx_id") if repo_data.get("license") else None
        )

    async def get_multiple_repo_details(
        self,
        repos: list[dict],
        readme_max_chars: int = 2500,
        max_concurrent: int = 10
    ) -> list[GitHubRepo]:
        """Get details for multiple repositories concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(owner: str, repo: str) -> GitHubRepo:
            async with semaphore:
                return await self.get_repo_details(owner, repo, readme_max_chars)

        tasks = []
        for repo in repos:
            owner, name = repo["full_name"].split("/")
            tasks.append(fetch_with_semaphore(owner, name))

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def search_code(
        self,
        query: str,
        max_results: int = 20
    ) -> list[dict]:
        """
        Search GitHub code. Returns unique repositories found in code search results.
        """
        url = f"{self.BASE_URL}/search/code?q={query}&per_page={max_results}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Extract unique repositories from code results
            seen_repos = set()
            unique_repos = []
            for item in data.get("items", []):
                repo = item.get("repository", {})
                full_name = repo.get("full_name", "")
                if full_name and full_name not in seen_repos:
                    seen_repos.add(full_name)
                    unique_repos.append(repo)

            return unique_repos

    async def search_combined(
        self,
        keywords: list[str],
        topics: list[str],
        language: Optional[str] = None,
        min_stars: int = 0,
        exclude_keywords: list[str] = None,
        max_results: int = 20,
        min_repo_results: int = 5
    ) -> tuple[list[dict], str]:
        """
        Combined search: repos with progressively fewer keywords, merging all results.
        Falls back to code search if still too few results.
        """
        seen = set()
        merged = []

        def add_repos(repos):
            for repo in repos:
                full_name = repo.get("full_name", "")
                if full_name and full_name not in seen:
                    seen.add(full_name)
                    merged.append(repo)

        # Try repo search with progressively fewer keywords, accumulating results
        active_keywords = list(keywords)
        while active_keywords:
            query = self.build_search_query(
                keywords=active_keywords,
                topics=topics,
                language=language,
                min_stars=min_stars,
                exclude_keywords=exclude_keywords
            )
            results = await self.search_repos(query, max_results)
            add_repos(results)

            if len(merged) >= min_repo_results:
                break

            active_keywords = active_keywords[:-1]

        if len(merged) >= min_repo_results:
            return merged[:max_results], f"Repositories ({len(merged)} results)"

        # Still too few — fall back to code search
        code_query = "+".join(k.strip().replace(",", "").replace(" ", "+") for k in keywords if k.strip())
        try:
            code_repos = await self.search_code(code_query, max_results)
            add_repos(code_repos)
            source = f"Combined: Repos+Code = {len(merged)} unique"
        except Exception:
            source = f"Repositories only ({len(merged)} results)"

        return merged[:max_results], source
