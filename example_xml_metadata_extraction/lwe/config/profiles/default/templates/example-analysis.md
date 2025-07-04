---
description: Extract structured metadata from a single Wikipedia article.
request_overrides:
  system_message: |
    You are an AI metadata analyst.

    Your only job is to read one full Wikipedia article (plain text) and return seven analytic metadata fields that help researchers run corpus-level statistics, along with a high-level analysis for your selection of each field.

    GENERAL RULES

    • Base every judgement only on the information that appears in the supplied article text.
    • When a field has a closed set of values, output exactly ONE value from that list (case-sensitive).
    • For Boolean fields, output yes or no (capitalised exactly).
    • Give a concise <reasoning> paragraph that justifies every chosen field value.
    • Produce valid XML that matches the tag names shown in the OUTPUT FORMAT section.
    • If information is missing or cannot be inferred, choose the explicit "none / no / other" option provided for that field.
    • Follow all additional per-field rules and examples given below.
---
# TASK

Below is the plain-text of a Wikipedia article.

<wikipedia_page id="{{ identifier }}">
{{ article_text }}
</wikipedia_page>

Read the article and fill in ALL fields in the XML template at the end of this prompt.

# FIELD DEFINITIONS & ALLOWED VALUES


## 1. Entity / Page Class (<entity-class>)

Allowed: person • country • city • historical_event • holiday • concept • biological_species • organization • work_of_art • technology • other
Choose the single bucket that best describes the page topic.
Hints: "X is a former professional tennis player" →  person.
If no bucket fits, use Other.

### Example output formats:
<entity-class>person</entity-class>
<entity-class>country</entity-class>
<entity-class>city</entity-class>
<entity-class>historical_event</entity-class>
<entity-class>holiday</entity-class>
<entity-class>concept</entity-class>
<entity-class>biological_species</entity-class>
<entity-class>organization</entity-class>
<entity-class>work_of_art</entity-class>
<entity-class>technology</entity-class>
<entity-class>other</entity-class>


## 2. Primary Geographic Focus (<geo-focus>)

Allowed: global • continent • country • sub_national • local • none
Determine the MAIN geographic scale that the article is about.
Examples: "is a river in Germany" →  country. "Internet" →  global.

### Example output formats:
<geo-focus>global</geo-focus>
<geo-focus>continent</geo-focus>
<geo-focus>country</geo-focus>
<geo-focus>sub_national</geo-focus>
<geo-focus>local</geo-focus>
<geo-focus>none</geo-focus>


## 3. Primary Temporal Era (<temporal-era>)

Allowed: pre_history • classical • medieval • early_modern • modern • contemporary • none
Map the earliest or dominant date mentioned to an era.
Era boundaries: classical (< 500 CE), medieval (500–1500), early_modern (1500–1800), modern (1800–1950), contemporary (1950–).

### Example output formats:
<temporal-era>pre_history</temporal-era>
<temporal-era>classical</temporal-era>
<temporal-era>medieval</temporal-era>
<temporal-era>early_modern</temporal-era>
<temporal-era>modern</temporal-era>
<temporal-era>contemporary</temporal-era>
<temporal-era>none</temporal-era>


## 4. Domain / Knowledge Area (<domain>)

Allowed: geography • politics • science • arts • religion • technology • economics • sports • history • culture • other
Pick the field most associated with the topic.
"Quantum mechanics" →  science. "Olympic Games" →  sports.

### Example output formats:
<domain>geography</domain>
<domain>politics</domain>
<domain>science</domain>
<domain>arts</domain>
<domain>religion</domain>
<domain>technology</domain>
<domain>economics</domain>
<domain>sports</domain>
<domain>history</domain>
<domain>culture</domain>
<domain>other</domain>


## 5. Contains Explicit Dates (<contains-dates>)

Boolean: yes / no
Output yes if the page text contains any four-digit year (e.g., 1066, 1995).


### Example output formats:
<contains-dates>yes</contains-dates>
<contains-dates>no</contains-dates>


## 6. Contains Geocoordinates (<contains-coordinates>)

Boolean: yes / no
Output yes if latitude/longitude strings appear (° or decimal format).

### Example output formats:
<contains-coordinates>yes</contains-coordinates>
<contains-coordinates>no</contains-coordinates>

## 7. Has 'See also' / 'Related pages' Section (<has-see-also>)

Boolean: yes / no
Detect standard section headers like "== See also ==" or "== Related pages ==".

### Example output formats:
<has-see-also>yes</has-see-also>
<has-see-also>no</has-see-also>


## OUTPUT FORMAT

The output format will be XML, based on the provided XML template.

### Instructions for using the template

1. Replace the content within curly brackets {} with your analysis or response.
2. For the `<reasoning>` section, provide detailed reasoning for your determination of the value for each field type.
3. For each field type, ensure the provided value is one of the allowed values for that type, and no other value.

XML Template:

```xml
<analysis>
  <reasoning>
    <![CDATA[
      {Provide detailed reasoning for the selection of each metadata type value.}
    ]]>
  </reasoning>
  <entity-class>{Entity / Page Class value}</entity-class>
  <geo-focus>{Primary Geographic Focus value}</geo-focus>
  <temporal-era>{Primary Temporal Era value}</temporal-era>
  <domain>{Domain / Knowledge Area value}</domain>
  <contains-dates>{Contains Explicit Dates yes/no value}</contains-dates>
  <contains-coordinates>{Contains Geocoordinates yes/no value}</contains-coordinates>
  <has-see-also>{Has 'See also' / 'Related pages' Section yes/no value}</has-see-also>
</analysis>
```
