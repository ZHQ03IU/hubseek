import json
from typing import Optional
from openai import AsyncOpenAI
from dataclasses import dataclass


@dataclass
class SearchStrategy:
    """AI-generated search strategy."""
    keywords: list[str]
    topics: list[str]
    language: Optional[str]
    min_stars: int
    exclude_keywords: list[str]


@dataclass
class ProjectRecommendation:
    """AI-generated project recommendation."""
    rank: int
    name: str
    full_name: str
    url: str
    stars: int
    last_update: str
    summary_zh: str
    pros: list[str]
    cons: list[str]
    verdict: str


@dataclass
class AnalysisResult:
    """AI analysis result."""
    recommendations: list[ProjectRecommendation]
    comparison_table: str


# System prompt for generating search strategy
SEARCH_STRATEGY_PROMPT = """你是一个 GitHub 项目搜索专家。
用户会用自然语言描述他们想找的项目（可能是中文）。
你需要将用户需求中的每个核心概念转换为英文关键词。

输出格式：
{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "topics": [],
  "language": null,
  "min_stars": 0,
  "exclude_keywords": []
}

关键规则：
- keywords: 根据查询复杂度决定数量（1-4个）。简单查询用少量关键词，复杂查询才用多个。
  原则：关键词越少，搜索结果越多；只保留最能区分该项目的核心词。

  示例：
  - "markdown转简历" -> ["markdown", "resume"]  （2个就够，加更多反而漏项目）
  - "Python爬虫框架" -> ["python", "scraper"]
  - "多被告法律判决预测" -> ["legal", "judgment", "prediction", "multi-defendant"]  （4个都是核心概念）
  - "React状态管理" -> ["react", "state"]

- topics: 始终为空数组 []
- language: 始终为 null
- min_stars: 始终为 0
- exclude_keywords: 始终为空数组 []

只返回 JSON，不要其他文字。"""


# System prompt for analyzing and recommending projects
ANALYSIS_PROMPT = """你是一个 GitHub 项目分析专家。
根据用户需求和项目信息，选出最符合要求的 3-5 个项目。

你需要分析每个项目的：
1. 是否符合用户需求
2. 项目的优缺点
3. 项目的活跃度和维护状态
4. 文档质量和易用性

输出 JSON 格式：
{
  "recommendations": [
    {
      "rank": 1,
      "name": "项目名",
      "full_name": "owner/repo",
      "url": "GitHub链接",
      "stars": 1234,
      "last_update": "2024-01-15",
      "summary_zh": "中文简介（2-3句话，说明项目功能和特点）",
      "pros": ["优点1", "优点2", "优点3"],
      "cons": ["缺点1", "缺点2"],
      "verdict": "一句话总结是否推荐"
    }
  ],
  "comparison_table": "Markdown格式的对比表格，包含项目名、Star数、语言、最后更新、一句话评价"
}

注意：
- summary_zh 必须是中文
- pros 和 cons 用中文
- verdict 用中文
- comparison_table 用 Markdown 格式，中文
- 按照匹配度排序，最匹配的排在前面
- 如果项目明显不符合需求，不要包含在推荐中

只返回 JSON，不要其他文字。"""


class AIAnalyzer:
    """AI analyzer using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini"
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    async def generate_search_strategy(self, user_query: str) -> SearchStrategy:
        """
        Generate search strategy from natural language query.
        Uses JSON mode for structured output.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SEARCH_STRATEGY_PROMPT},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        return SearchStrategy(
            keywords=data.get("keywords", []),
            topics=data.get("topics", []),
            language=data.get("language"),
            min_stars=data.get("min_stars", 0),
            exclude_keywords=data.get("exclude_keywords", [])
        )

    async def analyze_projects(
        self,
        user_query: str,
        projects: list[dict]
    ) -> AnalysisResult:
        """
        Analyze projects and generate recommendations.
        Uses JSON mode for structured output.
        """
        # Prepare project information for AI
        projects_info = []
        for i, project in enumerate(projects, 1):
            info = f"""
项目 {i}:
- 名称: {project['full_name']}
- 描述: {project.get('description', '无')}
- Star 数: {project.get('stars', 0)}
- Fork 数: {project.get('forks', 0)}
- 语言: {project.get('language', '未知')}
- 最后更新: {project.get('last_update', '未知')}
- 许可证: {project.get('license', '未知')}
- Topics: {', '.join(project.get('topics', []))}
- README 摘要:
{project.get('readme', '无')[:1500]}
"""
            projects_info.append(info)

        user_message = f"""用户需求: {user_query}

候选项目信息:
{''.join(projects_info)}

请分析这些项目，选出最符合用户需求的 3-5 个项目，并给出详细的中文分析。"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Parse recommendations
        recommendations = []
        for rec in data.get("recommendations", []):
            recommendations.append(ProjectRecommendation(
                rank=rec.get("rank", 0),
                name=rec.get("name", ""),
                full_name=rec.get("full_name", ""),
                url=rec.get("url", ""),
                stars=rec.get("stars", 0),
                last_update=rec.get("last_update", ""),
                summary_zh=rec.get("summary_zh", ""),
                pros=rec.get("pros", []),
                cons=rec.get("cons", []),
                verdict=rec.get("verdict", "")
            ))

        return AnalysisResult(
            recommendations=recommendations,
            comparison_table=data.get("comparison_table", "")
        )
