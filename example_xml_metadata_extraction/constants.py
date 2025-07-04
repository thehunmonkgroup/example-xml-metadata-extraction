HUGGINGFACE_DATASET = {
    "path": "wikipedia",
    "name": "20220301.simple",
    "trust_remote_code": True,
}

DATA_LENGTH_THRESHOLD = 0
DEBUG_DATASET_SIZE = 5

# Database defaults
DEFAULT_DATABASE_NAME = "example-analysis-stats.db"

# Analysis configuration
ANALYSIZER_TEMPLATE = "example-analysis.md"
BACKUP_PRESET = "voicemail-analysis-llama3"
BATCH_SIZE = 1000

# Data processing
COMMA_SEPARATED_HEADERS = [
    "sentiments",
    "categories",
]
