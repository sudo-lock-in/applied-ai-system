# PawPal+ Model Card

## 1. Limitations & Biases

**System Limitations:**

- **Time-Based Scheduling Only** - The scheduler only considers available time and task duration; it cannot adapt to real-world interruptions (vet emergencies, owner illness, weather delays)
- **No Learning from History** - Each daily plan is generated fresh; the system doesn't learn which schedules owners actually approve/reject to improve future suggestions
- **Assumes Fixed Pet Profiles** - Pet data (age, breed, needs) remains static; the system doesn't account for seasonal changes or aging (e.g., senior dogs needing more rest)
- **No Cost/Resource Constraints** - Scheduler doesn't consider supply constraints (e.g., limited dog shampoo) or travel time between locations

**Potential Biases:**

- **Priority Bias** - HIGH priority tasks always come first; might miss urgent MEDIUM tasks that better serve pet welfare
- **Owner Availability Bias** - System trusts owner's reported available time but doesn't validate realistic capacity (people often overestimate)
- **One-Size-Fits-All Validation** - Rules like "all high-priority tasks must fit" work for busy owners but may over-constrain for flexible ones

---

## 2. Misuse Prevention & Safety

**Potential Misuse:**

- Owner could enter unrealistic high-priority tasks (e.g., 300 minutes of exercise/day) → system marks as impossible but doesn't prevent user deception
- Owner could ignore pet welfare warnings → system can't force human to approve realistic plans

**Prevention Mechanisms:**

1. **Human-In-The-Loop Approval** - Every schedule requires explicit owner approval before implementation; system never auto-executes
2. **Validation Checkpoints** - 6 critical constraints validated before human review (time, conflicts, pet welfare, feasibility)
3. **Explainability** - Every scheduling decision includes reasoning; owner can identify if logic is sound
4. **Audit Trail** - All decisions logged to JSONL; enables future review/investigation if pet welfare issues arise
5. **Rejection Option** - Owner can reject and regenerate; system doesn't penalize users who disagree

---

## 3. Testing Surprises & Reliability Findings

**Surprise #1: Recurring Task Explosion**
- Expected: Monthly tasks repeat once/month cleanly
- Reality: Edge case where Feb-starting monthly tasks don't align with 31-day months; created cascading errors
- Finding: Deterministic scheduling is fragile at boundaries; simple calendar logic needs defensive programming

**Surprise #2: Validation Catches More Than Scheduling**
- Expected: Scheduling logic would be the main value
- Reality: ~70% of user-facing bugs were caught by validation layer, not scheduling layer
- Finding: For safety-critical systems, validation > generation


---

## 4. AI Collaboration

**Helpful AI Suggestion:**

**Context:** Stuck on how to structure recurring task expansion (daily/weekly/monthly logic)

**AI Suggestion:** "Generate all task instances for the week upfront, then filter to available slots rather than deciding on-the-fly"

**Why It Worked:** Separated concerns cleanly (generation vs. packing), made debugging easier, enabled batch validation

**Implementation:** Now recurring tasks are all generated first, then validation runs once on full set → caught 3 edge cases in testing

---

**Flawed AI Suggestion:**

**Context:** Performance was slow (~500ms for 20-task schedules)

**AI Suggestion:** "Add caching with memoization and parallel processing using multiprocessing library"

**Why It Failed:** 
- Caching didn't help (each day's schedule is unique)
- Multiprocessing added 200ms overhead just to spawn processes
- Root cause was actually inefficient validation loop (checking constraints 5x per task)

**My Verification:** Tested the AI's suggestion, saw no improvement, profiled the code myself, found the real bottleneck in validation loop. Simple refactor (check constraints once) reduced time from 500ms to 45ms.

**Lesson:** AI suggested sophisticated solutions; often the fix is simpler