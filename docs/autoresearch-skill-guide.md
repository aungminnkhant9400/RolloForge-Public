# Karpathy Autoresearch Skill Integration Guide

**For:** RolloForge OpenClaw Skills  
**Priority:** 8.5/10 (from actionable-intelligence.md)  
**Proven Result:** 56% → 92% pass rate improvement with zero manual work

---

## What is Karpathy Autoresearch?

Karpathy's autoresearch is a method where an AI agent autonomously improves a system through iterative experimentation:

> **AI agent makes change → evaluates result → keeps if improved → reverts if not → repeats**

### Core Pattern
```
while (time_budget_remaining):
    make_small_change()
    run_test()
    if (score_improved):
        keep_change()
    else:
        revert_change()
    log_experiment()
```

### Real-World Results

| Implementation | Domain | Results |
|----------------|--------|---------|
| **Ole Lehmann's Skill** | Claude Code skills | 56% → 92% passing (landing page copy) |
| **Aakash Gupta** | Claude Code experiments | 41% → 92% in 4 rounds while sleeping |
| **BTCautoresearch** | Bitcoin price prediction | 328 experiments, 50.5% improvement over baseline |
| **Tennis XGBoost** | Sports prediction | +155 basis points ROC-AUC (60 iterations) |
| **Deedy's Chess Engine** | Rust chess AI | Top 50 grandmaster (#311 engine), 2718 ELO |
| **Karpathy's Original** | Nanochat LLM training | ~12 experiments/hour, ~100 overnight |

---

## How It Auto-Improves Skills

### The Mechanism

1. **Define Measurable Success**: Create a scoring checklist (3-6 yes/no questions)
2. **Make Small Changes**: Agent modifies skill instructions incrementally
3. **Run Test Suite**: Test modified skill against benchmark cases
4. **Score Results**: Apply scoring checklist to output
5. **Keep or Revert**: Keep if score improves, revert if not
6. **Repeat**: Continue until time budget exhausted

### Why It Works

- **Compounding improvements**: Small gains stack exponentially
- **Local hill-climbing**: Avoids catastrophic forgetting
- **Runs overnight**: No human intervention needed
- **Measurable**: Only keeps objectively better changes
- **Domain agnostic**: Works on any measurable task

---

## Integration Guide for RolloForge Skills

### Step 1: Identify Target Skills

**Best candidates for autoresearch:**
- Skills with clear success criteria (classification, extraction, formatting)
- Skills that run repeatedly (high ROI on improvement)
- Skills with measurable output quality

**RolloForge skill candidates:**
1. `bookmark-processor` - Tagging accuracy, bucket assignment
2. `analysis-generator` - Report quality, insight relevance
3. `priority-scorer` - Priority alignment with user goals
4. `deepseek-analyzer` - Analysis completeness, actionability

### Step 2: Create Test Suite

For each target skill, create a benchmark dataset:

```python
# Example: bookmark-processor test suite
test_cases = [
    {
        "input": "https://x.com/karpathy/status/2036487306585268612",
        "expected_tags": ["security", "llm", "supply-chain"],
        "expected_bucket": "test_this_week",
        "description": "Security vulnerability from trusted source"
    },
    # ... 20-50 more cases
]
```

### Step 3: Define Scoring Checklist

Create 3-6 yes/no questions (see template below).

### Step 4: Set Up Autoresearch Loop

```python
# autoresearch_skill.py - Core loop
import time
from datetime import datetime, timedelta

class SkillAutoresearch:
    def __init__(self, skill_path, test_suite, scorer, time_budget_hours=8):
        self.skill_path = skill_path
        self.test_suite = test_suite
        self.scorer = scorer
        self.end_time = datetime.now() + timedelta(hours=time_budget_hours)
        self.experiments = []
        self.best_score = 0
        self.best_version = None
    
    def run(self):
        while datetime.now() < self.end_time:
            # 1. Make small change to skill
            modification = self.generate_modification()
            self.apply_modification(modification)
            
            # 2. Run tests
            results = []
            for test in self.test_suite:
                output = self.run_skill(test["input"])
                score = self.scorer.score(output, test["expected"])
                results.append(score)
            
            avg_score = sum(results) / len(results)
            
            # 3. Keep or revert
            if avg_score > self.best_score:
                self.best_score = avg_score
                self.best_version = modification
                self.log_experiment(modification, avg_score, "kept")
            else:
                self.revert_modification()
                self.log_experiment(modification, avg_score, "reverted")
            
            # 4. Pace to avoid rate limits
            time.sleep(30)  # Adjust based on API tier
    
    def generate_modification(self):
        """Use LLM to generate skill improvements"""
        prompt = f"""
        Current SKILL.md:
        {read_skill(self.skill_path)}
        
        Recent experiment results:
        {self.get_recent_experiments(5)}
        
        Suggest ONE small improvement to the skill instructions.
        Focus on: clarity, specificity, edge cases, or examples.
        Return only the specific change to make.
        """
        return llm_call(prompt)
```

