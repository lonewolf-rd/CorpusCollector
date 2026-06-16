# CorpusCollector

**A multi-source, configuration-driven pipeline for building a custom Turkish corpus tailored to language-model and tokenizer training.**

CorpusCollector harvests Turkish text from academic publications, news outlets, and user-generated content platforms, filters it for language quality, and consolidates the result into a single tokenizer-ready corpus file.

The framework was built to produce the training corpus behind the morphology-aware Turkish tokenizer developed under the [lonewolf-rd](https://github.com/lonewolf-rd) organization.

---

## Related Work

The corpus produced by this repository underpins the following artifacts. Everything — the collection pipeline, the cleaned dataset, the trained tokenizer, and the accompanying paper — is fully open source.

- **Tokenizer:** [TurkishMorpheus](https://github.com/lonewolf-rd/TurkishMorpheus) — a morphology-aware Turkish tokenizer.
- **Released Model:** [lonewolflab/Morpheus-TR-50K](https://huggingface.co/lonewolflab/Morpheus-TR-50K) — the 50K-vocabulary release on Hugging Face.
- **Organization:** [lonewolf-rd](https://github.com/lonewolf-rd)

---

## Features

- **Multi-source collection.** Dedicated crawlers for academic articles (DergiPark), news content (Hürriyet), and user comments (Ekşi Sözlük).
- **Language filtering.** A `langdetect`-based validator discards non-Turkish content at the source.
- **Stealth browser sessions.** Built on `undetected-chromedriver` and `selenium-stealth` to resist common bot-detection schemes.
- **Configuration-first design.** All XPaths, URLs, and driver options are declared in YAML — target sites can be updated without touching the code.
- **Tokenizer-ready output.** A `PostProcessor` stage merges heterogeneous `.txt` and `.json` artifacts into a single line-per-sample `corpus.txt`.

---

## Data Sources

| Source | Module | Description |
|---|---|---|
| DergiPark | `helpers/article_crawler.py` | Walks academic search results, separates Turkish from English titles, and collects article links. |
| Hürriyet | `helpers/news_crawler.py` | Paginates through category feeds and extracts headline, lead, and body text. |
| Ekşi Sözlük | `helpers/form_crawler.py` | Uses the "today in history" navigation to traverse historical threads and aggregate user entries. |

Target-site templates live under `src/configs/`:

- `scraping_configs.yaml` — DergiPark article crawler
- `news_configs.yaml` — Hürriyet news crawler
- `form_configs.yaml` — Ekşi Sözlük forum crawler
- `request_configs.yaml` — HTTP request headers
- `logging.yaml` — logger configuration

---

## Preprocessing & Data Cleaning

The pipeline cleans text both **inline** during collection and **once more** during corpus consolidation, so noise never accumulates into the final artifact.

- **Source-side language gating.** Every candidate title or entry is passed through a `langdetect`-based filter; anything that is not classified as Turkish is dropped before it ever reaches disk. For academic content, Turkish and English links are split into separate files at crawl time.
- **PDF-to-text extraction.** Academic PDFs are parsed with `PyPDF2`, then case-folded and whitespace-collapsed (`\s+ → ` `). Section boundaries are recovered with anchored regexes (`öz … anahtar kelimeler` for the abstract, `giriş … kaynaklar` for the body), so boilerplate like headers, page numbers, and reference lists are excised in the same pass.
- **HTML noise removal.** News and forum crawlers extract text from a small set of pinned XPaths (headline, lead, body, entry content), which structurally excludes navigation, ads, and sidebar markup.
- **Whitespace and empty-line normalization.** During consolidation, each line is stripped, internal whitespace runs are collapsed to a single space (`" ".join(text.split())`), and empty lines are skipped.
- **Encoding sanitization.** A final `sanitize_corpus` pass re-decodes the file as UTF-8 with `errors="ignore"`, dropping malformed byte sequences that survived upstream parsing.
- **Format normalization.** Heterogeneous `.txt` and nested `.json` artifacts are flattened into a uniform **one-sample-per-line** layout — the format expected by the downstream tokenizer trainer.

The end result is a single `corpus.txt` where each line is a clean, Turkish-only, whitespace-normalized text sample.

---

## Installation

Requirements: Python 3.10+, Google Chrome.

### With Make (recommended)

```bash
make venv
make install
```

### Manual setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install -e .
```

---

## Usage

Each crawler is an independent component and can be instantiated directly:

```python
from src.helpers.article_crawler import ArticleCrawler
from src.helpers.news_crawler import NewsCrawler
from src.helpers.form_crawler import FormCrawler

ArticleCrawler().start_crawling()
NewsCrawler().start_crawling()
FormCrawler().start_crawling()
```

Once collection is finished, consolidate the raw artifacts into a single tokenizer-ready corpus:

```python
from src.helpers.post_processor import PostProcessor

PostProcessor().prepare_tokenizer_data(output_file="corpus.txt")
```

`PostProcessor` scans the `data/` directory for every `.txt` and `.json` artifact, normalizes each line, and writes them to the output file.

---

## Configuration

Adding a new source — or adapting to a DOM change in an existing one — is a matter of editing the relevant YAML. For example, the DergiPark article-card selectors live in `src/configs/scraping_configs.yaml`:

```yaml
xpaths:
  source: "dergipark"
  base_url: https://dergipark.org.tr/tr/search?q=*&section=article
  article_cards: //div[@class='article-cards']//div[@class='card article-card ...']
  article_title: .//div[@class='card-body']//h5[@class='card-title']/a[1]
```

`ConfigManager` honors `include:` directives, so child YAML files are merged into the parent configuration automatically.

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## Citation

If you use this framework or a derivative corpus in academic work, please cite it as:

```
@software{corpuscollector2025,
  author  = {lonewolf-rd},
  title   = {CorpusCollector: A Multi-Source Turkish Corpus Pipeline},
  year    = {2025},
  url     = {https://github.com/lonewolf-rd}
}
```
