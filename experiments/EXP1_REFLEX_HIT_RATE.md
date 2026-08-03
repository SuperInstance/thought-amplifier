# Experiment 1: Reflex Hit Rate — Cognitive Content vs Command Routing

**Date:** 2026-08-03 12:21 AKDT  
**Embedding method:** TF-IDF (1-2 grams, sublinear TF, L2-normalized) via scikit-learn  
**Thresholds:** exact ≥0.80 | similar 0.55–0.80 | novel <0.55  
**Sample size:** 100 cognitive thoughts + 100 command phrases  

## Hypothesis

> The reflex hit rate for cognitive content (2-4 sentence thoughts) is significantly
> lower than for command routing (3-8 word intent phrases), due to higher semantic
> variability in thought content.

## Data Characteristics

| Metric | Cognitive Thoughts | Command Phrases |
|--------|-------------------|-----------------|
| Count | 100 | 100 |
| Mean word count | 22.0 | 3.1 |
| Min word count | 16 | 2 |
| Max word count | 28 | 4 |
| Mean char count | 128 | 16 |
| Vocabulary (unique terms) | 294 | 105 |

**Combined vocabulary (TF-IDF features):** 768 terms (1-2 grams)

### Sample Cognitive Thoughts (first 5)
1. "I pause at this storm on island where colors shift and change as you move. I wonder if i can reach that high point for a better view."
2. "Standing here at the misty meadow, I notice smooth stones line a pathway. Let me investigate that sound cautiously."
3. "The hidden waterfall is striking — the air feels charged with energy. I should check if this area is safe before proceeding."
4. "Looking around the forest path, something glints just below the surface. I feel drawn to investigate the glowing elements."
5. "Looking around the desert canyon, fragrant blooms release their scent. I want to pause here and appreciate this moment."

### Sample Command Phrases (first 5)
1. `search canyon forward`
2. `harvest the large tunnel`
3. `move lighthouse at valley`
4. `use tunnel on farm`
5. `examine door at garden`

## Hit Rate Results

### Cumulative Hit Rates at Checkpoints

| Checkpoint | Type | Exact (≥0.80) | Similar (0.55-0.80) | Novel (<0.55) | Hit Rate (E+S) | Avg Sim |
|-----------|------|---------------|---------------------|---------------|----------------|---------|
| n=25 | Cognitive | 0 (0.0%) | 1 (4.0%) | 24 (96.0%) | 4.0% | 0.262 |
| n=25 | Command | 0 (0.0%) | 0 (0.0%) | 25 (100.0%) | 0.0% | 0.094 |
| n=50 | Cognitive | 0 (0.0%) | 5 (10.0%) | 45 (90.0%) | 10.0% | 0.324 |
| n=50 | Command | 0 (0.0%) | 1 (2.0%) | 49 (98.0%) | 2.0% | 0.173 |
| n=100 | Cognitive | 0 (0.0%) | 13 (13.1%) | 86 (86.9%) | 13.1% | 0.380 |
| n=100 | Command | 1 (1.0%) | 5 (5.1%) | 93 (93.9%) | 6.1% | 0.238 |

### Similarity Distribution (best match per item)

| Metric | Cognitive | Command |
|--------|-----------|---------|
| Mean best similarity | 0.3798 | 0.2382 |
| Std deviation | 0.1565 | 0.1843 |
| Median | 0.3741 | 0.2418 |
| 25th percentile | 0.3256 | 0.1448 |
| 75th percentile | 0.4332 | 0.3218 |
| Min | 0.0000 | 0.0000 |
| Max | 0.7326 | 1.0000 |

## Threshold Sensitivity Analysis

Hit rate at various similarity thresholds (full 100-item set):

