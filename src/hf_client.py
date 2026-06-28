"""Hugging Face Hub client — the open-weights side of the LLM landscape.

The model listing endpoint is public (no auth), so the dashboard refreshes from a
GitHub Actions cron with no secret. We focus on text-generation models (the open
"LLMs") ranked by 30-day downloads, and surface the **license** and **gated** flag —
the details that decide whether a model can be self-hosted for data-residency or
used commercially.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests

HF_MODELS_URL = "https://huggingface.co/api/models"
_NEW_WINDOW_DAYS = 7
# Permissive = freely usable commercially without extra acceptance terms.
_PERMISSIVE = {"apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause", "cc-by-4.0"}
# Dummy/CI fixtures that rank high on raw downloads but aren't real LLMs.
_TESTING_ORGS = {"trl-internal-testing", "hf-internal-testing"}


class HuggingFaceClient:
    """Minimal client for the public Hugging Face model listing."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def get_models(
        self, limit: int = 60, pipeline_tag: str = "text-generation"
    ) -> list[dict]:
        """Return raw model dicts: top `limit` of `pipeline_tag` by 30-day downloads.

        Each item includes: id, author, downloads, likes, pipeline_tag, gated,
        createdAt, tags (license lives here as ``license:<id>``).
        """
        params = {
            "pipeline_tag": pipeline_tag,
            "sort": "downloads",
            "direction": "-1",
            "limit": str(limit),
            "full": "true",
        }
        resp = requests.get(
            HF_MODELS_URL,
            params=params,
            headers={"Accept": "application/json", "User-Agent": "llm-radar"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            raise ValueError("Hugging Face returned no models")
        return data


def _license(tags: list[str] | None) -> str:
    for t in tags or []:
        if t.startswith("license:"):
            return t.split(":", 1)[1]
    return "unknown"


def _human(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def process_hf_models(raw: list[dict], now: datetime | None = None) -> pd.DataFrame:
    """Return a tidy DataFrame, one row per open-weight model."""
    now = now or datetime.now(timezone.utc)
    rows = []
    for m in raw:
        cid = m.get("id") or m.get("modelId") or ""
        org = m.get("author") or (cid.split("/", 1)[0] if "/" in cid else "—")
        short = cid.split("/", 1)[1] if "/" in cid else cid
        # Drop CI/dummy fixtures that inflate raw downloads but aren't real models.
        if org in _TESTING_ORGS or short.lower().startswith(("tiny-", "dummy")):
            continue
        lic = _license(m.get("tags"))
        created = m.get("createdAt")
        created_dt = None
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                created_dt = None
        dl = int(m.get("downloads") or 0)
        rows.append(
            {
                "id": cid,
                "name": short,
                "org": org,
                "downloads": dl,
                "downloads_disp": _human(dl),
                "likes": int(m.get("likes") or 0),
                "license": lic,
                "permissive": lic.lower() in _PERMISSIVE,
                "task": m.get("pipeline_tag") or "—",
                "gated": bool(m.get("gated")),
                "created": created_dt,
                "created_str": created_dt.strftime("%Y-%m-%d") if created_dt else "—",
                "is_new": bool(
                    created_dt and (now - created_dt).days <= _NEW_WINDOW_DAYS
                ),
            }
        )
    df = pd.DataFrame(rows).sort_values("downloads", ascending=False).reset_index(
        drop=True
    )
    return df


def hf_summary_stats(df: pd.DataFrame) -> dict:
    """High-level numbers for the open-weights value boxes."""
    top = df.iloc[0] if len(df) else None
    top_liked = df.nlargest(1, "likes").iloc[0] if len(df) else None
    return {
        "tracked": int(len(df)),
        "top_model": top["name"] if top is not None else "—",
        "top_liked": top_liked["name"] if top_liked is not None else "—",
        "new_this_week": int(df["is_new"].sum()),
        "permissive_pct": int(round(100 * df["permissive"].mean())) if len(df) else 0,
        "orgs": int(df["org"].nunique()),
        "gated": int(df["gated"].sum()),
    }


if __name__ == "__main__":  # smoke test
    df = process_hf_models(HuggingFaceClient().get_models())
    print(
        df[["name", "org", "downloads_disp", "likes", "license", "gated", "is_new"]]
        .head(10)
        .to_string()
    )
    print()
    for k, v in hf_summary_stats(df).items():
        print(f"{k}: {v}")
