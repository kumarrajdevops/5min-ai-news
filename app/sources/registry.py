NEWS_SOURCES = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "source_type": "rss",
        # Re-confirmed 2026-09-17 (still HTTP 429, Vercel bot challenge,
        # same as 2026-09-10): a real fix needs a headless browser to
        # clear a JS challenge, which is out of scope for this
        # project's local-first/minimal-dependency approach -- and not
        # something to build bot-detection evasion for. Disabled until
        # VentureBeat offers a real, non-challenged feed or API.
        "enabled": False,
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "Microsoft Research Blog",
        "url": "https://www.microsoft.com/en-us/research/blog/feed/",
        "source_type": "rss",
        # The old "Microsoft AI Blog" feed (blogs.microsoft.com/ai/feed/)
        # returns HTTP 410 Gone -- retired, not moved (re-confirmed
        # 2026-09-17). This is a real, currently-active, official
        # replacement (verified HTTP 200, well-formed RSS, recent
        # posts). Broader than AI-only, same as Hacker News already is
        # -- the deterministic AI-relevance filter narrows it down,
        # same pattern as every other source here.
        "enabled": True,
    },
    {
        "name": "NVIDIA Blog",
        "url": "https://blogs.nvidia.com/feed/",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "Ars Technica AI",
        "url": "https://arstechnica.com/ai/feed/",
        "source_type": "rss",
        "enabled": True,
    },
    {
        "name": "Google DeepMind News",
        "url": "https://deepmind.google/blog/rss.xml",
        "source_type": "rss",
        # Verified 2026-09-15: official feed, HTTP 200, valid RSS 2.0,
        # latest item dated 2026-09-08.
        "enabled": True,
    },
    {
        "name": "Wired — Artificial Intelligence",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "source_type": "rss",
        # Verified 2026-09-15: official Condé Nast tag feed, HTTP 200,
        # valid RSS 2.0, latest item dated 2026-09-14.
        "enabled": True,
    },
]
