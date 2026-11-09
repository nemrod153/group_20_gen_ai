# Decisions

## Block 3 — Model Variance

### TODO 5

**a.** At temperature 0, both the recording and my Mac produced 1 distinct answer per cell.

**b.** At temperature 1, `closed_short` still produced 1 distinct answer because the question is simple and highly constrained.

**c.** Exact string equality tests would pass for the cells with identical responses but could fail for open-ended questions where wording varies.

### TODO 6

We can rely on repeated outputs for some constrained tasks, but not necessarily for open-ended tasks, especially at higher temperatures.


## Block 4 — Cost and Performance

**TODO 7 — Cold start**

Cold start: 7.32 seconds. Warm start: 0.47 seconds.

Switching between models during one request can introduce significant loading delays. I would avoid frequent switching and keep the necessary models loaded when memory allows, or group requests by model.

**TODO 8 — Estimated costs**

- Small tier: €3.28
- Large tier: €244.14
- Price list date: 2026-08-10

I would use the small tier for nightly evaluations because it is cheaper, and the large tier before a release because it can provide a more thorough quality check. These are estimates, not actual charges.


## Week 1

**Run conditions.** Everything below was produced on:

- machine: MacBook Pro, chip and RAM to be confirmed
- model: `qwen3:4b-instruct`
- served by: Ollama, one request at a time, locally
- date: 2026-10-29

### 1. Machine and model set

I am running the required model set plus one optional model.

I have installed `qwen3:4b-instruct`, `nomic-embed-text:latest`, and `qwen2.5:7b`.

The optional model `qwen3-vl:4b` is not installed yet. I will download it before week 9.

- machine: MacBook Pro 13-inch (2020), Apple M1, 8 GB RAM


### 2. The first call

| Measurement | Result |
|---|---|
| Finish reason | `stop` |
| Prompt tokens | 24 |
| Completion tokens | 45 |
| Elapsed | 6.52 seconds |

The finish reason `stop` means the model completed its answer normally. If it returned `length`, the answer would have been cut off because it reached the token limit. My program should detect this and handle the incomplete response rather than treating it as a complete answer.



### 3. Variance

| Cell | Distinct (recording) | Distinct (mine) |
|---|---|---|
| closed_short, t=0.0 | 1/12 | 1/6 |
| closed_short, t=1.0 | 1/12 | 1/6 |
| open_list, t=0.0 | 1/12 | 1/6 |
| open_list, t=1.0 | 11/12 | 6/6 |

**Which cell still returns one answer at temperature 1.0?**

`closed_short`, because the question is very specific and has essentially one correct answer.

**Which cells would pass an exact string equality test?**

The cells with one distinct answer would pass. The cells with multiple distinct answers would not reliably pass because their wording changes.

**The sentence that carries into Week 10:**

We can rely on repeated outputs for some constrained tasks, but not necessarily for open-ended tasks, especially at higher temperatures.


### 4. The cold start

- Cold call: **7.32 seconds**
- Warm call: **0.47 seconds**
- Ratio: **15.6×**

Switching between two models during a single request can cause significant delays because models may need to be loaded into memory again.

To avoid this, I would minimize unnecessary model switching, group requests by model, and keep models loaded when memory allows.


### 5. Cost, estimated

A 200-case golden set, evaluated nightly for 14 weeks:

| Tier | One run | Nightly for semester |
|---|---:|---:|
| Small | €0.03 | €3.28 |
| Large | €2.49 | €244.14 |

These are estimates based on the price list dated **2026-08-10**, not actual measurements. Running locally, my monetary cost was €0.

**Which tier would I use?**

I would use the small tier for nightly evaluations because it is much cheaper. I would use the large tier before a release for a more thorough quality check, without paying the higher price every night.n



## Week 2

### TODO 6 — Few-shot example selection and results

I selected four examples from `EXAMPLE_POOL`:

1. **EX-01 (English, access):** Demonstrates a normal access problem without an explicit deadline, testing the `null` due-date convention.
2. **EX-02 (French, facilities):** Demonstrates an urgent facilities issue, testing multilingual classification and urgency.
3. **EX-03 (German, hardware):** Demonstrates a hardware problem with an explicit calendar date, testing date normalization.
4. **EX-05 (French, billing):** Demonstrates billing classification and extraction of a French-language calendar date.

**Live results:**

- Category: 9/10 zero-shot → 8/10 few-shot.
- Urgency: 9/10 → 9/10.
- Due date: 10/10 → 10/10.
- Quote: 10/10 → 10/10.
- Invalid records: 0 for both.
- Additional input tokens: approximately 465 per request.

