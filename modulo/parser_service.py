"""
# parser_service.py

This module is responsible for parsing natural language-like transaction input into structured transaction data.
It extracts transaction type, amount, unit, and note from user input using regex-based parsing and preprocessing techniques.

Example:
-30k cafe → expense, 30000, "cafe"

Main responsibilities:

* Validate input format
* Parse amount and currency shorthand (k, tr, củ)
* Detect transaction type (income/expense)
* Normalize extracted data
* Build structured JSON response for API usage
"""