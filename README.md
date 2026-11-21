# Book Tracker API

A full-stack book tracking app. Users register, log in, and manage their own reading list. Built to learn backend development with Python.

**Live demo:** https://book-tracker-9dgo.onrender.com
**API docs:** https://book-tracker-9dgo.onrender.com/docs

> The demo runs on a free hosting tier. It sleeps after inactivity, so the first load can take about 30 seconds, and the data resets when it sleeps. If you can't log in, just register again.

## Features

- User registration and login with hashed passwords (Argon2) and JWT tokens
- Each user sees and edits only their own books
- Add, list, update, and delete books
- Filter books by read status
- Input validation with clear error messages
- A simple web page built with plain HTML, CSS, and JavaScript
- Automated tests with pytest

## Tech stack

- Python 3.13 and FastAPI
- SQLite
- PyJWT and pwdlib for authentication
- pytest for testing
- Deployed on Render

## API endpoints

| Method | Path | Description | Login required |
|---|---|---|---|
| POST | `/register` | Create an account | No |
| POST | `/login` | Get an access token | No |
| GET | `/books` | List your books (optional `?read=true` or `?read=false`) | Yes |
| GET | `/books/{id}` | Get one book | Yes |
| POST | `/books` | Add a book | Yes |
| PUT | `/books/{id}` | Update a book | Yes |
| DELETE | `/books/{id}` | Delete a book | Yes |

## Run it locally

```bash
git clone https://github.com/Saint-OG/book-tracker.git
cd book-tracker
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

Then open http://127.0.0.1:8000 for the web page or http://127.0.0.1:8000/docs for the interactive API docs.

Optionally set your own secret key for signing tokens:

```bash
set SECRET_KEY=your-long-random-string      # Mac/Linux: export SECRET_KEY=...
```

## Run the tests

```bash
pytest
```

## What I learned

- Building REST APIs and working with a SQL database
- Password hashing, tokens, and protecting user data
- Writing automated tests
- Using Git and GitHub, and deploying to the cloud

## Possible next steps

- Move from SQLite to PostgreSQL so data persists on free hosting
- Add Docker support
- Improve the page styling