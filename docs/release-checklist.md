# Public release checklist

## Repository metadata

- Description: `Offline search across exported 1C/BSL code with BM25 and local embeddings.`
- Topics: `1c`, `1c-enterprise`, `bsl`, `code-search`, `semantic-search`,
  `static-analysis`, `developer-tools`, `python`.
- Website: leave empty until a stable live demo or documentation site exists.
- Social preview: upload `assets/social-preview.png` in repository settings.

## v0.1.0

- Run the documented test, Ruff, and compile checks.
- Confirm GitHub recognizes `Apache-2.0` on the repository page.
- Confirm both README quick-start commands in a clean environment.
- Create tag `v0.1.0` from the reviewed commit.
- Publish a GitHub release using the `Unreleased` section of `CHANGELOG.md`.
- Do not publish to PyPI until the package name and trusted-publishing setup have
  been verified.

## Launch material

- Record a 15–25 second terminal GIF against a redistributable BSL fixture.
- Lead with the user result; link the full benchmark after the quick start.
- Suggested article: `BM25 vs embeddings for BSL: evidence from 156,869 lines`.
- Ask users for difficult queries and minimal fixtures, not only stars.
