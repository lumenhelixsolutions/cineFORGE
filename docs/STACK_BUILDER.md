# StackBuilder Guide

StackBuilder is CineForge's intelligent profile recommendation engine. It ranks available routing profiles against your project constraints and hardware.

## How It Works

StackBuilder scores every profile across four dimensions:
- **Quality** — output fidelity and resolution support
- **Speed** — end-to-end generation latency
- **Cost** — estimated USD spend per minute
- **Depth** — richness of features (extend, frame bridge, native audio)

## Using StackBuilder

### Via API

```bash
curl -X POST http://127.0.0.1:8765/stackbuilder/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "documentary",
    "target_duration_min": 2.0,
    "budget_usd": 10.00,
    "deadline_hours": 4,
    "vram_available_gb": 12,
    "prioritize": "balanced",
    "source_count": 1,
    "word_count": 1500
  }'
```

### Response Fields

| Field | Description |
|-------|-------------|
| `overall_score` | Weighted composite (0–100) |
| `dimension_scores` | Breakdown of quality/speed/cost/depth |
| `recommendation` | Human-readable guidance |
| `warnings` | List of caveats (e.g., "requires GPU") |
| `tradeoffs` | What you gain/lose with this profile |

### Prioritize Modes

- `balanced` — equal weight across all dimensions
- `quality` — maximize fidelity
- `speed` — minimize wall-clock time
- `cost` — minimize spend
- `local` — prefer on-premise adapters

## Profiles

- **cloud_premium** — highest quality, cloud providers, highest cost
- **local_two_stage** — fully local, requires VRAM, zero cloud cost
- **hybrid** — mixes cloud and local based on shot tier

## Applying a Recommendation

The response includes `defaults` for the chosen topic. Use the top `name` as your `routing_profile` when creating or patching a project:

```bash
curl -X PATCH http://127.0.0.1:8765/projects/{id} \
  -H "Content-Type: application/json" \
  -d '{"routing_profile":"hybrid"}'
```
