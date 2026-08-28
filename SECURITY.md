# Security policy

Please report a suspected vulnerability privately through GitHub's security
advisory feature instead of opening a public issue.

The CLI reads local source files and does not send them to a remote service.
The optional embedding model is downloaded by `sentence-transformers` on first
use and then runs locally. Review the configured model name before using a
custom model.
