# **Cortex – Product Requirements Document (PRD)**

## **Overview**

**Cortex** is a modular personal knowledge graph system that ingests documents, extracts structured metadata (entities, topics, relations), and links these into a persistent graph with traceability to original sources and local document storage.

## **Objectives**
* Ingest PDFs, Markdown, audio transcripts, and other formats from multiple sources
* Extract named entities and relationships using LLMs
* Persist extracted knowledge as structured data in a graph database
* Retain durable links to all source material (original URL, archive snapshot, Google Drive ID)
* Enable temporal and relational queries across documents and entities

## **Use Cases**
* Analyze chip supply chain documents (e.g., ETO explorer)
* Map corporate structures (e.g., Huawei org chart from FT)
* Track and enrich SEC filings automatically (e.g., Google 10-Ks)
* Maintain cross-linked dossiers on companies, products, and people over time

## Core Modules

### 1. Ingestion Layer
- Drive watcher: polls /inbox/ for new files
- RSS poller: fetches feeds (Substack, blogs, YouTube via RSSHub) every 15 m
- EDGAR scraper: tracks 8-K/10-K/10-Q for configured tickers
- Media handler: accepts audio/video URLs, runs Whisper or OpenAI transcription

#### **1.1 Ingestion: Document Sources**

##### a. **Google Drive**
* Watch `/inbox/` folders for new uploads (PDF, DOCX, TXT, MD)
* Trigger extraction pipeline for each file
* Store final version in `/processed/` folder after processing
* Generate sidecar JSON in `/metadata/`

##### b. **RSS Feeds**
* Supported feeds: Substack, blogs, YouTube (via RSSHub), podcast feeds
* Poll every 15 mins or on demand
* Skip duplicate `GUID` or `source_url` entries already ingested
* Download main content (HTML, Markdown)
* Archive via `archive.md` or `archive.org`
* Save cleaned content as Markdown in Drive

##### c. **SEC Filings**

* Track new 8-K, 10-K, 10-Q for predefined tickers
* Use EDGAR scraper or API (e.g., `sec-edgar-downloader`)
* Identify relevant exhibits (EX-99.1, EX-101)
* Download and store PDF or HTML
* Link to company entity via `edgar_cik` or `ticker`

##### d. **Podcasts / YouTube**
* Accept transcript or audio URL
* Use Whisper or OpenAI transcription
* Store transcript + episode metadata
* Infer episode title, guests, themes

#### **1.2 Metadata & Content Processing**
* Each document results in:
  * Markdown/PDF/Transcript file in Drive
  * JSON metadata record
* Fields to extract (automatically or via prompt):
  * Title
  * Publish date
  * Source URL
  * Archive URL
  * Drive ID
  * Summary (GPT-4o)
  * Topics (classification or embeddings)
  * Named Entities (NER)
  * Inter-entity Relations (OpenAI function or rule-based model)

#### **1.3 Graph Updates**
* For each extracted entity:
  * `MERGE` node in graph if not present
  * Update aliases if partial match (with confidence score)
  * Create or update edges (e.g., `MENTIONS`, `SUBSIDIARY_OF`)
* Documents are linked to all entities they mention
* If `linked_entity` is known (e.g., ticker matched), associate directly

#### **1.4 Deduplication / Integrity**
* Use `source_url` as primary deduplication key
* Archive every `source_url` via `archive.md` and store `archive_url`
* Store and index all Drive file IDs (`drive_url`)
* Logs: every document has `date_ingested`, `status`, and `log_id`

##### Extraction Layer
- Text normalization: PDF→text, HTML→Markdown, transcripts cleaned
- Entity & relation extraction: GPT-4o function calls or custom NER+RE
- Topic classification & summarization: LLM-generated topics + abstracts
- Archive: pushes sources to archive.md/org, captures archive_url

##### Storage & Linking
- Moves processed files into /processed/
- Writes sidecar JSON into /metadata/
- Invokes graph engine to MERGE nodes & CREATE/UPDATE edges

##### Optional Index Layer
- Inserts metadata rows into Supabase/Postgres for search/filter
- Powers lightweight UI or API for boolean/full-text queries

### 2. **Extraction Layer**
* Uses GPT-4o or similar for NER, relation extraction, and summarization
* Outputs a structured `.json` metadata file per document

### 3. **Storage & Linking**
* Stores raw files in `/processed/`
* Stores structured metadata in `/metadata/`
* Updates graph database (e.g. Neo4j)

### 4. **Optional Index Layer**
* Inserts document metadata into Supabase or Postgres table for search and filtering

## **Project Folder Structure**
This structure uses Google Drive as the source-of-truth document store:

```
/Cortex/
├── /inbox/                     # Raw unprocessed content
│   ├── /sec_filings/           # EDGAR filings
│   ├── /rss_feeds/             # Newsletters, blogs, Substack
│   ├── /podcasts/              # Transcripts from podcast episodes
│   ├── /videos/                # Transcripts from YouTube, lectures, etc.
│   ├── /papers/                # arXiv or whitepapers
│   └── /manual_uploads/        # User-curated PDFs, research
│
├── /metadata/                  # Sidecar JSONs storing extracted metadata
│   ├── /sec_filings/
│   ├── /rss_feeds/
│   ├── /podcasts/
│   ├── /videos/
│   ├── /papers/
│   └── /manual_uploads/
│
├── /processed/                 # Archived documents after ingestion
│   ├── /pdfs/
│   ├── /markdown/
│   └── /transcripts/
│
├── /snapshots/                 # Exports or backups of graph or entity tables
│   └── /weekly_exports/
```

