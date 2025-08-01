# Huggingface dataset config
HUGGINGFACE_DATASET = {
    "path": "wikipedia",
    "name": "20220301.simple",
    "trust_remote_code": True,
}

# Database
DEFAULT_DATABASE_NAME = "example-analysis-stats.db"

# Analysis configuration
ANALYSIZER_TEMPLATE = "example-analysis.md"
DEFAULT_PRESET = "llama-4-scout"
DEFAULT_LIMIT = 1000

# Data
DATA_COLUMNS = [
    "entity_class",
    "geo_focus",
    "temporal_era",
    "domain",
    "contains_dates",
    "contains_coordinates",
    "has_see_also",
]

# Retry
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5

# Debug
DATA_LENGTH_THRESHOLD = 0
DEBUG_DATASET_SIZE = 5