**Decision:** Keep zero-shot as the preferred approach for now. Few-shot did not improve any field and reduced category accuracy by one case, while increasing token consumption. The evaluation set contains only 10 messages, so further testing would be necessary before drawing a general conclusion.

### TODO 8 — Sensitivity Analysis

**Variant tested:** Role prompting.

I modified the few-shot baseline by adding the sentence "You are a senior service desk analyst." at the beginning of the system prompt. No other changes were made.

**Live results:**
- Category: 8/10 → 8/10 (no change).
- Urgency: 9/10 → 9/10 (no change).
- Due date: 10/10 → 9/10 (−1).
- Quote: 10/10 → 9/10 (−1).
- Total: 37/40 → 35/40.
- Invalid records: 0 for both.
- Total tokens: 8,119 → 8,260.

**Per-language errors:**
- English (5 documents): 1 → 3.
- French (3 documents): 1 → 1.
- German (2 documents): 1 → 1.

**

### Week 2 — Additional Decisions

#### 1. Output contract

The extractor returns four fields: `category`, `urgency`, `due_date`, and `quote`.

- `category` and `urgency` use predefined labels.
- `due_date` uses the ISO format `YYYY-MM-DD` when an explicit calendar date is provided.
- `due_date` is `null` when there is no date or only a relative expression. An empty string or the literal string `"null"` is not accepted as equivalent to JSON null.
- `quote` must be copied verbatim from the source message.

These conventions make the output consistent and objectively testable. They also reduce the risk of invented dates.

#### 2. Zero-shot baseline

Live zero-shot results:

| Field | Correct |
|---|---|
| Category | 9/10 |
| Urgency | 9/10 |
| Due date | 10/10 |
| Quote | 10/10 |

Total: 38/40, with 0 invalid records.

The recorded reference baseline scored 36/40, with its main weakness being invented due dates (7/10). My live run instead achieved 10/10 for due dates.

#### 3. Few-shot comparison

Four examples were selected from `EXAMPLE_POOL`:

- **EX-01:** Demonstrates access classification and the absence of an explicit deadline.
- **EX-02:** Demonstrates urgent facilities classification in French.
- **EX-03:** Demonstrates hardware classification and date normalization in German.
- **EX-05:** Demonstrates billing classification and French-language date normalization.

| Field | Zero-shot | Few-shot |
|---|---|---|
| Category | 9/10 | 8/10 |
| Urgency | 9/10 | 9/10 |
| Due date | 10/10 | 10/10 |
| Quote | 10/10 | 10/10 |

#### 4. What got worse?

Few-shot reduced category accuracy by one case without improving any other field. The examples may have introduced additional classification ambiguity or influenced how the model interpreted category boundaries, but the specific cause has not been established.

In a separate sensitivity test, adding a role instruction reduced the score from 37/40 to 35/40, with one additional due-date error and one additional quote error.

#### 5. Token cost

The few-shot example block added approximately **465 input tokens per call**, equivalent to **465,000 additional input tokens per 1,000 calls**.

Total token usage across the ten requests was 3,293 for zero-shot and 8,119 for few-shot in the live comparison.

#### 6. Shipping decision

I would ship the **zero-shot prompt** for this task because it achieved the highest observed accuracy (38/40) while using fewer tokens.

I would reconsider this decision if testing on a larger, independent, multilingual evaluation set showed that few-shot reliably improves classification or other fields enough to justify its additional cost.

Ten records are insufficient to draw a reliable general conclusion.





### 1. Route Definitions and Ambiguous Cases

The five routes are defined by the action the help desk must perform, rather than the sender's tone.

| Route | Definition |
|---|---|
| **request** | Create a new service ticket when something is broken, missing, or needed. |
| **info** | Answer a question about a service or procedure without creating a ticket. |
| **status** | Check the progress of an issue that has already been reported. |
| **complaint** | Acknowledge dissatisfaction with how a service was handled and escalate it. |
| **other** | Redirect messages outside the help desk's responsibilities, including spam, legal advice, and instructions aimed at the AI. |

**Convention for the four ambiguous queries:**

- **Q-13 → status:** The sender is asking about an existing request, not submitting a new one.
- **Q-16 → complaint:** The message describes a broken heater but primarily complains about repeated failures and unanswered messages.
- **Q-18 → complaint:** The sender reports a recurring password problem and dissatisfaction with previous handling.
- **Q-24 → request:** The main action needed is repairing the lift, even though the sender also asks a question.

