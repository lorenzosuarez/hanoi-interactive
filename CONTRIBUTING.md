# Contributing

Thank you for your interest in improving **Hanoi Interactive Pro**.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Coding guidelines
- Python 3.8+
- Keep code-level explanations in **docstrings** (no inline comments).
- UI changes must preserve full disk visibility and interval accuracy.

## Pull requests
- Describe UX changes and attach a short screen capture or gif.
- Ensure `import hanoi_pro.ui` works with `MPLBACKEND=Agg` in CI.
