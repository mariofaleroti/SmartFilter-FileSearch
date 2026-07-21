# Security policy

## Supported version

Security fixes are currently applied to the latest stable `1.x` release.

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. Contact the repository owner privately through the contact method listed on the GitHub profile and include:

- affected Smart Filter version;
- reproduction steps;
- expected impact;
- operating system;
- any proposed mitigation.

Remove real documents, personal paths, credentials, tokens, and private content before sharing diagnostics.

## Privacy model

Smart Filter analyzes files locally. The application does not require uploading searched documents to an external service. Runtime state and generated content are stored outside version control under ignored directories such as `data/`, `runtime/`, and `output/`.
