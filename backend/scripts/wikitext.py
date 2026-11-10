"""WikiText-2 articles as distractor documents for evaluation and benchmarks.

WikiText-2 (Merity et al., 2016; CC BY-SA 3.0) holds ~600 Wikipedia articles
with their section headings. It is downloaded from the Hugging Face Hub into
the local cache on first use and is **never committed** to this repository.

Each article becomes a Markdown text: "= Title =" → "# Title",
"= = Section = =" → "## Section", so CADIS builds a real section tree for it.
Tokenisation artefacts (" @-@ ", " , ") are undone.
"""

import re

REPO = "Salesforce/wikitext"
FILES = {"train": "wikitext-2-raw-v1/train-00000-of-00001.parquet",
         "validation": "wikitext-2-raw-v1/validation-00000-of-00001.parquet",
         "test": "wikitext-2-raw-v1/test-00000-of-00001.parquet"}

_HEADING = re.compile(r"^((?:= )+)(.+?)(?: =)+$")      # "= = Gameplay = =" → level 2


def _clean(line: str) -> str:
    s = line.replace(" @-@ ", "-").replace(" @,@ ", ",").replace(" @.@ ", ".")
    s = re.sub(r" ([,.;:!?)\]'])", r"\1", s)
    s = re.sub(r"([(\[]) ", r"\1", s)
    s = s.replace(" n't", "n't").replace(" 's", "'s").replace('" ', '"')
    return s.strip()


def load_articles(splits=("train", "validation", "test"), limit: int | None = None):
    """[(title, markdown_text)] in dataset order."""
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    articles: list[tuple[str, list[str]]] = []
    for split in splits:
        path = hf_hub_download(REPO, FILES[split], repo_type="dataset")
        for raw in pq.read_table(path).column("text").to_pylist():
            line = raw.strip()
            if not line:
                continue
            m = _HEADING.match(line)
            level = m.group(1).count("=") if m else 0
            if level == 1:
                articles.append((_clean(m.group(2)), [f"# {_clean(m.group(2))}"]))
            elif m and articles:
                articles[-1][1].append("#" * level + " " + _clean(m.group(2)))
            elif articles:
                articles[-1][1].append(_clean(line))
            if limit and len(articles) > limit:
                break
        if limit and len(articles) > limit:
            break
    out = [(title, "\n\n".join(lines)) for title, lines in articles if len(lines) > 2]
    return out[:limit] if limit else out
