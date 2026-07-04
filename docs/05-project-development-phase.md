# 5. Project Development Phase

## Implemented Features

- User registration and login
- JWT-based session handling
- Profile storage for role, industry, and goal
- Event theme extraction using DistilBERT
- Conversation starter generation with Gemini
- Confidence scoring for generated starters
- Fact checking through Wikipedia
- Conversation history tracking
- Feedback logging
- Streamlit page navigation

## Code Organization

- Route handlers are kept in `app/routes/`
- Business logic sits in `app/services/`
- UI helpers live in `frontend/common.py`
- Each Streamlit page has a focused responsibility

## Development Notes

- Shared state is managed in `st.session_state`
- The backend returns clear error messages instead of stack traces
- Rate limiting is applied to the expensive endpoints
- Docker files are included for full-stack deployment

