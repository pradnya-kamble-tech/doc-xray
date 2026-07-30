"""
Training script for the Doc-XRay risk classifier.

Pipeline:
    TfidfVectorizer(ngram_range=(1,2)) → SGDClassifier

Usage:
    python scripts/train_risk_classifier.py

Output:
    data/risk_classifier.pkl  — serialized sklearn pipeline
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score


DATA_PATH = Path(__file__).parent.parent / "data" / "risk_training_data.csv"
MODEL_PATH = Path(__file__).parent.parent / "data" / "risk_classifier.pkl"


def train():
    print("=" * 60)
    print("Doc-XRay Risk Classifier Training")
    print("=" * 60)

    # Load data
    df = pd.read_csv(DATA_PATH)
    print(f"\nDataset: {len(df)} examples")
    print("Label distribution:")
    print(df["label"].value_counts())

    X = df["text"].tolist()
    y = df["label"].tolist()

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")

    # Build pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=2000,
            stop_words="english",
            sublinear_tf=True,
        )),
        ("clf", SGDClassifier(
            loss="modified_huber",   # enables predict_proba
            alpha=1e-4,
            max_iter=200,
            random_state=42,
            class_weight="balanced",
        )),
    ])

    # Train
    print("\nTraining SGDClassifier with TF-IDF features...")
    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"Accuracy:  {acc:.4f}")
    print(f"F1 Score:  {f1:.4f} (weighted)")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")
    print("Training complete.")
    return pipeline


if __name__ == "__main__":
    train()