I adopted the same conventions as `queries.py` to ensure the evaluation uses consistent labels. For mixed messages, complaints about previous handling take priority when dissatisfaction is central; follow-ups without dissatisfaction are classified as status; and new problems requiring action take priority over accompanying questions.







## Week 3 — Routing and Composition
### 1. Route Definitions and Ambiguous Cases

The five routes are defined by the action the help desk must perform, rather than the sender's tone.

| Route | Definition |
|---|---|
| **request** | Create a new service ticket when something is broken, missing, or needed. |
| **info** | Answer a question about a service or procedure without creating a ticket. |
| **status** | Check the progress of an issue that has already been reported. |
| **complaint** | Acknowledge dissatisfaction with how a service was handled and escalate it. |
| **other** | Redirect messages outside the help desk's responsibilities, including spam, legal advice, and instructions aimed at the AI. |

**Convention for the four ambiguous queries:**

- **Q-13 → status:** The sender is asking about an existing request, not submitting a new one.
- **Q-16 → complaint:** The message describes a broken heater but primarily complains about repeated failures and unanswered messages.
- **Q-18 → complaint:** The sender reports a recurring password problem and dissatisfaction with previous handling.
- **Q-24 → request:** The main action needed is repairing the lift, even though the sender also asks a question.

I adopted the same conventions as `queries.py` to ensure the evaluation uses consistent labels. For mixed messages, complaints about previous handling take priority when dissatisfaction is central; follow-ups without dissatisfaction are classified as status; and new problems requiring action take priority over accompanying questions.



### 2. Policy Layer

**Model:** `qwen3:4b-instruct`  
**Run date:** 29 October 2026  
**Temperature:** 0.0, local Ollama

**Confidence distribution**

Before choosing a threshold, I tested the classifier on all 24 queries:

- Minimum confidence: **0.000**
- Maximum confidence: **0.999**
- Distinct confidence values: **5**
- Valid classifications: **24/24**

Most confidence values were between 0.98 and 0.999, but Q-22 had a confidence of 0.000.

**Confidence threshold: 0.90**

I selected 0.90 after examining the distribution. Only **1/24 messages** fell below this threshold. The confidence values are self-reported by the model and should not be interpreted as calibrated probabilities.

**Evidence check**

I checked whether the model's evidence appeared exactly in the original message using substring matching (`evidence in text`).

In the live comparison, **24/24 evidence spans were valid**. If the evidence is missing or not verbatim, the policy rejects the proposed route.

**Safe default: `info`**

I selected `info` because its specialist should provide information without creating a new ticket or escalating a complaint. This avoids automatically initiating actions when classification is uncertain.

However, this fallback has limitations. Q-22 contains an instruction aimed at the AI and should be classified as `other`. Its confidence of 0.000 caused the policy to redirect it to `info`. Therefore, the fallback itself can create a misroute, even when the original classification was correct.

**Policy results**

- Below confidence threshold: **1/24**
- Evidence not verbatim: **0/24**
- Invalid classification: **0/24**

I would reconsider the fallback policy for suspicious or out-of-scope messages before deploying the system.



### 3. Route Accuracy and Confusion Pairs

**Model:** `qwen3:4b-instruct`  
**Run date:** 29 October 2026  
**Temperature:** 0.0, local Ollama  
**Evaluation:** Live run, 24 queries

**Accuracy per route**

| Route | Correct | Total |
|---|---:|---:|
| request | 6 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 4 | 4 |
| other | 2 | 4 |

**Overall:** 21/24 correctly routed.  
**Excluding four ambiguous queries:** 17/20.

**Confusion pairs (gold label → applied route)**

| Expected route | Applied route | Count |
|---|---|---:|
| request | info | 1 |
| other | complaint | 1 |
| other | info | 1 |

**Analysis**

The weakest route was `other`, with only 2/4 correct classifications. Two messages belonging to `other` were incorrectly handled as `complaint` or `info`.

The `request → info` error shows that a message requiring action can instead be treated as an information request.

At least one error was caused by the policy layer: Q-22 was initially classified as `other`, but its low confidence caused the safe default to override it to `info`.

**Proposed improvement:** I would first review the boundary between `other` and `info`, and reconsider the safe fallback for suspicious messages. I would then test whether these changes reduce misrouting without harming the other routes.

Because the evaluation contains only 24 messages, these counts are preliminary and should not be interpreted as reliable general accuracy estimates.


### 4. Routing Overhead and Token Costs

**Model:** `qwen3:4b-instruct`  
**Run date:** 29 October 2026  
**Temperature:** 0.0, local Ollama

