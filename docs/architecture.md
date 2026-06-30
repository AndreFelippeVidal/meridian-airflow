# Architecture

Replace the placeholder below with the real flow. Keep it in Mermaid so it renders on GitHub.

\`\`\`mermaid
flowchart LR
    subgraph Sources
        S[Meridian synthetic data]
    end
    S --> I[Ingestion]
    I --> L[(Lakehouse / Warehouse)]
    L --> T[Transformations]
    T --> SV[Serving / API / Dashboard]
\`\`\`

## Decisions
See docs/adr/ for the reasoning behind each component choice.
