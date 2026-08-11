"""Hugging Face Hub client — the open-weights side of the LLM landscape.

The model listing endpoint is public (no auth), so the dashboard refreshes from a
GitHub Actions cron with no secret.

Two things decide what a reader sees here, and both are deliberate:

**The universe is more than text.** Open models are no longer only
``text-generation``: a 30B multimodal release lands as ``image-text-to-text`` and
would be invisible to a text-only query. We ask for each tag we track and label the
result, so the "full landscape" claim stays true (issue #2).

**Downloads alone are a rear-view mirror.** The 30-day download counter needs weeks
to move, so ranking by it can only ever show what was already popular — a model
published two days ago sits at zero no matter how important it is. We therefore
also pull each tag by ``trendingScore``, the signal behind the Hub's own trending
page, which surfaces a release the day after it lands. The two lists are merged, so
the catalog holds both the established and the newly arrived.
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

# The tags we track, and the label each one gets in the UI. Order is the
# categorical order used by the charts.
PIPELINE_TAGS: dict[str, str] = {
    "text-generation": "Text",
    "image-text-to-text": "Multimodal",
    "image-to-text": "Vision / OCR",
}
# Established adoption + what is landing right now. See the module docstring.
_SORTS = ("downloads", "trendingScore")

# Third-party repackagings of someone else's weights. They are legitimate downloads
# but they are not new models, and they crowd out the originals in any ranking. We
# keep them in the searchable catalog and exclude them from the charts and the
# headline tables.
_DERIVATIVE_MARKERS = (
    "gguf", "awq", "gptq", "mlx", "exl2", "exl3", "ggml", "onnx", "bnb",
    "4bit", "8bit", "3bit", "fp8", "int8", "int4", "nf4", "w4a16",
    "abliterated", "uncensored", "distill-merge",
)


class HuggingFaceClient:
    """Minimal client for the public Hugging Face model listing."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def _page(self, pipeline_tag: str, sort: str, limit: int) -> list[dict]:
        """One listing page: top `limit` of `pipeline_tag` by `sort`, descending."""
        resp = requests.get(
            HF_MODELS_URL,
            params={
                "pipeline_tag": pipeline_tag,
                "sort": sort,
                "direction": "-1",
                "limit": str(limit),
                "full": "true",
            },
            headers={"Accept": "application/json", "User-Agent": "llm-radar"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    def get_models(self, limit: int = 40) -> list[dict]:
        """Return raw model dicts across every tracked tag and both rankings.

        Deduplicated by model id; a model that appears in several lists keeps the
        first payload seen (they are identical) and is not counted twice.

        Each item includes: id, author, downloads, likes, pipeline_tag, gated,
        createdAt, tags (license lives here as ``license:<id>``).
        """
        merged: dict[str, dict] = {}
        for tag in PIPELINE_TAGS:
            for sort in _SORTS:
                for m in self._page(tag, sort, limit):
                    mid = m.get("id") or m.get("modelId")
                    if mid:
                        merged.setdefault(mid, m)
        if not merged:
            raise ValueError("Hugging Face returned no models")
        return list(merged.values())


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


def _is_derivative(model_id: str) -> bool:
    """True for quantizations, conversions and edits of someone else's weights."""
    parts = model_id.lower().replace("_", "-").split("-")
    return any(marker in parts for marker in _DERIVATIVE_MARKERS)


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
        tag = m.get("pipeline_tag") or ""
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
                "task": tag or "—",
                "category": PIPELINE_TAGS.get(tag, "Other"),
                "derivative": _is_derivative(cid),
                "gated": bool(m.get("gated")),
                "created": created_dt,
                "created_str": created_dt.strftime("%Y-%m-%d") if created_dt else "—",
                "age_days": (now - created_dt).days if created_dt else None,
                "is_new": bool(
                    created_dt and (now - created_dt).days <= _NEW_WINDOW_DAYS
                ),
            }
        )
    df = pd.DataFrame(rows).sort_values("downloads", ascending=False).reset_index(
        drop=True
    )
    return df


def originals(df: pd.DataFrame) -> pd.DataFrame:
    """The catalog minus third-party repackagings — what the charts should plot."""
    return df[~df["derivative"]].copy()


def hf_summary_stats(df: pd.DataFrame) -> dict:
    """High-level numbers for the open-weights value boxes."""
    orig = originals(df)
    top = orig.iloc[0] if len(orig) else None
    top_liked = orig.nlargest(1, "likes").iloc[0] if len(orig) else None
    return {
        "tracked": int(len(df)),
        "top_model": top["name"] if top is not None else "—",
        "top_liked": top_liked["name"] if top_liked is not None else "—",
        "new_this_week": int(df["is_new"].sum()),
        "permissive_pct": int(round(100 * df["permissive"].mean())) if len(df) else 0,
        "orgs": int(df["org"].nunique()),
        "gated": int(df["gated"].sum()),
        "multimodal": int((df["category"] != "Text").sum()),
    }


if __name__ == "__main__":  # smoke test
    df = process_hf_models(HuggingFaceClient().get_models())
    print(f"universe: {len(df)} models  ({df['derivative'].sum()} derivatives)")
    print(df.groupby("category").size().to_string())
    print()
    print(
        originals(df)
        .nlargest(10, "likes")[
            ["name", "org", "category", "downloads_disp", "likes", "license", "is_new"]
        ]
        .to_string(index=False)
    )
    print()
    for k, v in hf_summary_stats(df).items():
        print(f"{k}: {v}")