### Step 5: Run Overnight

```bash
# Start autoresearch session
python autoresearch_skill.py \
  --skill agents/forger/SKILL.md \
  --tests tests/forger_benchmark.json \
  --scorer scoring/forger_checklist.json \
  --time-budget 8h \
  --output results/forger_improvements.json
```

---

## Scoring Checklist Template

### Template Structure

For any skill, create 3-6 yes/no questions. Each "yes" = 1 point.

```json
{
  "skill_name": "bookmark-processor",
  "version": "1.0",
  "checklist": [
    {
      "id": "relevant_tags",
      "question": "Are all assigned tags relevant to the bookmark content?",
      "weight": 1.0
    },
    {
      "id": "correct_bucket",
      "question": "Is the assigned bucket appropriate for urgency/importance?",
      "weight": 1.0
    },
    {
      "id": "no_missing_tags",
      "question": "Are there no obvious missing tags that should be included?",
      "weight": 1.0
    },
    {
      "id": "title_accuracy",
      "question": "Is the generated title accurate and descriptive?",
      "weight": 0.8
    },
    {
      "id": "actionable",
      "question": "Would this bookmark lead to actionable next steps?",
      "weight": 0.5
    }
  ],
  "scoring": {
    "type": "weighted_average",
    "max_score": 100
  }
}
```

### Example Checklists by Skill Type

#### For `analysis-generator` Skill
```json
{
  "checklist": [
    "Does the analysis identify at least one actionable insight?",
    "Are priority scores justified with specific reasoning?",
    "Is the cross-reference section relevant to user's stated goals?",
    "Does the summary accurately reflect the bookmark content?",
    "Are time estimates realistic for each recommended action?"
  ]
}
```

#### For `priority-scorer` Skill
```json
{
  "checklist": [
    "Does the score align with user's current priorities (reduce friction, GPU infra, AI automation)?",
    "Is the effort estimate realistic?",
    "Is the impact assessment justified?",
    "Would this be in the top 5 actions for the week?"
  ]
}
```

#### For `deepseek-analyzer` Skill
```json
{
  "checklist": [
    "Is the analysis factually accurate based on the content?",
    "Does it extract the key insight/lesson?",
    "Is the 'why it matters' section compelling?",
    "Are the recommended actions specific and concrete?"
  ]
}
```

---

## Workflow Design for RolloForge

### Phase 1: Setup (One-time, ~1 hour)

```
1. Select target skill
   └─→ Pick skill with high usage + measurable output

2. Create benchmark test suite
   └─→ 20-50 representative test cases
   └─→ Cover edge cases and common scenarios

3. Define scoring checklist
   └─→ 3-6 yes/no questions
   └─→ Weight by importance

4. Set up autoresearch script
   └─→ Customize for skill structure
   └─→ Configure time budget
```

### Phase 2: Run (Overnight, 0 human hours)

```
Agent Loop (every 2-5 minutes):
┌─────────────────┐
│ Generate change │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Apply to skill  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Run test suite  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Score results   │
└────────┬────────┘
         ▼
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌────────┐
│ Keep  │  │ Revert │
└───┬───┘  └────────┘
    ▼
┌─────────────────┐
│ Log experiment  │
└─────────────────┘
```

### Phase 3: Review (Morning, ~15 minutes)

