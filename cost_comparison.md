# Cost comparison: up to 89.1% lower in an illustrative workflow

**A lightweight parent, a small router, and task-specific worker models can substantially reduce token-equivalent cost.** In the detailed example below, the routed configuration costs **$0.480**, compared with an **Astra-only work baseline of $4.392**: a **89.1% reduction after rounding**.

This is a **static price comparison using anonymized observed token counts**, not a head-to-head model benchmark. The alternative configurations were not rerun. Token counts, output lengths, and cache hits are held constant when changing model prices. The result does **not** establish equal quality, equal latency, or a 89.1% reduction in subscription-limit consumption. “Up to 89.1%” describes the best configuration evaluated in this example, not a general performance guarantee.

## Example request and execution

The following request is a fictionalized description of a three-part administrative and technical workflow:

> Check whether an acknowledgement has already been sent for a contributor's update; send it only if necessary. Compare the contributor's technical report with the internal project design. Then summarize the current work queue.

The work must remain in order. A router selects a routine profile for the acknowledgement check, an analytical profile for the technical comparison, and the routine profile again for the queue summary. Workers share a persistent thread so that later stages can use earlier findings. The parent assistant receives the completed report and presents it to the user.

In this example, the acknowledgement already existed: the first stage verified the previous effect without sending a duplicate. Its token counts should not be read as a measured benchmark of a fresh send operation.

```text
User request
  -> Router: classify the ordered tasks
  -> Routine worker: verify acknowledgement status
  -> Analytical worker: compare technical materials
  -> Routine worker: summarize the work queue
  -> Parent: deliver the final formatted report
```

No real request text, contributor identity, research subject, document content, organization, account data, message ID, session ID, or private filesystem path is included here. Only aggregate token measurements and generalized task descriptions are published.

## What the token measurements include

The counts include the entire model interaction for each stage, not just the final prose:

- Instructions and previous conversation supplied to the model.
- File contents and tool results read during the task.
- Repeated context input across successive model responses.
- Generated tool calls, intermediate outputs, and final reports.
- Reported reasoning tokens, counted within output tokens rather than added again.
- Router overhead and the parent's final delivery overhead.

Resumed sessions can report cumulative usage. The measurements below subtract the preceding session totals; they do not sum overlapping lifetime counters. Earlier tasks, setup, testing, and the subsequent cost analysis are excluded.

| Stage | Model responses | Input tokens | Cached input subset | Noncached input | Output tokens |
|---|---:|---:|---:|---:|---:|
| Route the request | 1 | 18,765 | 0 | 18,765 | 145 |
| Verify acknowledgement | 3 | 245,572 | 159,872 | 85,700 | 770 |
| Compare technical materials | 11 | 1,177,599 | 1,044,608 | 132,991 | 3,572 |
| Summarize work queue | 2 | 270,216 | 219,264 | 50,952 | 1,091 |
| Read and deliver report | 2 | 296,415 | 155,264 | 141,151 | 1,179 |
| **Total** | **19** | **2,008,567** | **1,579,008** | **429,559** | **6,757** |

The three worker stages made 13 tool calls. Their returned content and subsequent model processing are included above. Of the 6,757 output tokens, 242 were reported as reasoning tokens. A million cumulative input tokens does not mean a million-token document or a single million-token prompt: the same conversation can be read repeatedly.

## Pricing assumptions

The comparison uses the following **Standard, short-context API rates in USD per million tokens**, checked against the official pricing table on 2026-10-04. Prices and available models can change. These are a common accounting basis, not a reconstruction of an invoice. Fast/Ultrafast, long-context premiums, regional uplifts, external service charges, and local compute costs are not included.

| Model | Noncached input | Cached input | Output |
|---|---:|---:|---:|
| GPT-6 Astra | $10.00 | $1.00 | $50.00 |
| GPT-6.1 Sol | $2.00 | $0.10 | $10.00 |
| GPT-6 Luna | $0.10 | $0.01 | $0.50 |

Source: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing).

For a stage with input tokens `I`, cached input tokens `C`, and output tokens `O`:

```text
cost = ((I - C) * input_rate + C * cached_input_rate + O * output_rate) / 1,000,000
```

Cache-write token counts were zero in the observed records. Reasoning effort is not a separate multiplier in this calculation: any extra reasoning is represented by output-token usage. Holding that usage constant when changing models is an explicit limitation of this static comparison.

