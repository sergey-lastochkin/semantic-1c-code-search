# Changelog

All notable changes to this project will be documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-08-29

### Added

- A Windows PowerShell quick start using the prebuilt release wheel.
- A terminal GIF recorded against the redistributable example BSL module.
- Windows and Ubuntu CI coverage for Python 3.11 and 3.12.
- Distribution build, wheel smoke test, and downloadable CI artifacts.

### Changed

- The package version is now `0.1.1`.

## [0.1.0] - 2026-08-28

### Added

- Directory-wide search for exported `.bsl` files.
- Human-readable CLI results with source paths and line ranges.
- Optional hybrid retrieval with the pinned local multilingual E5 model.
- Machine-readable output through `code-search search --json`.
- Apache-2.0 license, package metadata, contribution guide, and issue forms.

### Changed

- Query and passage prefixes are now applied correctly for retrieval models
  that distinguish the two roles.
