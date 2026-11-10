"""All CADIS settings in one place (DECISIONS ADR-021).

Every setting is read from an environment variable with the ``CADIS_`` prefix
(or a ``.env`` file in development). The V1 names ``QA_MODEL``, ``SUM_MODEL``,
``NER_MODEL``, ``EMB_MODEL`` and ``FRONTEND_URL`` are still accepted as
fallbacks so existing deployments keep working during the migration.

No other module should call ``os.getenv`` — import ``get_settings()`` instead.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env(name: str, *legacy: str) -> AliasChoices:
    """Accept CADIS_<NAME> first, then any V1 variable names."""
    return AliasChoices(f"CADIS_{name}", *legacy)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Service ────────────────────────────────────────────────────────────────
    service_name: str = "CADIS API"
    service_version: str = "2.1"

    # Comma-separated extra CORS origins. FRONTEND_URL (V1) is a single origin.
    frontend_urls: str = Field("", validation_alias=_env("FRONTEND_URLS", "FRONTEND_URL"))

    # ── Model IDs ──────────────────────────────────────────────────────────────
    spacy_model: str = Field("en_core_web_sm", validation_alias=_env("SPACY_MODEL"))
    emb_model: str = Field("all-MiniLM-L6-v2", validation_alias=_env("EMB_MODEL", "EMB_MODEL"))
    ner_model: str = Field("dslim/bert-base-NER", validation_alias=_env("NER_MODEL", "NER_MODEL"))
    qa_model: str = Field("deepset/roberta-base-squad2", validation_alias=_env("QA_MODEL", "QA_MODEL"))
    sum_model: str = Field("sshleifer/distilbart-cnn-12-6", validation_alias=_env("SUM_MODEL", "SUM_MODEL"))

    # ── Extractive QA ──────────────────────────────────────────────────────────
    qa_window: int = Field(384, validation_alias=_env("QA_WINDOW"))            # tokens per sliding window
    qa_stride: int = Field(128, validation_alias=_env("QA_STRIDE"))            # overlap between windows
    qa_max_answer_tokens: int = Field(40, validation_alias=_env("QA_MAX_ANSWER_TOKENS"))
    qa_top_k: int = Field(20, validation_alias=_env("QA_TOP_K"))               # start/end candidates per window
    qa_max_passages: int = Field(6, validation_alias=_env("QA_MAX_PASSAGES"))  # passages retrieved per question
    # Retrieval passages are sized in the *embedding model's* tokens and are
    # always capped below what that model can read (MiniLM: 256 incl. specials).
    # V1 used 200 words, which is ~244–260 tokens and could be cut off.
    passage_tokens: int = Field(220, validation_alias=_env("PASSAGE_TOKENS"))
    passage_overlap_tokens: int = Field(50, validation_alias=_env("PASSAGE_OVERLAP_TOKENS"))
    passage_cache_size: int = Field(8, validation_alias=_env("PASSAGE_CACHE_SIZE"))  # documents kept

    # ── NER ────────────────────────────────────────────────────────────────────
    ner_chunk_tokens: int = Field(400, validation_alias=_env("NER_CHUNK_TOKENS"))  # BERT limit is 512
    # "first" groups at word level. V1 used "simple", which can split one word
    # into several entities ("Ai" + "##sha Patel" for "Aisha Patel").
    ner_aggregation: str = Field("first", validation_alias=_env("NER_AGGREGATION"))

    # ── Embeddings view (keeps /api/process responses small) ───────────────────
    sim_matrix_max: int = Field(20, validation_alias=_env("SIM_MATRIX_MAX"))       # rows/cols sent
    vector_preview_max: int = Field(50, validation_alias=_env("VECTOR_PREVIEW_MAX"))
    top_pairs: int = Field(5, validation_alias=_env("TOP_PAIRS"))

    # ── Summarization ──────────────────────────────────────────────────────────
    sum_max_tokens: int = Field(1024, validation_alias=_env("SUM_MAX_TOKENS"))      # DistilBART input limit
    sum_chunk_tokens: int = Field(512, validation_alias=_env("SUM_CHUNK_TOKENS"))   # target per chunk
    sum_short_words: int = Field(400, validation_alias=_env("SUM_SHORT_WORDS"))     # single pass at or below

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
        for url in self.frontend_urls.split(","):
            url = url.strip().rstrip("/")
            if url and url not in origins:
                origins.append(url)
        return origins

    @property
    def health_name(self) -> str:
        return f"{self.service_name} v{self.service_version}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
