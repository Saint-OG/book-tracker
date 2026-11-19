import sqlite3
import os
import secrets

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

# DB_NAME = "books.db"

DB_NAME = os.environ.get("BOOKS_DB", "books.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    try:
        yield conn
        conn.commit()  # save changes if nothing went wrong
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                owner_id INTEGER NOT NULL REFERENCES users(id)
            )
            """
        )


def row_to_dict(row):
    book = dict(row)
    book["read"] = bool(book["read"])  # SQLite stores 0/1, we want False/True
    return book


init_db()


# class BookCreate(BaseModel):
#     title: str
#     author: str


# class BookUpdate(BaseModel):
#     title: str | None = None
#     author: str | None = None
#     read: bool | None = None

class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=100)
    read: bool | None = None

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/register", status_code=201)
def register(user: UserCreate):
    hashed = password_hash.hash(user.password)
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (user.username, hashed),
            )
            return {"id": cursor.lastrowid, "username": user.username}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (form.username,)
        ).fetchone()
    if row is None or not password_hash.verify(form.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_token(row["id"]), "token_type": "bearer"}

# @app.get("/books")
# def list_books():
#     with get_db() as conn:
#         rows = conn.execute("SELECT * FROM books").fetchall()
#         return [row_to_dict(row) for row in rows]

@app.get("/books")
def list_books(read: bool | None = None, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        if read is None:
            rows = conn.execute(
                "SELECT * FROM books WHERE owner_id = ?", (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM books WHERE owner_id = ? AND read = ?",
                (user_id, int(read)),
            ).fetchall()
        return [row_to_dict(row) for row in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ? AND owner_id = ?", (book_id, user_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return row_to_dict(row)


@app.post("/books", status_code=201)
def add_book(book: BookCreate, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, owner_id) VALUES (?, ?, ?)",
            (book.title, book.author, user_id),
        )
        new_id = cursor.lastrowid
    return {"id": new_id, "title": book.title, "author": book.author, "read": False}


@app.put("/books/{book_id}")
def update_book(book_id: int, update: BookUpdate, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ? AND owner_id = ?", (book_id, user_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")

        book = row_to_dict(row)
        book.update(update.model_dump(exclude_unset=True))

        conn.execute(
            "UPDATE books SET title = ?, author = ?, read = ? WHERE id = ?",
            (book["title"], book["author"], int(book["read"]), book_id),
        )
        return book


@app.delete("/books/{book_id}")
def delete_book(book_id: int, user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM books WHERE id = ? AND owner_id = ?", (book_id, user_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
        return {"message": "Book deleted"}