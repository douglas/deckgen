# Contributing

Thanks for helping. deckgen is a small tool, so the bar for a change is "most decks would use it", and the simplest version that works wins.

## Reporting a bug

[Open an issue](https://github.com/douglas/deckgen/issues) with:

- `deckgen --version`, your OS, and your browser if it's about `pdf` or `snap`;
- the command you ran and its full output;
- **a small fictional spec** that shows the problem. Never attach a real deck, spec or snapshot: decks often hold private material.

## Sending a change

1. Read [DEVELOPMENT.md](DEVELOPMENT.md): it covers the architecture and the steps for adding blocks, diagrams and themes.
2. Keep the change focused, with tests for new behavior, and an entry under Unreleased in `CHANGELOG.md` for anything users will notice.
3. Run the checks; CI runs the same ones:

   ```
   uv run ruff format . && uv run ruff check .
   uv run mypy
   uv run python -W error::ResourceWarning -m unittest discover -s tests
   ```

4. For changes to output, render and snap `examples/showcase.yaml` and look at the slides you touched, in light and dark.

Agents are welcome contributors too; `AGENTS.md` has the rules they follow in this repo.

## License

deckgen is licensed under the [GNU AGPL v3 or later](LICENSE). By sending a change, you agree that it's licensed the same way.
