import asyncio
from pathlib import Path

import edge_tts


# The architecture calls for "One branded AI voice" across every
# episode -- hardcoded rather than configurable so every story sounds
# consistent. en-US-GuyNeural is a free Microsoft neural voice served
# by edge-tts over the network; no API key required.
VOICE_NAME = "en-US-GuyNeural"


async def _synthesize(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(str(output_path))


def synthesize_voice(text: str, output_path: Path) -> None:
    """
    Generate narration audio for `text` and save it as an mp3 at
    `output_path`. Runs edge-tts's async client inside a fresh event
    loop -- safe here because each Celery worker task runs
    synchronously in its own process.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, output_path))
