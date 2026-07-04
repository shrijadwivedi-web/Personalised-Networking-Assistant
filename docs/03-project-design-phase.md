# 3. Project Design Phase

## Architecture

The project uses a two-part architecture:

- Streamlit frontend for the user interface
- FastAPI backend for authentication, conversation generation, fact checking, and persistence

## Major Components

- `app/main.py` creates the API application and registers routes
- `app/routes/auth.py` handles registration and login
- `app/routes/conversation.py` handles the main assistant workflows
- `frontend/app.py` provides the home page and generation flow
- `frontend/pages/` contains profile, fact check, history, and feedback pages

## Design Choices

- Keep the frontend and backend loosely coupled through HTTP
- Store all account-specific data in the database
- Use service modules to keep route handlers small
- Use a consistent sidebar layout in Streamlit for a simple workflow

## Expected User Flow

1. User registers or logs in
2. User fills in profile details
3. User describes the event and interests
4. The app generates conversation starters and confidence scores
5. The user checks facts, reviews history, and leaves feedback

