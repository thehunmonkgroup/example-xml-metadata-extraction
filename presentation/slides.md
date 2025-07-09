---
# vim: nowritebackup nobackup backupcopy=yes
marp: true
theme: cluecon-zen
paginate: true
size: 16:9
title: Harnessing XML Templates for Reliable Large‑Scale Metadata Extraction with LLMs
author: Chad Phillips
description: ClueCon 2025
---

## Consistent Structured Output is a Problem...

> "Anytime you refuse to output **valid JSON** a kitten is harmed. Think of the kittens!"
>
> "Answer in JSON **or your API key gets revoked**—this is your *final warning*."
>
> "I'll give you **\$100 in Dogecoin** if you add the missing comma."

### ...when we resort to this...

---

## Premise

> **XML templates offer a straightforward path to reliable, low-cost data extraction, independent of the underlying LLM.**

---

## XML FTW

- **Cognitive Scaffolding:** Tags guide the model's reasoning process.
- **Training Data Familiarity:** LLMs are "native speakers" of XML.
- **Robust Extraction from Text:** Easily located in noisy LLM output.
- **Mature Schema Validation:** Can be verified against a mature, widely-supported schema (XSD).

---

## Objection:

> XML is too verbose & costs more tokens.

### We trade verbosity for reliability, context windows grow while inference costs drop.

---

## Objection:

> Why not use native JSON modes?

### XML templates are portable and model-agnostic, working across proprietary and open-source LLMs.

---

## Objection:

> "JSON is a better fit for our data model & pipeline."

### The XML is transient, optimize for reliable communication *from* the LLM, then convert downstream.

---

## Objection:

> This is just good prompting, not an XML feature.

### Yep. And XML is a superior format for this kind of structured prompting.

---

## Stage 2 – Method Walk‑Through

### The Prompt Pattern

```xml
<analysis>
  <reasoning>{Instructions}</reasoning>
  <field-name-one>{Instructions}</field-name-one>
  <field-name-two>{Instructions}</field-name-two>
  <field-name-three>{Instructions}</field-name-three>
</analysis>
```

---

### Workflow Integration

(Bring up your own Python snippet on this slide)

---

### Results – 60 k Wikipedia Pages × 6 Small LLMs

| Model               | Pages  | Success | Fail | Retry | Success % | Cost (USD) |
| :------------------ | -----: | ------: | ---: | ----: |  -------: | ---------: |
| Gemini 2.5 Flash    | 10,000 |   9,999 |    1 |    15 |    99.99% |     $14.30 |
| GPT 4.1 Nano        | 10,000 |   9,974 |   26 |   359 |    99.74% |      $2.98 |
| Llama 4 Scout       | 10,000 |  10,000 |    0 |    26 |   100.00% |      $2.99 |
| Phi 4               | 10,000 |         |      |       |           |            |
| Qwen 3 8B           | 10,000 |         |      |       |           |            |
| Ministral 8B        | 10,000 |         |      |       |           |            |

*Stub: replace dashes with real run data when available*

---

## Stage 3 – Tips & Tricks

1. Use **attributes** for soft constraints (`maxWords`, `list="true"`).
2. **Temp 0 + low max\_tokens** to minimise truncation.
3. Retry policy: exponential back‑off + "shallow reprompt" comment.
4. Chunk ≤ ⅓ context window; parallelise small models for throughput.
5. Validate with **XSD** before DB insert.
6. Log raw completions for drift analysis.
7. Fine‑tune LoRA for cost drop once prompt stabilises.

---

## Key Takeaways

> **One XML tag in your prompt can remove 90 % of post‑processing pain.**

- Higher success rates than JSON
- Easier, safer parsing at scale
- Works even with cheap small models

---

## Thank You

**Questions?**

*Slides: will be available after the talk*