## Detailed comparison

The observed configuration used Sol low / medium / low for the three worker stages, a Sol low router, and an Astra parent. The recommended alternative keeps the router on **Sol low**, keeps the technical comparison on **Sol medium**, and uses **Luna for the two routine stages and final delivery**.

| Stage | Observed configuration | Observed-token cost | Recommended configuration | Same-token cost |
|---|---|---:|---|---:|
| Router | Sol low | $0.038980 | Sol low | $0.038980 |
| Acknowledgement verification | Sol low | $0.195087 | Luna low | $0.010554 |
| Technical comparison | Sol medium | $0.406163 | Sol medium | $0.406163 |
| Work queue summary | Sol low | $0.134740 | Luna low | $0.007833 |
| Parent report delivery | Astra | $1.625724 | Luna | $0.016257 |
| **Total** | | **$2.400694** | | **$0.479787** |

For example, acknowledgement verification on Luna is:

```text
(85,700 * $0.10 + 159,872 * $0.01 + 770 * $0.50) / 1,000,000
= $0.01055372
```

The expensive observed parent delivery had a large noncached conversation input. Consequently, changing only the parent model already has a substantial effect in this particular example. A shorter or better-cached parent conversation would change that effect.

## Where the 89.1% figure comes from

To avoid inflating the Astra baseline with routing overhead that direct execution would not need, the baseline includes **only the three substantive worker stages**, repriced at Astra rates. It excludes the router and separate parent relay entirely.

| Substantive work repriced as Astra | Cost |
|---|---:|
| Acknowledgement verification | $1.055372 |
| Technical comparison | $2.553118 |
| Work queue summary | $0.783334 |
| **Astra-only work baseline** | **$4.391824** |

The routed alternative includes **all five stages**, including router and parent overhead:

```text
Routed total = $0.038980 + $0.01055372 + $0.40616280 + $0.00783334 + $0.01625724
             = $0.47978710

Reduction = 1 - ($0.47978710 / $4.39182400)
          = 89.0754% ≈ 89.1%

Absolute difference = $3.91203690 per example workload
```

This baseline is conservative **about routing and relay overhead only**. It is not a lower or upper bound on what Astra would actually consume. A direct Astra run could make different tool calls, use a different amount of reasoning, reuse context differently, or avoid redundant reads.

| Configuration | Total cost | Lower than observed configuration | Lower than Astra-only work baseline |
|---|---:|---:|---:|
| Observed: Astra parent + Sol workers | $2.401 | — | 45.3% |
| Luna parent + all original Sol workers | $0.791 | 67.0% | 82.0% |
| **Luna parent + Luna routine workers + Sol analytical worker** | **$0.480** | **80.0%** | **89.1%** |

The router remains Sol low in every row. This example makes no claim about savings from moving the router itself to Luna.

## Messages, credits, and subscription limits

There was one user request, but 19 internal model responses. Routing does not make model work free, and it does not necessarily reduce token counts or the number of calls. The principal saving illustrated here is **assigning lower token prices to routine work while retaining a more capable model for analysis**.

Using published Standard paid-credit rates, the observed configuration corresponds to about **60.02 credits**, the recommended configuration to **11.99 credits**, and the Astra-only work baseline to **109.80 credits**. These are rate-card equivalents, not measured credit deductions. Source: [OpenAI pricing and credit rates](https://learn.chatgpt.com/docs/pricing).

Included subscription allowances are not determined solely by those credit prices. Therefore:

- Do not advertise this example as “89.1% less subscription usage.”
- Do not convert the saving into a guaranteed number of additional messages or tasks.
- Do not interpret unchanged rounded usage indicators as zero consumption.
- Actual allowance savings require sufficiently precise, isolated account usage measurements.

## Applying the result

Use a lightweight parent for report delivery and smaller workers for bounded, well-defined operations. Preserve stronger profiles for technical judgment, conflicting evidence, and complex planning. Validate smaller-model quality before adopting the alternative configuration: authorization, duplicate-effect checks, result validation, and failure handling remain necessary regardless of token price.

**Suggested public claim:** “In an anonymized static token-price comparison, task-based routing with a lightweight parent reduced estimated cost by up to 89.1% against an Astra-only work baseline, including routing and relay overhead. Actual cost, quality, and subscription usage vary.”
