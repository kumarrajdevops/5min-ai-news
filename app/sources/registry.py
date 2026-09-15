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
        # Confirmed 2026-09-10: still returns HTTP 429 (Vercel bot
        # challenge) even with a browser-like User-Agent set, and the
        # response body isn't valid XML (bozo=1, "invalid token") -- it's
        # the challenge page, not the feed. Disabled until/unless we
        # want to invest in a real headless-browser fetch for this one.
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
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "source_type": "rss",
        # Confirmed 2026-09-10: HTTP 410 Gone. The feed was retired, not
        # just moved. Disabled -- needs a real replacement URL, not a fix.
        "enabled": False,
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