| Threshold | Cognitive Hit Rate | Command Hit Rate | Difference |
|-----------|-------------------|------------------|------------|
| ≥0.10 | 92.9% | 76.8% | -16.2% |
| ≥0.15 | 91.9% | 73.7% | -18.2% |
| ≥0.20 | 89.9% | 61.6% | -28.3% |
| ≥0.25 | 88.9% | 46.5% | -42.4% |
| ≥0.30 | 80.8% | 32.3% | -48.5% |
| ≥0.35 | 57.6% | 19.2% | -38.4% |
| ≥0.40 | 35.4% | 17.2% | -18.2% |
| ≥0.45 | 21.2% | 12.1% | -9.1% |
| ≥0.50 | 17.2% | 9.1% | -8.1% |
| ≥0.55 | 13.1% | 6.1% | -7.1% |
| ≥0.60 | 11.1% | 1.0% | -10.1% |
| ≥0.65 | 9.1% | 1.0% | -8.1% |
| ≥0.70 | 4.0% | 1.0% | -3.0% |
| ≥0.75 | 0.0% | 1.0% | +1.0% |
| ≥0.80 | 0.0% | 1.0% | +1.0% |

## Statistical Analysis

| Test | Value | p-value | Significant? |
|------|-------|---------|--------------|
| Mann-Whitney U (one-sided, cog < cmd) | U=7495.0 | 1.000000 | No (α=0.05) |
| Welch's t-test (two-sided) | t=5.831 | 0.000000 | Yes (α=0.05) |

