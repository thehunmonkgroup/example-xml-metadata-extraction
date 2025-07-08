# XML For the Win: Reliable AI Data Extraction

This repository contains the source code for the "XML For the Win: Reliable AI Data Extraction" presentation at ClueCon.

The project demonstrates a robust method for extracting structured metadata from unstructured text (Wikipedia articles) using a Large Language Model (LLM) and storing it in a local SQLite database.

## Core Concepts

This example illustrates several key techniques for reliable, automated data extraction.

### 1. XML as a Prompting Strategy

The core of this project is the `lwe/config/profiles/default/templates/example-analysis.md` template. This prompt instructs the LLM to return its analysis within a strict XML format. Using XML provides several advantages:
-   **Structure:** It forces the LLM to think in a structured way, improving the reliability of the output.
-   **Clarity:** The tag-based format is unambiguous and easy for both humans and machines to understand.
-   **Compatibility:** Most LLMs are well-trained in XML.
-   **Reliability:** LLMs have a very high success rate using XML templates.
-   **Parsability:** XML is a well-established standard, and is particularly easy to parse if/when the LLM outputs other text around it.

### 2. Robust Output Sanitization

LLMs can sometimes include characters in their free-text reasoning (e.g., `<` or `&`) that break standard XML parsers. This project demonstrates a simple but effective technique to prevent this:
1.  The Python script first uses a regular expression to find the `<analysis>` block in the LLM's raw output.
2.  It then wraps the content of each inner tag (like `<reasoning>` and `<domain>`) with `<![CDATA[...]]>`.
3.  This `CDATA` section tells the XML parser to treat the enclosed text as literal character data, ignoring any special XML characters within it.

This sanitization step makes the parsing process far more resilient to unexpected LLM outputs.

### 3. End-to-End Workflow

The script automates the entire data extraction pipeline:

1.  **Fetch Data:** It downloads the "simple" Wikipedia dataset from Hugging Face.
2.  **Analyze with LLM:** It sends each article to an LLM, using the XML prompt template to guide the analysis.
3.  **Parse and Sanitize:** It receives the raw response, sanitizes the XML content, and parses it into a Python dictionary.
4.  **Store Results:** It inserts the structured metadata into a local SQLite database, creating a clean, queryable dataset for further research.

## Setup and Installation

Follow these steps to set up and run the project.

### Prerequisites

-   Python 3.10+
-   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/llm-workflow-engine/example-xml-metadata-extraction.git
    cd example-xml-metadata-extraction
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    The project is packaged with `setuptools`, and the `xml-metadata-extractor` command will be installed into your environment.
    ```bash
    pip install -e .
    ```

### Configuration

The script uses models from [OpenRouter](https://openrouter.ai/). You will need an API key to run the analysis.

1.  **Create a `.env` file:**
    Copy the example file to a new `.env` file.
    ```bash
    cp .env.example .env
    ```

2.  **Add your API key:**
    Open the `.env` file and paste your [OpenRouter API key](https://openrouter.ai/settings/keys).
    ```
    OPENROUTER_API_KEY="sk-or-..."
    ```

## How to Run

The script is run from the command line using the `xml-metadata-extractor` command.

Here is a basic example that analyzes 50 articles and saves a detailed log of the LLM's reasoning to `analysis.log`:
```bash
xml-metadata-extractor --limit 50 --logfile analysis.log
```

### Key Command-Line Arguments
* `--limit`: The number of Wikipedia articles to process (default: 1000).
* `--preset`: The LLM model preset to use for analysis (default: `llama-4-scout`). The codebase is bundled with the following presets:
  * gemini-2.5-flash
  * gpt-4.1-nano
  * llama-4-scout
  * phi-4
  * qwen3-8b
  * ministral-8b
* `--database`: The path to the SQLite database file (default: `example-analysis-stats.db`).
* `--logfile`: A file path to log the full reasoning and metadata for each analysis.
* `--debug`: Enable verbose debug logging.

## Viewing the Results

The extracted data is stored in an SQLite database file, `example-analysis-stats.db` by default. You can inspect the data using the `sqlite3` command-line tool.

For example, to see the first 10 rows of extracted data:
```bash
sqlite3 example-analysis-stats.db "SELECT * FROM analysis_data LIMIT 10;"
```

To get a count of articles by their assigned domain:
```bash
sqlite3 example-analysis-stats.db "SELECT domain, COUNT(*) FROM analysis_data GROUP BY domain;"
```

To view the success and failure statistics for each preset:
```bash
sqlite3 example-analysis-stats.db "SELECT * FROM preset_stats ORDER BY success_count DESC;"
```
The `preset_stats` table contains `success_count`, `failure_count` (for pages that failed all retry attempts), and `retry_error_count` (for individual failed attempts that were retried).

## Presentation Data

The presentation data consists of metadata extraction from 60,000 full Wikipedia pages, 10,000 pages each from the following models:

* gemini-2.5-flash
* gpt-4.1-nano
* llama-4-scout
* phi-4
* qwen3-8b
* ministral-8b

```sh
xml-metadata-extractor --logfile gemini-2.5-flash.log --limit 10000 --preset gemini-2.5-flash
xml-metadata-extractor --logfile gpt-4.1-nano.log --limit 10000 --offset 10001 --preset gpt-4.1-nano
xml-metadata-extractor --logfile llama-4-scout.log --limit 10000 --offset 20001 --preset llama-4-scout
xml-metadata-extractor --logfile phi-4.log --limit 10000 --offset 30001 --preset phi-4
xml-metadata-extractor --logfile qwen3-8b.log --limit 10000 --offset 40001 --preset qwen3-8b
xml-metadata-extractor --logfile ministral-8b.log --limit 10000 --offset 50001 --preset ministral-8b
```
