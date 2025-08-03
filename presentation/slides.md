---
# vim: nowritebackup nobackup backupcopy=yes
marp: true
theme: cluecon-zen
paginate: true
size: 16:9
title: Harnessing XML Templates for Reliable Data Extraction with LLMs
author: Chad Phillips
description: ClueCon 2025
---

<div style="text-align: center">

## Harnessing XML Templates for Reliable Data Extraction with LLMs

### Chad Phillips, CTO, Apartment Lines

</div>

---

<style scoped>
section {
  font-size: 1.8em;
}
</style>

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

## The XML Template Pattern

```xml
<analysis>
  <reasoning>{Instructions}</reasoning>
  <field-name-one>{Instructions}</field-name-one>
  <field-name-two>{Instructions}</field-name-two>
  <field-name-three>{Instructions}</field-name-three>
</analysis>
```

---

## XML FTW

* **Cognitive Scaffolding:** Tags guide the model's process.
* **Training Data Familiarity:** LLMs are "native speakers" of XML.
* **Robust Extraction from Text:** Easily located in noisy LLM output.
* **Mature Schema Validation:** Can be verified against a widely-supported schema (XSD).

---

## The Prompt

- Role / Rules
- Task
- Definitions
- Output format (the XML template)

### Context, context, context...

---

## Workflow Integration

* **Load Source Data** (e.g., Wikipedia pages)
* **Generate Prompt** with the XML template.
* **Call LLM API** (any provider).
* **Extract & Parse** the `<analysis>` block.
* **Validate & Store**

*Full example code: github.com/thehunmonkgroup/example-xml-metadata-extraction*

---

<style scoped>
section {
  font-size: 2em;
}
table tr:last-child td {
  border-top: 2px solid #333;
  font-weight: bold;
}
</style>

#### Results – 60 k Wikipedia Pages

| Model               | Pages  | Success | Fail | Retry | Success % | Cost (USD) |
| :------------------ | -----: | ------: | ---: | ----: |  -------: | ---------: |
| Llama 4 Scout       | 10,000 |  10,000 |    0 |    26 |   100.00% |      $2.99 |
| Gemini 2.5 Flash    | 10,000 |   9,999 |    1 |    15 |    99.99% |     $14.30 |
| Phi 4               | 10,000 |   9,991 |    9 |    44 |    99.91% |      $1.84 |
| Qwen 3 8B           | 10,000 |   9,953 |   47 | 1,154 |    99.53% |      $2.05 |
| Ministral 8B        | 10,000 |   9,873 |  127 |   550 |    98.73% |      $2.01 |
| GPT 4.1 Nano        | 10,000 |   9,974 |   26 |   359 |    99.74% |      $2.98 |
| Totals              | 60,000 |  59,790 |  210 | 2,148 |    99.65% |     $26.17 |

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

## Tips & Tricks

* UUID retries (XML attribute + tenacity)
* Fallback to smarter model
* `<![CDATA[ ]]` wrapping
* More complex data model == smarter model
* **XSD** data validation

---

## In closing

> **Stop bribing your LLM. Start giving it a clear blueprint.**

> XML Templates are a reliable engineering pattern.

* Model-agnostic
* Works well with smaller, cheaper LLMs.
* Delivers near-100% data extraction

---

<div style="text-align: center">

# Questions

![Questions](./questions.png)

*github.com/thehunmonkgroup/example-xml-metadata-extraction*
</div>
