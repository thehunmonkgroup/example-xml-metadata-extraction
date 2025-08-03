# Slide Talking Points

This document contains talking points for each slide in the presentation.

---

### Slide 1: Title Slide

* Before I get started with the presentation, I want to take a moment to set the context
* Across the AI landscape, a lot of attention is being paid to 'frontier AI' -- top performing models, AGI, and ASI
* In addition, there's an idea that someday we'll have 'intelligence to cheap to meter'
* What's gotten a lot less attention is that we've already achieved 'intelligence almost too cheap to meter'
* What I'm talking about today is an example of this less-hyped intelligence
* I'm hoping it will inspire some new kinds of creativity and productivity, especially for business use cases

---

### Slide 2: Consistent Structured Output is a Problem...

* I'm guessing some of you can relate to the approaches illustrated in this slide -- lord knows I've done it.
* This is bribery, and it underscores a fundamental challenge when trying to extract value from LLMs, especially in data pipelines: how do we reliably get structured data from a non-deterministic resource?

---

### Slide 3: Premise

* My premise today is simple: Using XML templates in your prompts is a easy way to get highly reliable, low-cost data extraction, and it's a method that works across almost any LLM you can find.

---

### Slide 4: The XML Template Pattern

* Here's what this looks like in practice.
* You have a single root tag, an optional `<reasoning>` tag where you ask the model to explain its choices, and then a series of tags, one for each piece of data you want to extract.
* The language model is instructed to replace the instructions in the curly braces with the actual data value

---

### Slide 5: XML FTW

So what makes the XML template pattern ideal for this kind of data extraction?

* **Cognitive Scaffolding:** The tag structure acts like guardrails. It forces the model into a more deliberate pattern matching process, which improves accuracy.
* **Training Data Familiarity:** LLMs are 'native speakers' of XML. They've seen massive amounts of it in their training data, and they're good at writing valid XML.
* **Robust Extraction from Text:** LLMs will often add conversational filler around the structured output. A self-contained XML block is easy to parse from a noisy response with a simple regular expression.
* **Mature Schema Validation:** You can validate the *entire structure and all values* of the output against a formal XSD schema.

---

### Slide 6: The Prompt

* This is not a talk on prompt engineering, so I'll just briefly cover the full prompt structure I've used along with the XML template
* **Role and Rules:** First, I assign the model a role, like 'You are a metadata analyst', and provide rules to focus the model on the task.
* **Task:** Then I state the specific task and provide the text to be analyzed.
* **Definitions:** Then I explicitly define every field, including its XML tag, possible values, and example outputs.
* **Output Format:** And finally, I provide the XML template, with simple instructions for how to complete it.
* *(Show the full `example-analysis.md` file.)*

---

### Slide 7: Workflow Integration

* Integrating this prompt into a data pipeline is straightforward in most programming languages
* I chose Python for my example code, the high level flow goes like this:
* Load the source data, then generate the full prompt with the XML template, then call your preferred LLM API, then use a simple regex to extract the `<analysis>` block, and finally validate and store it.
* The full code that generated the results you're about to see is on GitHub if you want to see exactly how it's done.

---

### Slide 8: Results – 60k Wikipedia Pages

* So, how well does it work?
* I tested this by analyzing 60,000 full Wikipedia articles using six different small, off-the-shelf language models.
* Each model was tasked with extracting the seven pieces of metadata you saw in the full example prompt I showed previously
* The results are pretty impressive. As you can see, even with cheap models, the success rate was consistently at or near 99.5%.
* The listed success rates include automated retries, I'll talk more about the details of that mechanism in a bit, but you can see that it helped to drive down the failure rate for all models.
* And most importantly, look at the cost. In most cases, we are talking about just a few dollars to process ten thousand documents.

---

### Slide 9: Objection: XML is too verbose & costs more tokens.

* There are some valid reasons why you might doubt this approach, so let's discuss a few
* A fair objection is that XML is verbose, and more tokens means more cost.
* While this is true, it's also true that I've consistently been able to get high reliability from smaller, cheaper models, which more than offsets the cost of the additional tokens
* In addition context windows are consistently going up while inference costs are going down over time, which means this concern gets continuously less relevant.

---

### Slide 10: Objection: Why not use native JSON modes?

* Why not just use the built-in JSON modes from providers like OpenAI?
* Those tools are excellent and also provide high reliability, but they lock you into that specific provider's ecosystem.
* The XML template pattern is portable. It works the same way across any model—from proprietary APIs to open-source models you run yourself. This gives you flexibility and prevents vendor lock-in.

---

### Slide 11: Objection: JSON is a better fit for our data model & pipeline.

* You might think, 'My whole pipeline is JSON, why introduce XML?'
* The key is that the XML is *transient*. It only exists for the communication between your application code and the LLM.
* You're optimizing for the most reliable communication protocol *from* the LLM. Once you get a valid response, you easily can parse it into a native object that is compatible with the rest of your pipeline.

---

### Slide 12: Objection: This is just good prompting, not an XML feature.

* I agree, this *is* good prompting. My argument is that XML is a *superior format* for this kind of highly structured prompting.
* Its syntax is less ambiguous for the model and easier for us to parse reliably, making it the right tool for this specific job.

---

### Slide 13: Tips & Tricks

In addition to the basic XML template pattern I've illustrated, here are some additional tips and tricks to get the most of of this approach:

* **UUID Retries:** I pass a short, unique identifier as an XML attribute with every inference call. When a request fails, I simply re-send the exact same prompt with a new UUID. I don't have hard data to support this claim, but it seems like the slight variation in input tokens, combined with the natural variation of the non-deterministic responses will often allow the model to succeed on inputs where it initially failed. My example code gives the model three attempts to complete each extraction, and as you saw from the data, these simple retries often result in success.
* **Fallback Model:** If a less capable, cheaper model fails after a few retries, have your code automatically fall back to a more capable model to handle the more difficult cases.
* **CDATA Wrapping:** If you're concerned about output inside a tag breaking the XML parsing (like with the more free form output of a `<reasoning>` tag), you can also programmatically wrap values in CDATA tags to prevent parsing errors from special characters.
* **Complexity vs. Model Size:** This pattern works great with small models for simple schemas. I recommend always trying the smallest, cheapest model you can, working your way up in model size and cost if needed until you hit a model that executes the task well.
* **XSD Validation:** There are various ways to validate your data. For this example code, I used simple database constraints, but I'd also recommend looking at an XSD schema to formally validate the LLM's output. It's pretty easy to use AI to generate the schema, and its a simple and powerful validation mechanism that should be available in just about any programming language.
  * *(Show the full `wikipedia-schema.xsd` file.)*

---

### Slide 14: Key Takeaways

* In summary: you don't have to bribe your LLM to get consistent output if you start giving it a clear blueprint.
* XML Templates are an ideal engineering pattern for many of your data extraction needs.
* It's model-agnostic, works incredibly well with smaller, cheaper LLMs, and delivers near-100% data extraction.

---

### Slide 15: Questions
