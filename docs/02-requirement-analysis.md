# 2. Requirement Analysis

## Functional Requirements

- Users can register and log in securely
- Users can generate networking conversation starters from an event description
- Users can store profile details such as role, industry, and networking goal
- Users can fact-check a topic quickly
- Users can review history and feedback from previous suggestions

## Non-Functional Requirements

- The app should be responsive and easy to use
- User data should remain private per account
- Errors should be handled gracefully
- The system should support local development and Docker-based deployment

## Technology Decisions

- FastAPI for the backend
- Streamlit for the frontend
- SQLite for local persistence
- JWT for authentication
- DistilBERT for local theme extraction
- Gemini API for conversation generation
- Wikipedia API for quick fact checking

## Data Considerations

- User accounts must be isolated by `user_id`
- Conversation history and feedback must be tied to the account that created them
- Secrets and API keys should stay out of version control