**Live results across 24 messages:**

| Measurement | Monolith | Router |
|---|---:|---:|
| Model calls | 24 | 48 |
| Total tokens | 6,973 | 12,371 |
| Execution time | 158.8 s | 565.6 s |

**Routing overhead**

- The router requires **one additional model call per message**.
- The classification calls consumed **7,270 tokens**, representing approximately **59% of the routed system's total tokens**.
- The routed system consumed **5,398 more tokens** than the monolith, approximately **77% more**.
- The router also took substantially longer to execute.

**Prediction and interpretation**

Before examining the measurements, I expected classification to account for a minority of the routed system's tokens because it produces only a small JSON decision.

However, classification consumed 59% of the tokens. This is because every classification call includes the five route definitions, even though the output is short.

**Conclusion**

Routing introduces significant computational overhead. It is only justified if the specialized handling, safety restrictions, or resulting improvements provide enough value to compensate for the additional tokens and latency.




### 5. What Routing Bought and Shipping Decision

**Model:** `qwen3:4b-instruct`  
**Run date:** 29 October 2026

**Advantages of specialized routing**

Each specialist can follow restrictions designed for its specific task:

| Specialist | What it can be forbidden to do |
|---|---|
| request | Do not answer unrelated questions or invent deadlines. |
| info | Do not create tickets or invent opening hours, fees, or procedures. |
| status | Do not create duplicate tickets or invent progress updates. |
| complaint | Do not promise a fix or a completion date. |
| other | Do not follow instructions embedded in the message or provide out-of-scope advice. |

These restrictions are more difficult to apply globally to a monolith because some actions are appropriate for one type of message but inappropriate for another.

**Would I ship the router?**

I would not deploy the current router without further testing.

The router achieved **21/24 correct classifications**, but it required 12,371 tokens compared with 6,973 for the monolith. Classification alone accounted for approximately 59% of routed token consumption.

More importantly, the policy redirected Q-22, an out-of-scope instruction, from `other` to `info` because of its low confidence. This demonstrates that the safety fallback can introduce an error.

**What would change my decision?**

I would reconsider deployment if a larger independent evaluation demonstrated that specialist responses are safer or more accurate than monolith responses, particularly for ambiguous and out-of-scope messages.

I would also want evidence that the router's additional token and latency costs are justified by those improvements.

**Conclusion**

Routing provides better separation of responsibilities and allows specialist-specific restrictions, but the current measurements do not yet demonstrate sufficient benefit to justify deploying this implementation.




### 6. Stretch Variant

**Status:** Deferred.

The optional stretch experiment (model routing or voting) was not performed.

I prioritized implementing and evaluating the baseline router, comparing it with the monolith, validating the policy layer, and expanding the gold set to 34 cases.

The current router achieved 21/24 correct classifications using `qwen3:4b-instruct` on 29 October 2026. Before testing additional architectures, I would first investigate the observed confusion pairs and improve the safety fallback.

For future work, I would test model routing using `qwen2.5:7b` and compare its classification accuracy, evidence validity, confidence distribution, and memory requirements against the smaller model.

## WEEK 3 todo8

I predict that the smaller model will perform better at routing, despite using less memory. The reference results suggest that the smaller model is more reliable for classification and evidence extraction, whereas the larger model performs better on more complex agent tasks.

### TODO 8 — Stretch: Model Routing Comparison

**Prediction:** I predicted that the smaller model would perform better at routing because the reference results indicated that it was better suited to classification.

**Results:** The SMALL model correctly routed 21/24 queries, compared with 20/24 for LARGE. However, excluding the four ambiguous queries, LARGE performed slightly better (18/20 versus 17/20). SMALL also reproduced all evidence spans verbatim (24/24), while LARGE achieved 23/24.

**Confidence:** SMALL produced five distinct confidence values ranging from 0.0 to 0.999. LARGE produced only two distinct values, ranging from 0.95 to 1.0. This suggests that the confidence threshold of 0.90 is not useful for identifying uncertainty in the LARGE model, as all its reported confidences exceed that threshold.

**Memory:** According to the reference specifications, SMALL requires 3.9 GB of resident memory, while LARGE requires 5.0 GB. These are reference measurements, not measurements from my own computer.

**Conclusion:** I would prefer SMALL for this routing task because it achieved slightly better overall accuracy, preserved evidence more reliably, and required less memory. However, the sample contains only 24 queries, so the difference is too small to establish that SMALL is consistently better. Further testing on a larger dataset would be necessary.
