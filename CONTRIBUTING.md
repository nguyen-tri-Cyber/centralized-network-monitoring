# Contributing Guidelines

Thank you for your interest in contributing to the **Centralized Network Monitoring System** thesis project!

## Code of Academic Integrity

As an undergraduate thesis and open-source portfolio project, all contributions must uphold strict academic honesty:
- **No Fabricated Benchmarks**: Never commit synthetic or guessed performance numbers into documentation without explicitly labeling them as synthetic or using `[TODO]` placeholders.
- **Reproducibility**: Ensure all newly added configurations or modules can be tested and verified using automated test commands.

## How to Contribute

1. **Fork and Branch**: Create a feature branch off `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Adhere to Code Standards**:
   - Python code must follow PEP 8 and include unit tests in `tests/`.
   - YAML files must use 2-space indentation.
   - Pinned versions must be used for container images (no `latest`).
3. **Run Validation Checks**:
   Before opening a Pull Request, run the local validation suite:
   ```bash
   python scripts/validate.py
   ```
4. **Submit a Pull Request**: Provide a clear description of the problem solved, architectural changes made, and test evidence.
