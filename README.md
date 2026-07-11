# gd-tools

A modern development workflow CLI for GDScript projects in Godot 4.5+.

## Installation

```bash
pip install gd-tools
```

## Development

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/mansyar/gd-tools.git
cd gd-tools
pip install -e ".[dev]"
```

### Running Tests

Unit tests run without Godot. Integration tests require a Godot 4.5+
binary — configure via `.env` (see `.env.example`):

```bash
cp .env.example .env
# Edit .env: set GODOT_BIN to your Godot binary path

# Run all tests with coverage
pytest --cov=src/gd_tools --cov-report=term-missing
```

See `docs/TESTING_STRATEGY.md` for the full testing guide.
