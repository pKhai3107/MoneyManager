## 1. Coding Standards
- **Language:** We use Python 3.12. All functions MUST include type hints.
- **Database Architecture:** All database interactions MUST go through `modulo/db_helper.py`.
- Do not write raw SQLite queries in other files.
- **Style:** Follow PEP 8 strictly.
    
## 2. Testing & Workflow Mandates
- Every new feature in the `modulo/` directory must have a corresponding test.
- After making code changes, ALWAYS run `python -m unittest` to verify. Do not consider a task complete if tests fail.
   
## 3. Project Context
   **FinanceManager** is a local CLI tool for tracking personal expenses.