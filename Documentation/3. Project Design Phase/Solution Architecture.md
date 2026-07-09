# Solution Architecture

```mermaid
flowchart TB
    subgraph Frontend
        S[Streamlit App]
    end
    subgraph Backend
        F[Auth Routes]
        C[Conversation Routes]
        V[Services]
        D[Database Layer]
    end
    subgraph External
        M[DistilBERT]
        G[Gemini API]
        W[Wikipedia API]
    end

    S --> F
    S --> C
    C --> V
    V --> M
    V --> G
    V --> W
    V --> D
```

