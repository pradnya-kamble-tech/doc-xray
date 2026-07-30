# Doc-XRay ML Pipeline

## Overview
The Doc-XRay system employs a dual-pipeline architecture for Machine Learning. Due to concerns with GenAI hallucination, risk and jargon classifiers rely heavily on deterministic NLP and traditional ML for auditing and predictability.

## NLP Pipeline (Deterministic & Extractive)
We utilize `spaCy` (en_core_web_sm) to segment document pages into semantically whole logical chunks (sentences/paragraphs).

1. **Named Entity Recognition (NER)**: spaCy is used to label text entities (ORG, PERSON, DATE, MONEY).
2. **Keyword Extraction**: Words are ranked by significance using local TF-IDF (TfidfVectorizer) fitted across the document text. This helps pull out salient vocabulary.

## ML Pipeline (Risk Classification)
This pipeline scans all document chunks to find potentially compromising, risky, or exceptional clauses.

### Dataset
The training dataset is located in `data/risk_training_data.csv`. It contains synthetic pairs of clauses, sentences, and their labeled risk tiers (LOW_RISK, MEDIUM_RISK, HIGH_RISK).

### Algorithm
We use standard `scikit-learn` stack:
- **TfidfVectorizer**: Converts text into count-normalized word vectors.
- **SGDClassifier**: A linear SVM optimized for sparse document data.

### Rule-based Exemptions
The classical ML classifier is occasionally overridden by a simple deterministic rule-engine containing flag-terms. If any flag-term is found, the system artificially bumps up the risk score with `prediction_source="rule_override"`. This enables non-ML-engineers to hot-fix specific misclassifications easily.

### Limitations
- The custom SGD classifier is trained on a synthetic dataset, so out-of-distribution text might fall back to lower-confidence predictions.
- TF-IDF cannot detect deep semantic meaning—this is offloaded to the RAG LLM layer, but only optionally by the user.