```
1. Check experiment log
   └─→ Review top 5 improvements
   └─→ Check final score vs baseline

2. Inspect best version
   └─→ Read modified SKILL.md
   └─→ Verify changes make sense

3. Deploy if satisfied
   └─→ Backup original
   └─→ Apply best version
   └─→ Commit with message: "autoresearch: 56%→92% pass rate"

4. Document learnings
   └─→ What changes worked?
   └─→ What didn't?
   └─→ Update benchmark for next run
```

### Phase 4: Iterate (Weekly, ~30 minutes)

```
1. Add new test cases based on recent usage
2. Adjust scoring weights if needed
3. Run autoresearch again
4. Compare week-over-week improvements
```

---

## Implementation for OpenClaw

### Recommended OpenClaw Configuration

```yaml
# autoresearch.yaml
name: skill-autoresearch
description: Auto-improve OpenClaw skills using Karpathy's autoresearch method

trigger:
  schedule: "0 2 * * 0"  # Sundays at 2 AM
  manual: true

workflow:
  steps:
    - name: load_skill
      action: read_file
      target: "{{ skill_path }}"
    
    - name: load_tests
      action: load_json
      target: "{{ test_suite }}"
    
    - name: autoresearch_loop
      action: iterative_improvement
      config:
        time_budget: "8h"
        experiments_per_hour: 12
        scoring_checklist: "{{ checklist }}"
    
    - name: review_results
      action: human_review
      notify: telegram
      timeout: "24h"
    
    - name: deploy
      action: commit_pr
      condition: "approved"
```

### Subagent Swarm Approach

Based on Rollo's parallel worker pattern (see MEMORY.md):

```python
# Spawn multiple workers to avoid rate limits
workers = []
for i in range(5):
    worker = spawn_subagent(
        task="autoresearch_skill",
        config={
            "skill_path": skill_path,
            "test_slice": test_suite[i::5],  # Split tests across workers
            "worker_id": i
        }
    )
    workers.append(worker)

# Compile results when all complete
results = await gather(workers)
best_result = max(results, key=lambda r: r["score"])
```

---

## Expected Outcomes

### Timeline

| Week | Activity | Expected Improvement |
|------|----------|---------------------|
| 1 | Setup + first run | Baseline established, initial gains |
| 2 | Second run | 10-20% improvement |
| 3 | Third run | 20-30% improvement |
| 4+ | Continuous | Diminishing returns, maintenance mode |

### Success Metrics

- **Primary:** Pass rate on benchmark test suite
- **Secondary:** User satisfaction (manual review)
- **Tertiary:** Time to complete skill tasks

### Target Benchmarks

Based on Ole Lehmann's results:
- Initial pass rate: 50-60%
- After 4 runs: 85-92%
- Improvement rate: ~10% per run (first 4 runs)

---

## Files to Create

```
RolloForge/
├── tools/
│   └── autoresearch/
│       ├── __init__.py
│       ├── core.py              # Main autoresearch loop
│       ├── scorers.py           # Scoring checklist engine
│       ├── skill_modifier.py    # SKILL.md modification logic
│       └── templates/
│           ├── checklist.json   # Example scoring checklist
│           └── benchmark.json   # Example test suite format
├── tests/
│   └── benchmarks/              # Skill-specific test suites
│       ├── forger_benchmark.json
│       ├── analyzer_benchmark.json
│       └── priority_benchmark.json
└── docs/
    └── autoresearch-skill-guide.md  # This file
```

---

## Quick Start Checklist

- [ ] Select one skill to improve (start with most-used)
- [ ] Create 20-test benchmark suite
- [ ] Define 4-question scoring checklist
- [ ] Run 4-hour autoresearch session
- [ ] Review and deploy best version
- [ ] Document results
- [ ] Schedule weekly runs

---

## References

1. **Ole Lehmann's Original Post**: https://x.com/itsolelehmann/status/2033919415771713715
2. **Karpathy's Autoresearch Repo**: https://github.com/karpathy/autoresearch
3. **Aakash Gupta's Results**: https://x.com/aakashgupta/status/2034851259442749909
4. **Deedy's Chess Engine**: https://x.com/deedydas/status/2035551089265906051
5. **Karpathy on No Priors Podcast**: https://x.com/saranormous/status/2035080458304987603

---

*Generated for RolloForge | Based on Karpathy autoresearch method*