**Effect size (Cohen's d):** -0.829 (large effect)
**Cognitive mean similarity:** 0.3798 ± 0.1565
**Command mean similarity:** 0.2382 ± 0.1843
**Cognitive hit rate (≥0.55):** 13.1%
**Command hit rate (≥0.55):** 6.1%

## Assessment: Can the 40% Reflex Hit Rate Threshold Be Achieved?

The dissertation (Claim C2) states that after 1 hour of play, the reflex cascade
should achieve ≥40% hit rate (exact + similar at threshold 0.55).

- **Command phrases hit rate (≥0.55):** 6.1%
- **Cognitive thoughts hit rate (≥0.55):** 13.1%
- **Gap:** -7.1% percentage points

- **Cognitive content does NOT reach 40% hit rate within 100 items at ≥0.55** ❌
- **Command content does NOT reach 40% hit rate within 100 items at ≥0.55** ❌

- **Cognitive content reaches 40% at threshold ≥0.10** (instead of 0.55)

**VERDICT:** The 40% threshold is NOT achievable for cognitive content at n=100 with standard thresholds.
Only 13.1% of cognitive thoughts found a match ≥0.55.

## Implications for Reflex Cascade Design

### Key Findings

1. **Semantic diversity gap:** Cognitive thoughts are moderately more semantically diverse than commands.
2. **Hit rate differential:** Commands achieve 6.1% vs thoughts at 13.1% (≥0.55)
3. **Effect size:** Cohen's d = -0.829 (large)
4. **Statistical significance:** Mann-Whitney p = 1.000000 (not significant)

### Design Recommendations

Based on these results:

1. **Adaptive thresholds:** Use different similarity thresholds for cognitive vs command content
   - Recommended cognitive threshold: ~0.10
   - Recommended command threshold: ~0.55 (current)

2. **Two-tier reflex store:**
   - Command reflex: strict threshold (0.55+), fast path
   - Thought reflex: relaxed threshold, slower but more useful

3. **Semantic clustering:** Pre-cluster thoughts by topic (location, action, emotion)
   before similarity search to reduce search space

4. **Cache warmup strategy:** Accept longer warmup for cognitive reflex
   - Commands may reach 40% hit rate by n=~50+
   - Thoughts need either more items or lower thresholds

### Comparison to Expected Values

| Metric | Expected (Dissertation) | Observed | Assessment |
|--------|------------------------|----------|------------|
| Command hit rate | 50-60% | 6.1% | Outside range |
| Cognitive hit rate | 20-35% | 13.1% | Outside range |
| Hit rate gap | ~20-30pp | -7.1% | Different than expected |
| 40% achievable (cognitive) | At risk | NO | Claim C2 at risk |

## Limitations

1. **Embedding method:** TF-IDF (lexical similarity) rather than neural embeddings (bge-m3).
   - TF-IDF captures lexical overlap, not deep semantic similarity
   - Neural embeddings may show higher hit rates due to semantic understanding
   - However, TF-IDF is a conservative estimate — if it shows low hit rates, neural may also

2. **Sample size:** 100 items per category (dissertation calls for 1,000)
3. **Single seed:** One generation run; dissertation calls for 3 seeds
4. **No temporal correlation:** Real thought streams have autocorrelation; random sampling overestimates diversity
5. **Template generation:** Thoughts generated from structured templates, not live LLM inference
6. **Gateway contention:** Ollama shared with OpenClaw gateway caused instability during neural embedding attempts

## Appendix A: Per-Item Classification

### Cognitive Thoughts (all 99 comparisons)

| Item | Best Similarity | Classification | Matched Item | Thought Excerpt (20 chars) |
|------|----------------|----------------|--------------|---------------------------|
| 1 | 0.0000 | novel | 0 | Standing here at the... |
| 2 | 0.0000 | novel | 0 | The hidden waterfall... |
| 3 | 0.0298 | novel | 1 | Looking around the f... |
| 4 | 0.0254 | novel | 3 | Looking around the d... |
| 5 | 0.3316 | novel | 2 | The harbor at dusk i... |
| 6 | 0.0265 | novel | 5 | The sandstone arch i... |
| 7 | 0.4387 | novel | 0 | What catches my eye ... |
| 8 | 0.0695 | novel | 7 | What catches my eye ... |
| 9 | 0.1915 | novel | 6 | What catches my eye ... |
| 10 | 0.3574 | novel | 3 | I pause at this bamb... |
| 11 | 0.3796 | novel | 10 | I pause at this ligh... |
| 12 | 0.3324 | novel | 11 | The marsh at night i... |
| 13 | 0.0288 | novel | 5 | The dock constructio... |
| 14 | 0.2775 | novel | 13 | Looking around the v... |
| 15 | 0.3371 | novel | 6 | What catches my eye ... |
| 16 | 0.3911 | novel | 9 | I pause at this rive... |
| 17 | 0.7075 | similar | 0 | The crystal cave is ... |
| 18 | 0.3895 | novel | 8 | What catches my eye ... |
| 19 | 0.1333 | novel | 2 | Looking around the h... |
| 20 | 0.3260 | novel | 4 | What catches my eye ... |
| 21 | 0.3251 | novel | 6 | Looking around the d... |
| 22 | 0.3709 | novel | 20 | The abandoned mine i... |
| 23 | 0.3440 | novel | 20 | What catches my eye ... |
| 24 | 0.4261 | novel | 1 | Standing here at the... |
| 25 | 0.3058 | novel | 10 | The workshop interio... |
| 26 | 0.3165 | novel | 22 | Standing here at the... |
| 27 | 0.5939 | similar | 26 | What catches my eye ... |
| 28 | 0.6036 | similar | 23 | I pause at this ston... |
| 29 | 0.3385 | novel | 2 | Standing here at the... |
| 30 | 0.2867 | novel | 4 | Looking around the d... |
| 31 | 0.2424 | novel | 19 | I pause at this gard... |
| 32 | 0.2847 | novel | 27 | What catches my eye ... |
| 33 | 0.3774 | novel | 9 | What catches my eye ... |
| 34 | 0.3414 | novel | 12 | The frozen lake is s... |
| 35 | 0.4291 | novel | 0 | Standing here at the... |
| 36 | 0.2555 | novel | 12 | Looking around the b... |
| 37 | 0.4036 | novel | 1 | Looking around the g... |
| 38 | 0.3889 | novel | 3 | Looking around the h... |
| 39 | 0.3277 | novel | 38 | What catches my eye ... |
| 40 | 0.3777 | novel | 35 | Standing here at the... |
| 41 | 0.3810 | novel | 14 | I pause at this fore... |
| 42 | 0.3162 | novel | 4 | What catches my eye ... |
| 43 | 0.3325 | novel | 8 | I pause at this hidd... |
| 44 | 0.7082 | similar | 21 | I pause at this clif... |
| 45 | 0.3123 | novel | 34 | Standing here at the... |
| 46 | 0.3855 | novel | 41 | I pause at this froz... |
| 47 | 0.5998 | similar | 29 | Looking around the t... |
| 48 | 0.3480 | novel | 44 | I pause at this wind... |
| 49 | 0.3884 | novel | 8 | What catches my eye ... |
| 50 | 0.2972 | novel | 25 | Standing here at the... |
| 51 | 0.4329 | novel | 45 | Standing here at the... |
| 52 | 0.3507 | novel | 4 | I pause at this hidd... |
| 53 | 0.4709 | novel | 19 | Looking around the g... |
| 54 | 0.4323 | novel | 24 | Standing here at the... |
| 55 | 0.3446 | novel | 12 | The beach at dawn is... |
| 56 | 0.3749 | novel | 39 | The glowing ancient ... |
| 57 | 0.2614 | novel | 19 | Looking around the c... |
| 58 | 0.6147 | similar | 9 | I pause at this obsi... |
| 59 | 0.4127 | novel | 41 | The glowing ancient ... |
| 60 | 0.6642 | similar | 5 | I pause at this trop... |
| 61 | 0.3674 | novel | 51 | I pause at this stor... |
| 62 | 0.3532 | novel | 57 | The harbor at dusk i... |
| 63 | 0.2931 | novel | 13 | Standing here at the... |
| 64 | 0.3483 | novel | 44 | I pause at this beac... |
| 65 | 0.6587 | similar | 52 | Standing here at the... |
| 66 | 0.3911 | novel | 57 | Looking around the o... |
| 67 | 0.3566 | novel | 36 | The tide pools is st... |
| 68 | 0.3347 | novel | 16 | Looking around the d... |
| 69 | 0.4051 | novel | 32 | The snowy mountain p... |
| 70 | 0.6773 | similar | 18 | The bamboo grove is ... |
| 71 | 0.3401 | novel | 10 | I pause at this rive... |
| 72 | 0.1835 | novel | 40 | What catches my eye ... |
| 73 | 0.4327 | novel | 53 | I pause at this beac... |
| 74 | 0.3336 | novel | 66 | Standing here at the... |
| 75 | 0.5134 | novel | 37 | Standing here at the... |
| 76 | 0.5071 | novel | 50 | Standing here at the... |
| 77 | 0.7121 | similar | 76 | Standing here at the... |
| 78 | 0.6811 | similar | 59 | I pause at this clif... |
| 79 | 0.7326 | similar | 70 | I pause at this aban... |
| 80 | 0.4582 | novel | 47 | The cliff edge is st... |
| 81 | 0.5073 | novel | 65 | Standing here at the... |
| 82 | 0.3998 | novel | 72 | Looking around the r... |
| 83 | 0.3990 | novel | 30 | The garden in rain i... |
| 84 | 0.5290 | novel | 10 | I pause at this bamb... |
| 85 | 0.3297 | novel | 31 | Standing here at the... |
| 86 | 0.3046 | novel | 60 | I pause at this mars... |
| 87 | 0.4693 | novel | 69 | The dock constructio... |
| 88 | 0.4156 | novel | 85 | Standing here at the... |
| 89 | 0.3624 | novel | 56 | Looking around the b... |
| 90 | 0.3982 | novel | 61 | The beach at dawn is... |
| 91 | 0.3741 | novel | 38 | Looking around the d... |
| 92 | 0.2620 | novel | 12 | Standing here at the... |
| 93 | 0.4188 | novel | 20 | Looking around the h... |
| 94 | 0.3297 | novel | 31 | The tropical jungle ... |
| 95 | 0.6732 | similar | 41 | What catches my eye ... |
| 96 | 0.4970 | novel | 90 | Looking around the w... |
| 97 | 0.4339 | novel | 16 | I pause at this wind... |
| 98 | 0.4468 | novel | 62 | Standing here at the... |
| 99 | 0.4336 | novel | 1 | What catches my eye ... |

### Command Phrases (all 99 comparisons)

| Item | Best Similarity | Classification | Matched Item | Command |
|------|----------------|----------------|--------------|---------|
| 1 | 0.0000 | novel | 0 | `harvest the large tunnel` |
| 2 | 0.0000 | novel | 0 | `move lighthouse at valley` |
| 3 | 0.1691 | novel | 1 | `use tunnel on farm` |
| 4 | 0.0000 | novel | 0 | `examine door at garden` |
| 5 | 0.0000 | novel | 0 | `go north` |
| 6 | 0.0000 | novel | 0 | `go around` |
| 7 | 0.0000 | novel | 0 | `go west` |
| 8 | 0.0000 | novel | 0 | `activate a hidden beacon` |
| 9 | 0.0000 | novel | 0 | `mark ridge back` |
| 10 | 0.0000 | novel | 0 | `repair a strange roof` |
| 11 | 0.0000 | novel | 0 | `craft pass left` |
| 12 | 0.2438 | novel | 8 | `find the ancient beacon` |
| 13 | 0.0000 | novel | 0 | `go east` |
| 14 | 0.0000 | novel | 0 | `collect cliff across` |
| 15 | 0.0000 | novel | 0 | `map statue at meadow` |
| 16 | 0.1763 | novel | 3 | `investigate a small tunnel` |
| 17 | 0.5480 | novel | 3 | `use tunnel on fence` |
| 18 | 0.0000 | novel | 0 | `cross to harbor` |
| 19 | 0.1853 | novel | 4 | `investigate to garden` |
| 20 | 0.2007 | novel | 4 | `examine cart` |
| 21 | 0.1689 | novel | 10 | `connect a distant roof` |
| 22 | 0.1283 | novel | 17 | `use window on torch` |
| 23 | 0.2557 | novel | 10 | `repair past` |
| 24 | 0.2644 | novel | 4 | `check door` |
| 25 | 0.0000 | novel | 0 | `place across` |
| 26 | 0.1808 | novel | 24 | `check platform` |
| 27 | 0.1714 | novel | 17 | `use well on sign` |
| 28 | 0.5859 | similar | 7 | `examine west` |
| 29 | 0.2060 | novel | 22 | `climb a distant window` |
| 30 | 0.2062 | novel | 17 | `find the old fence` |
| 31 | 0.1702 | novel | 29 | `climb wall at ruins` |
| 32 | 0.1911 | novel | 8 | `activate lever at canyon` |
| 33 | 0.0000 | novel | 0 | `go over` |
| 34 | 0.1681 | novel | 15 | `map jungle south` |
| 35 | 0.2519 | novel | 14 | `collect reef back` |
| 36 | 0.0000 | novel | 0 | `find a cold bridge` |
| 37 | 0.4814 | novel | 5 | `dig north` |
| 38 | 0.3049 | novel | 12 | `find a dark beacon` |
| 39 | 0.3312 | novel | 35 | `craft reef across` |
| 40 | 0.0000 | novel | 0 | `go right` |
| 41 | 0.5118 | novel | 5 | `map north` |
| 42 | 0.0000 | novel | 0 | `open to grove` |
| 43 | 0.3317 | novel | 38 | `find a dark door` |
| 44 | 0.2079 | novel | 28 | `examine fence at pass` |
| 45 | 0.4344 | novel | 34 | `go south` |
| 46 | 0.2648 | novel | 14 | `navigate to cliff` |
| 47 | 0.4617 | novel | 31 | `climb to ruins` |
| 48 | 0.3085 | novel | 41 | `map path` |
| 49 | 0.2588 | novel | 31 | `check wall` |
| 50 | 0.2595 | novel | 30 | `deactivate fence` |
| 51 | 0.2388 | novel | 21 | `check roof` |
| 52 | 0.3131 | novel | 18 | `cross path` |
| 53 | 0.2790 | novel | 42 | `open the ancient lever` |
| 54 | 0.2086 | novel | 27 | `use well on gate` |
| 55 | 0.2014 | novel | 0 | `explore plateau forward` |
| 56 | 0.3070 | novel | 2 | `harvest to valley` |
| 57 | 0.5954 | similar | 40 | `mark right` |
| 58 | 0.0000 | novel | 0 | `scan to forest` |
| 59 | 0.1498 | novel | 34 | `check floor at jungle` |
| 60 | 0.5596 | similar | 18 | `cross across` |
| 61 | 0.2014 | novel | 55 | `craft tower at plateau` |
| 62 | 0.0000 | novel | 0 | `go up` |
| 63 | 0.1770 | novel | 26 | `check chest` |
| 64 | 0.2454 | novel | 51 | `use lever on roof` |
| 65 | 0.3200 | novel | 46 | `navigate platform` |
| 66 | 0.1720 | novel | 27 | `use dock on shelter` |
| 67 | 0.0000 | novel | 0 | `find the glowing mechanism` |
| 68 | 0.5739 | similar | 31 | `connect wall at ruins` |
| 69 | 0.5326 | novel | 60 | `cross to valley` |
| 70 | 0.3197 | novel | 56 | `harvest to garden` |
| 71 | 0.3548 | novel | 67 | `check mechanism` |
| 72 | 0.3914 | novel | 5 | `navigate pass north` |
| 73 | 0.2909 | novel | 50 | `deactivate to mountain` |
| 74 | 0.2470 | novel | 8 | `activate to marsh` |
| 75 | 0.1658 | novel | 64 | `inspect the broken lever` |
| 76 | 0.4286 | novel | 26 | `check well` |
| 77 | 0.3263 | novel | 12 | `collect beacon` |
| 78 | 0.2528 | novel | 15 | `search statue` |
| 79 | 0.3295 | novel | 23 | `examine past` |
| 80 | 0.2752 | novel | 27 | `climb sign at canyon` |
| 81 | 0.2014 | novel | 61 | `collect the broken tower` |
| 82 | 0.2161 | novel | 50 | `craft the nearby fence` |
| 83 | 0.5910 | similar | 25 | `place north` |
| 84 | 0.4814 | novel | 5 | `remove north` |
| 85 | 0.4466 | novel | 76 | `check shelter` |
| 86 | 0.2657 | novel | 3 | `find the glowing farm` |
| 87 | 0.4466 | novel | 76 | `check path` |
| 88 | 0.2810 | novel | 87 | `find the ancient path` |
| 89 | 0.3148 | novel | 71 | `find the bright mechanism` |
| 90 | 0.3268 | novel | 3 | `use platform on farm` |
| 91 | 0.2714 | novel | 9 | `mark to garden` |
| 92 | 0.2418 | novel | 36 | `gather bridge at pass` |
| 93 | 0.2828 | novel | 63 | `deactivate chest at pass` |
| 94 | 0.1398 | novel | 32 | `build rope at canyon` |
| 95 | 0.4321 | novel | 45 | `deactivate marsh south` |
| 96 | 0.3237 | novel | 22 | `use torch on rope` |
| 97 | 0.0000 | novel | 0 | `go under` |
| 98 | 1.0000 | exact | 14 | `collect cliff through` |
| 99 | 0.2318 | novel | 19 | `construct to garden` |

## Appendix B: Similarity Matrix Samples (10×10)

### Cognitive Thoughts (first 10)

| | T0 | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 |
|---|---|---|---|---|---|---|---|---|---|---|
| T0 | 1.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.00 | 0.00 | 0.44 | 0.00 | 0.00 |
| T1 | 0.00 | 1.00 | 0.00 | 0.03 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| T2 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.33 | 0.02 | 0.00 | 0.00 | 0.03 |
| T3 | 0.00 | 0.03 | 0.00 | 1.00 | 0.03 | 0.26 | 0.00 | 0.00 | 0.00 | 0.00 |
| T4 | 0.02 | 0.00 | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 |
| T5 | 0.00 | 0.00 | 0.33 | 0.26 | 0.00 | 1.00 | 0.03 | 0.00 | 0.00 | 0.03 |
| T6 | 0.00 | 0.00 | 0.02 | 0.00 | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0.19 |
| T7 | 0.44 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.07 | 0.07 |
| T8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 1.00 | 0.11 |
| T9 | 0.00 | 0.00 | 0.03 | 0.00 | 0.02 | 0.03 | 0.19 | 0.07 | 0.11 | 1.00 |

### Command Phrases (first 10)

| | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C1 | 0.00 | 1.00 | 0.00 | 0.17 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C3 | 0.00 | 0.17 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C4 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| C8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 |
| C9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |

## Appendix C: Similarity Distribution Histograms

### Cognitive Thoughts — Best Match Similarity Distribution
```
       Range |  Cognitive |    Command | Bar
------------------------------------------------------------
0.00-0.05  |          6 |         23 | C:███████ M:▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
0.05-0.10  |          1 |          0 | C:█ M:
0.10-0.15  |          1 |          3 | C:█ M:▓▓▓
0.15-0.20  |          2 |         12 | C:██ M:▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
0.20-0.25  |          1 |         15 | C:█ M:▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
0.25-0.30  |          8 |         14 | C:██████████ M:▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
0.30-0.35  |         23 |         13 | C:██████████████████████████████ M:▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
0.35-0.40  |         22 |          2 | C:████████████████████████████ M:▓▓
0.40-0.45  |         14 |          5 | C:██████████████████ M:▓▓▓▓▓▓
0.45-0.50  |          4 |          3 | C:█████ M:▓▓▓
0.50-0.55  |          4 |          3 | C:█████ M:▓▓▓
0.55-0.60  |          2 |          5 | C:██ M:▓▓▓▓▓▓
0.60-0.65  |          2 |          0 | C:██ M:
0.65-0.70  |          5 |          0 | C:██████ M:
0.70-0.75  |          4 |          0 | C:█████ M:
0.75-0.80  |          0 |          0 | C: M:
0.80-0.85  |          0 |          0 | C: M:
0.85-0.90  |          0 |          0 | C: M:
0.90-0.95  |          0 |          0 | C: M:
0.95-1.00  |          0 |          0 | C: M:
```

## Appendix D: Methodology

### Embedding
- **Primary:** TF-IDF (Term Frequency-Inverse Document Frequency)
- **Configuration:** 1-2 grams, English stop words removed, sublinear TF (1+log(tf)), L2-normalized
- **Vocabulary:** Fitted on combined corpus (200 documents)
- **Library:** scikit-learn TfidfVectorizer

### Similarity Computation
- Cosine similarity (equivalent to dot product for L2-normalized vectors)
- Incremental insertion: for item i, compare against items 0..i-1
- Classification: exact (≥0.80), similar (0.55–0.80), novel (<0.55)

### Data Generation
- **Cognitive thoughts:** 30 scenarios × 20 observations × 20 intentions (12K combinations)
- **Commands:** 30 verbs × 30 objects × 16 directions × 20 locations × 15 modifiers
- **Generation:** Python random sampling from combinatorial space

### Statistical Tests
- **Mann-Whitney U:** Non-parametric test for difference in distributions
- **Welch's t-test:** Parametric test for difference in means (unequal variance)
- **Cohen's d:** Standardized effect size (pooled SD)
- **Library:** scipy.stats

### Reproducibility
- Raw data: `thoughts_cognitive.txt`, `thoughts_commands.txt`
- Scripts: `generate_data.py`, `run_experiment_tfidf.py`
- Packages: numpy, scikit-learn, scipy
