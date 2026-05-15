"""
Article generator — takes raw news stories and produces
original commentary articles via the OpenAI API.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@dataclass
class Article:
    headline: str
    body: str
    meta_description: str
    tags: list[str]
    excerpt: str
    category: str
    source_title: str
    source_url: str
    source_name: str
    image_query: str = ""
    images: object = None  # image_fetcher.ArticleImages


def generate_article(story: dict, client: OpenAI, config: dict) -> Optional[Article]:
    """
    Generate a full commentary article for a single news story.
    Returns None on failure.
    """
    model = config.get("openai", {}).get("model", "gpt-4o-mini")
    temperature = config.get("openai", {}).get("temperature", 0.7)
    max_tokens = config.get("openai", {}).get("max_tokens", 2000)

    commentary_prompt = _load_prompt("commentary")
    headline_prompt = _load_prompt("headline")

    user_input = (
        f"NEWS STORY\n"
        f"Title: {story['title']}\n"
        f"Source: {story['source']}\n"
        f"Summary: {story['summary']}\n"
        f"URL: {story['url']}\n"
        f"Published: {story.get('published', 'Unknown')}"
    )

    # Step 1: Generate the article body
    try:
        body_resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": commentary_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        body = body_resp.choices[0].message.content.strip()
    except Exception:
        log.exception("Body generation failed for: %s", story["title"])
        return None

    # Step 2: Generate headline + metadata
    try:
        headline_temp = config.get("openai", {}).get("headline_temperature", 0.9)
        meta_resp = client.chat.completions.create(
            model=model,
            temperature=headline_temp,
            max_tokens=350,
            messages=[
                {"role": "system", "content": headline_prompt},
                {"role": "user", "content": body},
            ],
        )
        meta_raw = meta_resp.choices[0].message.content.strip()
    except Exception:
        log.exception("Headline generation failed for: %s", story["title"])
        return None

    headline, meta_desc, tags, excerpt, image_query = _parse_headline_response(meta_raw)

    if not headline:
        headline = story["title"]
    if not meta_desc:
        meta_desc = excerpt or body[:155]
    if not excerpt:
        excerpt = meta_desc

    return Article(
        headline=headline,
        body=body,
        meta_description=meta_desc,
        tags=tags,
        excerpt=excerpt,
        category=story.get("category", "world"),
        source_title=story["title"],
        source_url=story["url"],
        source_name=story["source"],
        image_query=image_query,
    )


def _parse_headline_response(raw: str) -> tuple[str, str, list[str], str, str]:
    headline = ""
    meta = ""
    tags: list[str] = []
    excerpt = ""
    image_query = ""

    for line in raw.splitlines():
        line = line.strip()
        upper = line.upper()
        if upper.startswith("HEADLINE:"):
            headline = line.split(":", 1)[1].strip()
        elif upper.startswith("META:"):
            meta = line.split(":", 1)[1].strip()
        elif upper.startswith("TAGS:"):
            raw_tags = line.split(":", 1)[1].strip()
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif upper.startswith("EXCERPT:"):
            excerpt = line.split(":", 1)[1].strip()
        elif upper.startswith("IMAGE_QUERY:"):
            image_query = line.split(":", 1)[1].strip()

    return headline, meta, tags, excerpt, image_query


def attach_images(articles: list[Article]) -> None:
    """Fetch hero + inline images for each article in place."""
    from image_fetcher import fetch_article_images

    for article in articles:
        article.images = fetch_article_images(
            headline=article.headline,
            image_query=article.image_query,
            source_url=article.source_url,
            tags=article.tags,
        )


def generate_batch(stories: list[dict]) -> list[Article]:
    """Generate articles for a batch of stories."""
    config = _load_config()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    delay = config.get("pipeline", {}).get("delay_between_articles_seconds", 25)

    articles: list[Article] = []
    for i, story in enumerate(stories):
        if i > 0 and delay:
            log.info("Waiting %ds before next article (rate limit)", delay)
            time.sleep(delay)
        log.info("Generating article for: %s", story["title"])
        article = generate_article(story, client, config)
        if article:
            articles.append(article)
            log.info("  → %s", article.headline)
        else:
            log.warning("  → FAILED, skipping")

    if articles and config.get("images", {}).get("enabled", True):
        log.info("Fetching featured images for %d articles", len(articles))
        attach_images(articles)

    log.info("Generated %d / %d articles", len(articles), len(stories))
    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    sample = {
        "title": "Global chip shortage eases as new fabs come online",
        "source": "Reuters",
        "summary": "The global semiconductor shortage that has plagued industries for three years is finally showing signs of easing as major chip manufacturers bring new fabrication plants online.",
        "url": "https://reuters.com/example",
        "category": "tech",
        "published": "2026-05-14",
    }
    articles = generate_batch([sample])
    if articles:
        a = articles[0]
        print(f"\n{'='*60}")
        print(f"HEADLINE: {a.headline}")
        print(f"META: {a.meta_description}")
        print(f"TAGS: {', '.join(a.tags)}")
        print(f"{'='*60}")
        print(a.body)
