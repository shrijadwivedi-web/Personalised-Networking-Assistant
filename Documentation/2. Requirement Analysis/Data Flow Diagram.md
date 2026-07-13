<img width="1476" height="1298" alt="image" src="https://github.com/user-attachments/assets/5c4b9f55-28eb-4bfd-92a1-5475b4321f28" />


# Data Flow Diagram

```mermaid
flowchart LR
    U[User] --> F[Streamlit Frontend]
    F --> B[FastAPI Backend]
    B --> A[Authentication]
    B --> T[Theme Extraction]
    B --> G[Conversation Generation]
    B --> C[Fact Checking]
    B --> H[History and Feedback]
    T --> M[DistilBERT]
    G --> N[Gemini API]
    C --> W[Wikipedia API]
    H --> S[SQLite Database]
```