## Data Models, Minimum Output, Entity Relationships
Each document results in:
1. A saved local copy (.pdf or .md)
2. A structured `.json` metadata file
3. New or updated nodes and relationships in the knowledge graph

### **Example Schema: Document Metadata (`document_metadata.json`)**

```json
{
  "document_id": "sec_GOOG_10K_2024",
  "source_type": "sec_filing",
  "title": "Alphabet Inc. 10-K 2024",
  "date_published": "2024-02-10",
  "date_ingested": "2025-05-11T16:00:00Z",

  "source_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204424000012/0001652044-24-000012-index.htm",
  "archive_url": "https://archive.md/fn8Lx",
  "drive_url": "https://drive.google.com/file/d/abc123xyz/view",
  "file_type": "pdf",

  "linked_entity": {
    "name": "Google",
    "entity_id": "entity_google",
    "type": "Company"
  },

  "extracted_entities": [
    { "name": "Google", "type": "Company", "confidence": 0.99 },
    { "name": "TPU v5e", "type": "Product", "confidence": 0.94 },
    { "name": "OpenAI", "type": "Company", "confidence": 0.91 }
  ],

  "relations": [
    { "source": "Google", "target": "TPU v5e", "type": "develops" },
    { "source": "Google", "target": "OpenAI", "type": "competitor" }
  ],

  "topics": ["AI", "Semiconductors", "Cloud Infrastructure"],
  "summary": "Alphabet highlights growth in AI infrastructure and TPU development in its 2024 10-K."
}
```

### **Example Schema: Entity (Company or Product)**
```json
{
  "entity_id": "entity_nvidia",
  "name": "NVIDIA Corporation",
  "type": "Company",
  "stock_ticker": "NVDA",
  "exchange": "NASDAQ",
  "edgar_cik": "0001045810",
  "official_url": "https://www.nvidia.com",
  "investor_relations_url": "https://investor.nvidia.com",
  "headquarters": {
    "city": "Santa Clara",
    "state": "CA",
    "country": "USA"
  },
  "sector": "Semiconductors",
  "public": true,
  "aliases": ["NVIDIA", "NVDA", "NVIDIA Corp"],
  "last_updated": "2025-05-11T00:00:00Z"
}
```

```json
{
  "entity_id": "product_nvidia_h100",
  "name": "H100 Tensor Core GPU",
  "type": "Product",
  "manufacturer": {
    "name": "NVIDIA",
    "entity_id": "entity_nvidia"
  },
  "aliases": ["H100", "Hopper H100", "NVIDIA H100", "NVIDIA's flagship GPU"],
  "product_line": "Hopper Architecture",
  "generation": 8,
  "launch_date": "2022-03-22",
  "status": "active",
  "use_cases": ["AI Training", "Inference", "HPC"],
  "successor": {
    "name": "B100",
    "entity_id": "product_nvidia_b100"
  },
  "predecessor": {
    "name": "A100",
    "entity_id": "product_nvidia_a100"
  }
}
```

### Entity Types

| Type     | Example              | Key Fields                                 |
| -------- | -------------------- | ------------------------------------------ |
| Company  | NVIDIA, HiSilicon    | Name, CIK, ticker, IR URL, aliases         |
| Product  | H100, Ascend 910B    | Name, manufacturer, aliases, product\_line |
| Person   | Jensen Huang         | Name, org affiliation, roles               |
| Document | GOOG 10-K 2024       | Title, source, Drive link, entity mentions |
| Source   | Stratechery RSS, SEC | URL, ingestion method, tags                |

---

### Relationships

| Relationship      | Source → Target   | Description                                  |
| ----------------- | ----------------- | -------------------------------------------- |
| `MENTIONS`        | Document → Entity | Document references this entity              |
| `MANUFACTURES`    | Company → Product | Manufacturer-product linkage                 |
| `SUBSIDIARY_OF`   | Company → Company | Ownership/subsidiary relation                |
| `SUCCESSOR_OF`    | Product → Product | Product lineage (e.g. H100 → B100)           |
| `AFFILIATED_WITH` | Person → Company  | Executive, founder, or employee relationship |
| `PUBLISHED_BY`    | Document → Source | Origin source of the document                |

---

### Example: Graph Triples

```plaintext
"Alphabet Inc." --(SUBSIDIARY_OF)--> "Google LLC"
"GOOG 10-K 2024" --(MENTIONS)--> "TPU v5e"
"HiSilicon" --(MANUFACTURES)--> "Ascend 910B"
"Stratechery Feed" --(PUBLISHED_BY)--> "Stratechery"
"Ben Thompson" --(AFFILIATED_WITH)--> "Stratechery"
```

## System Architecture Diagram (Text Description)

### High-Level Modules

```plaintext
┌────────────────────────────┐
│ Google Drive / RSS / SEC   │ <── External Source Pollers
└────────────────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Ingestion Layer             │
│ - Download/Archive         │
│ - Store to Drive           │
└────────────────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Extraction Layer            │
│ - Text extraction (PDF/HTML)│
│ - NER & relation extraction │
│ - Topic + summary tagging   │
└────────────────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Metadata Layer              │
│ - JSON sidecar generation   │
│ - Source URL + archive link │
│ - Stored in /metadata/      │
└────────────────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Graph Update Engine         │
│ - Neo4j node/edge creation  │
│ - Entity deduping/aliasing  │
└────────────────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Optional Index Layer        │
│ - Supabase/Postgres table   │
│ - Document search UI        │
└────────────────────────────┘
```

## **Success Criteria**

* \>95% of documents processed without manual intervention
* All documents linked to at least one entity node
* All entities linked to source documents, with durable provenance (source, archive, Drive)
* Graph queries possible by entity, topic, relation, or time period