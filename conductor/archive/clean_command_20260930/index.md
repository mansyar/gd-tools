# Track: Clean Command (Roadmap Track 39)

- **Track ID:** `clean_command_20260930`
- **Type:** Feature
- **Status:** New
- **Branch:** `feature/clean-command-20260930`
- **Created:** 2026-09-30

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Add `gd-tools clean` to remove generated artifacts under `.gd-tools/`
(`--coverage`, `--artifacts`, `--baselines`, `--cache`, `--all`, `--dry-run`).
With no flags the command prints an inventory + hint and deletes nothing.
Protected paths (`addons/**` including `.backups/`, `gd-tools.toml`,
`.gutconfig.json`, home cache `~/.gd-tools`) are never touched.
