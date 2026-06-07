# CineForge StackBuilder

The StackBuilder is the most robust logic in CineForge. It scores all 12 routing profiles against your project constraints (topic, duration, budget, deadline, GPU VRAM, priority) and returns ranked recommendations with warnings.

## Philosophy

**v0.1 is documentary-first.** Cinematic entertainment is reserved for future upgrades when the pipeline has proven reliable on informational content. The StackBuilder enforces this by defaulting all topics to documentary-appropriate style packs and grammars.

## How It Works

```
Project Constraints → Dimension Scoring → Weighted Aggregation → Ranked Profiles
```

### Dimensions (0.0–1.0)

| Dimension | What It Measures | Weight in "balanced" |
|-----------|------------------|---------------------|
| **Quality** | Estimated output fidelity | 25% |
| **Speed** | Generation throughput vs. deadline | 20% |
| **Cost** | $ per minute of output | 20% |
| **Depth** | Narrative complexity / research integration | 20% |
| **Compat** | Hardware fit, duration feasibility | 15% |

### Priority Modes

| Mode | Quality | Speed | Cost | Depth | Compat | Best For |
|------|---------|-------|------|-------|--------|----------|
| **balanced** | 25% | 20% | 20% | 20% | 15% | General use |
| **quality** | 40% | 10% | 10% | 25% | 15% | Client delivery |
| **speed** | 15% | 40% | 15% | 10% | 20% | Breaking news |
| **cost** | 10% | 10% | 40% | 20% | 20% | Zero-budget |
| **depth** | 20% | 5% | 15% | 45% | 15% | Investigative |

## The 12 Profiles

### Documentary / Informational (v0.1 Primary)

| Profile | Quality | Speed | Cost | VRAM | Duration | Use Case |
|---------|---------|-------|------|------|----------|----------|
| **documentary_fast** | 0.65 | 0.85 | 0.55 | 4GB | 5 min | News reports, rapid turnaround |
| **documentary_deep** | 0.80 | 0.30 | 0.60 | 8GB | 15 min | Investigative journalism |
| **archival_premium** | 0.90 | 0.60 | 0.25 | 0GB | 20 min | Historical, museum exhibits |
| **explainer_budget** | 0.50 | 0.40 | 1.00 | 4GB | 5 min | Education, non-profit, tutorials |
| **research_walkthrough** | 0.70 | 0.55 | 0.50 | 6GB | 8 min | Academic papers, science comm |
| **news_breaking** | 0.50 | 0.95 | 0.40 | 0GB | 2 min | Breaking news, social clips |

### Advanced / Research-Based

| Profile | Quality | Speed | Cost | VRAM | Duration | Use Case |
|---------|---------|-------|------|------|----------|----------|
| **framepack_hybrid** | 0.75 | 0.35 | 0.70 | 6GB | 10 min | Long-form on limited hardware |
| **cogvideo_hybrid** | 0.55 | 0.50 | 0.75 | 4GB | 3 min | Laptop GPU production |
| **budget_local** | 0.60 | 0.20 | 1.00 | 6GB | 10 min | 100% free, zero API keys |
| **hybrid_balanced** | 0.75 | 0.65 | 0.55 | 6GB | 10 min | Smart tiering, adaptable |

### Cloud-First

| Profile | Quality | Speed | Cost | VRAM | Duration | Use Case |
|---------|---------|-------|------|------|----------|----------|
| **cloud_premium** | 0.95 | 0.90 | 0.15 | 0GB | 10 min | Maximum quality, no GPU |
| **hybrid** (original) | 0.80 | 0.70 | 0.45 | 6GB | 10 min | Cost-conscious with previews |
| **local_two_stage** | 0.60 | 0.30 | 1.00 | 8GB | 10 min | Full local, privacy-critical |

## Topic-Aware Defaults

When you select a topic, the StackBuilder auto-configures:

