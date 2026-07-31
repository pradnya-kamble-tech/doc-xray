# Doc-XRay ML Evaluation Report

## Risk Classification Pipeline

This report covers the internal implementation and structure of the Doc-XRay document risk scoring system. The evaluation metrics represent the underlying data performance on traditional Machine Learning architectures.

### Architecture Components

1. **TF-IDF Feature Extraction**
   - We utilize Scikit-Learn's `TfidfVectorizer` (Term Frequency-Inverse Document Frequency).
   - Extracts N-grams (1-2) with a bounded maximum feature set (2000 words).
   - This translates raw document chunks into dense numerical features.

2. **SGDClassifier**
   - The primary traditional ML layer is a `SGDClassifier` utilizing Stochastic Gradient Descent.
   - Configured with `loss="modified_huber"` to convert vector proximities into probability distributions (`predict_proba`).
   - Acts as an ultra-fast linear classifier to score high-risk features immediately upon document upload.

3. **Risk Classes**
   - Currently, the classifier labels output into binary classifications mapped internally (e.g., `Safe`, `Risky`).

### Rule-Based Override Layer vs. ML Prediction

It is vital to distinguish between ML predictions and domain-logic overrides in the pipeline:
- **ML Prediction:** A statistical probability derived strictly from the SGDClassifier weights based on historical TF-IDF document training data. It is inherently fuzzy.
- **Rule-Based Override:** Absolute deterministic criteria (e.g., "Contains standard NDAs" -> Force Risk = Safe). If an exclusion rule triggers, it explicitly overrides the ML probability and forces the final output assignment. These do not count toward ML accuracy metrics.

---

### Evaluation Metrics

*(Execution Note: True continuous measurement blocked during current CI run due to heavy missing numerical Windows compilation dependencies `scipy`/`scikit-learn` in Python 3.8).*

Based on historical execution of the internal structured test set:
- **Accuracy:** N/A (Awaiting Windows environment pipeline update)
- **Precision:** N/A
- **Recall:** N/A
- **F1 Score:** N/A (Weighted)

#### Expected Classification Report Output Format:
```text
              precision    recall  f1-score   support

           0       --        --        --        --
           1       --        --        --        --

    accuracy                           --        --
   macro avg       --        --        --        --
weighted avg       --        --        --        --
```
