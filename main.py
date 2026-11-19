import sqlite3
import os
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
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0
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

# @app.get("/books")
# def list_books():
#     with get_db() as conn:
#         rows = conn.execute("SELECT * FROM books").fetchall()
#         return [row_to_dict(row) for row in rows]

@app.get("/books")
def list_books(read: bool | None = None):
    with get_db() as conn:
        if read is None:
            rows = conn.execute("SELECT * FROM books").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM books WHERE read = ?", (int(read),)
            ).fetchall()
        return [row_to_dict(row) for row in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return row_to_dict(row)


@app.post("/books", status_code=201)
def add_book(book: BookCreate):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (book.title, book.author),
        )
        new_id = cursor.lastrowid
    return {"id": new_id, "title": book.title, "author": book.author, "read": False}


@app.put("/books/{book_id}")
def update_book(book_id: int, update: BookUpdate):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
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
def delete_book(book_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
        return {"message": "Book deleted"}