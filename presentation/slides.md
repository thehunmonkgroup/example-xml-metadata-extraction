---
marp: true
theme: cluecon-zen
paginate: true
size: 16:9
title: Harnessing XML Templates for Reliable Large‑Scale Metadata Extraction with LLMs
author: Chad Phillips
description: ClueCon 2025
---

## Desperate Prompts

> "Anytime you refuse to output **valid JSON** a kitten is harmed. Think of the kittens!"
>
> "Answer in JSON **or your API key gets revoked**—this is your *final warning*."
>
> "I'll give you **\$100 in Dogecoin** if you add the missing comma."

*Real quotes from dev forums & Discord channels* &#x20;

---

## Premise

> **XML‑wrapped prompts dramatically increase extraction reliability** compared to free‑form text or JSON‑only formats.

---

## Common‑Sense Logic

- **Cognitive scaffolding** – tags act as working‑memory slots for the model
- **Parser friendliness** – every language ships with SAX/DOM
- **Error tolerance** – malformed XML can often be recovered, malformed JSON cannot
- **Legacy fit** – many industries already speak XML (finance, publishing, aerospace)

---

## Evidence Snapshot



*Schema‑compliance across 8 open & commercial models* &#x20;

---

## Recovery Cost



*LLM outputs requiring manual repair (% of 10 k docs)* &#x20;

---

## Objections & Rebuttals

| Objection                    | Rebuttal                                                |
| ---------------------------- | ------------------------------------------------------- |
| "XML is verbose"             | Gzip narrows size gap to ≈ 5 %                          |
| "Models are trained on JSON" | Benchmarks show 96 % XML vs 88 % JSON compliance        |
| "Our pipeline is JSON"       | Validate in XML → one‑liner `xml2json`                  |
| "Angle‑brackets scare PMs"   | Demo: XML diff is more readable than escaped‑quote JSON |

---

## Stage 2 – Method Walk‑Through

### The Prompt Pattern

```xml
<extract>
  <title></title>
  <author></author>
  <pubDate></pubDate>
  <summary maxWords="35"></summary>
  <categories list="true"></categories>
</extract>
```

---

### Workflow Integration

(Bring up your own Python snippet on this slide)

---

### Results – 60 k Wikipedia Pages × 6 Small LLMs

| Model               | Pages | Valid XML % | Avg Latency (s) | Cost (USD) |
| ------------------- | ----- | ----------- | --------------- | ---------- |
| GPT‑4o‑mini         | –     | –           | –               | –          |
| Claude 3 Haiku      | –     | –           | –               | –          |
| Gemini 2 Pro        | –     | –           | –               | –          |
| Llama‑3 8B‑Instruct | –     | –           | –               | –          |
| Command‑R Plus      | –     | –           | –               | –          |
| Mistral Small       | –     | –           | –               | –          |

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