| Topic | Default Style | Default Grammar | Recommended Profiles |
|-------|--------------|-----------------|----------------------|
| **documentary** | documentary_natural | mini_doc | documentary_deep, hybrid_balanced, documentary_fast |
| **explainer** | whiteboard_explainer | explainer_short | explainer_budget, research_walkthrough |
| **archival** | archival_sepia | mini_doc | archival_premium, documentary_deep |
| **news** | documentary_natural | news_breaking | news_breaking, documentary_fast |
| **research** | whiteboard_explainer | research_walkthrough | research_walkthrough, documentary_deep |
| **tutorial** | whiteboard_explainer | research_walkthrough | explainer_budget, research_walkthrough |
| **historical** | archival_sepia | mini_doc | archival_premium, documentary_deep |
| **cinematic** | cinematic_noir | narrative_3_act | cloud_premium, framepack_hybrid |

## Topic-Aware Director

The Director (treatment + storyboard generators) adapts its system prompt based on topic:

- **documentary**: Factual accuracy, interview subjects, B-roll opportunities, archival footage
- **explainer**: Concept hierarchy, visual metaphors, step-by-step reveal, CTA
- **archival**: Period authenticity, primary sources, narrator voice, emotional through-line
- **news**: Immediacy, source attribution, visual evidence, audience relevance
- **research**: Hypothesis, methodology visualization, result reveal, implication
- **cinematic**: Visual spectacle, emotional arc, character development, set pieces

## Using the StackBuilder

### In the UI

1. Open the **StackBuilder** tab
2. Select your **Topic** (defaults to Documentary)
3. Set **Duration**, **Budget**, **Deadline**, **GPU VRAM**
4. Choose **Prioritize** mode
5. Click **Recommend Stack**
6. Review ranked profiles with dimension scores and warnings
7. Click a profile name to auto-apply it to your project

### Via API

```bash
curl -X POST http://127.0.0.1:8765/stackbuilder/recommend   -H "Content-Type: application/json"   -d '{
    "topic": "documentary",
    "target_duration_min": 5,
    "budget_usd": 10,
    "deadline_hours": 24,
    "vram_available_gb": 8,
    "prioritize": "balanced",
    "source_count": 3,
    "word_count": 8000
  }'
```

Response:
```json
{
  "constraints": { ... },
  "recommendations": [
    {
      "name": "documentary_deep",
      "overall_score": 0.87,
      "dimension_scores": {
        "quality": 0.20,
        "speed": 0.09,
        "cost": 0.12,
        "depth": 0.19,
        "compat": 0.13
      },
      "recommendation": "strong_match",
      "warnings": [],
      "description": "Investigative long-form...",
      "primary_use_case": "Investigative journalism..."
    }
  ],
  "defaults": {
    "style_pack": "documentary_natural",
    "grammar": "mini_doc",
    "recommended_profiles": ["documentary_deep", "hybrid_balanced", "documentary_fast"]
  }
}
```

## Decision Matrix

| If you... | Use Profile | Why |
|-----------|-------------|-----|
| Have no GPU | cloud_premium or news_breaking | No local dependency |
| Have 4GB laptop GPU | cogvideo_hybrid or explainer_budget | Fits in VRAM |
| Have 6GB GPU | framepack_hybrid or documentary_fast | FramePack long-form |
| Have 12GB+ GPU | documentary_deep or hybrid_balanced | Full quality pipeline |
| Need it in 10 min | news_breaking | Fastest cloud pipeline |
| Have $0 budget | budget_local or explainer_budget | Zero API keys |
| Are making a tutorial | research_walkthrough | Equation/diagram optimized |
| Are making a museum piece | archival_premium | Maximum fidelity |
| Want to iterate cheaply | hybrid | Local preview → cloud final |

## Future Upgrades (v0.2+)

- **Auto-detect VRAM** via CUDA query instead of manual input
- **Historical performance** integration ("you used documentary_deep last time, it took 4 hours")
- **Multi-GPU profiles** for distributed rendering
- **Cinematic entertainment** expansion with character consistency, action sequences
- **Real-time preview** mode with LTX-Video sub-second generation
- **A/B test mode** — render same shot with two profiles, compare side-by-side
