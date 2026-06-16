from __future__ import annotations

import httpx

from app.config import get_settings


async def build_parent_digest(student_id: str) -> str:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{settings.public_api_base_url}/api/students/{student_id}/dashboard")
        response.raise_for_status()
    data = response.json()
    tracks = ", ".join(f"{track['subject']}: {track['current_score']}/{track['target_score']}" for track in data.get("tracks", []))
    return (
        "EGE Mentor digest\n"
        f"Tracks: {tracks or 'no tracks yet'}\n"
        f"Clean sheet: {data.get('clean_sheet_ratio', 0):.0%}\n"
        f"Due reviews: {data.get('due_reviews', 0)}"
    )


def main() -> None:
    try:
        import aiogram  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Install backend with the [bot] extra to run Telegram bot") from exc
    raise SystemExit("Telegram runtime wiring is intentionally deferred until API slice is verified.")


if __name__ == "__main__":
    main()
