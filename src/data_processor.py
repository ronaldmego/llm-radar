"""Transform raw OpenRouter models into a clean DataFrame for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

_NEW_WINDOW_DAYS = 7


def _provider(model: dict) -> str:
    """Human provider label, e.g. 'Anthropic'. Prefer the 'Provider: Model' name."""
    name = model.get("name") or ""
    if ":" in name:
        return name.split(":", 1)[0].strip()
    pid = (model.get("id") or "").lstrip("~")
    return pid.split("/", 1)[0].title() if "/" in pid else pid


def _price_per_m(value: str | None) -> float | None:
    try:
        if value is None:
            return None
        per_m = round(float(value) * 1_000_000, 4)
        # OpenRouter uses negative sentinel prices for some placeholder models.
        return per_m if per_m >= 0 else None
    except (TypeError, ValueError):
        return None


def process_models(raw: list[dict], now: datetime | None = None) -> pd.DataFrame:
    """Return a tidy DataFrame, one row per model."""
    now = now or datetime.now(timezone.utc)
    rows = []
    for m in raw:
        pricing = m.get("pricing") or {}
        arch = m.get("architecture") or {}
        params = m.get("supported_parameters") or []
        created = m.get("created")
        created_dt = (
            datetime.fromtimestamp(created, tz=timezone.utc) if created else None
        )
        in_mods = arch.get("input_modalities") or []
        price_in = _price_per_m(pricing.get("prompt"))
        price_out = _price_per_m(pricing.get("completion"))

        rows.append(
            {
                "name": (m.get("name") or m.get("id") or "").split(":", 1)[-1].strip(),
                "full_name": m.get("name") or m.get("id"),
                "provider": _provider(m),
                "id": m.get("id"),
                "context": m.get("context_length") or 0,
                "context_k": round((m.get("context_length") or 0) / 1000),
                "price_in": price_in,
                "price_out": price_out,
                "is_free": (price_in == 0 and price_out == 0),
                "multimodal": any(x != "text" for x in in_mods),
                "modalities": ", ".join(in_mods) if in_mods else "text",
                "reasoning": "reasoning" in params or "include_reasoning" in params,
                "tools": "tools" in params,
                "created": created_dt,
                "created_str": created_dt.strftime("%Y-%m-%d") if created_dt else "—",
                "is_new": bool(
                    created_dt and (now - created_dt).days <= _NEW_WINDOW_DAYS
                ),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(["created", "context"], ascending=False).reset_index(drop=True)
    return df


def summary_stats(df: pd.DataFrame) -> dict:
    """High-level numbers for the hero value boxes."""
    paid = df[(df["price_in"].notna()) & (df["price_in"] > 0)]
    cheapest = paid.nsmallest(1, "price_in")
    biggest = df.nlargest(1, "context")
    return {
        "total_models": int(len(df)),
        "providers": int(df["provider"].nunique()),
        "free_models": int(df["is_free"].sum()),
        "new_this_week": int(df["is_new"].sum()),
        "max_context_k": int(biggest["context_k"].iloc[0]) if len(biggest) else 0,
        "max_context_model": biggest["name"].iloc[0] if len(biggest) else "—",
        "cheapest_price": float(cheapest["price_in"].iloc[0]) if len(cheapest) else 0.0,
        "cheapest_model": cheapest["name"].iloc[0] if len(cheapest) else "—",
        "updated_utc": (now_str := datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    }


if __name__ == "__main__":  # smoke test
    from api_client import OpenRouterClient

    df = process_models(OpenRouterClient().get_models())
    print(df[["name", "provider", "context_k", "price_in", "price_out", "is_new"]].head(10).to_string())
    print()
    for k, v in summary_stats(df).items():
        print(f"{k}: {v}")
