# Contributing

Thanks for helping make this course better! Useful contributions include:

- 🐛 **Fixes**: typos, wrong explanations, broken links, failing labs
- 📚 **Resources**: a better *free* resource for a topic (please explain why it's better)
- 🧪 **Exercises**: new "Break it" or "Extend it" exercises with solutions
- 🌍 **Translations**: open an issue first so we can agree on the folder structure

## Before you open a PR

1. Read [docs/course-conventions.md](docs/course-conventions.md). Every lesson follows the same template and every lab follows the same code rules.
2. Run the checks:
   ```bash
   python3 tools/check_links.py
   cd modules/<module>/lab && uv sync && uv run pytest -q
   ```
3. Keep labs free and offline: tests must pass with `KESTREL_LLM_PROVIDER=fake` and no API keys.
4. Never invent statistics, quotes or case studies about real companies. Link the real public source.

## Reporting a problem

Open an issue with the lesson or lab, what you ran, what you expected, what happened, and your OS and Python version.
