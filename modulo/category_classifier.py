"""
# category_classifier.py

This module handles automatic expense category classification based on transaction notes.
It uses keyword matching and lightweight scoring logic to infer the most suitable category for expense transactions.

Example:
"grab về nhà" → transport

Main responsibilities:

* Analyze transaction notes
* Match keywords against predefined category mappings
* Calculate category confidence score
* Return predicted expense category
* Support future extensibility for NLP or ML-based classification
"""