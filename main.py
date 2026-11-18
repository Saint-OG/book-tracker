from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# In-memory "database": just a list of dictionaries
books = []
next_id = 1


class BookCreate(BaseModel):
    title: str
    author: str


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    read: bool | None = None


@app.get("/books")
def list_books():
    return books


@app.post("/books", status_code=201)
def add_book(book: BookCreate):
    global next_id
    new_book = {
        "id": next_id,
        "title": book.title,
        "author": book.author,
        "read": False,
    }
    books.append(new_book)
    next_id += 1
    return new_book


@app.put("/books/{book_id}")
def update_book(book_id: int, update: BookUpdate):
    for book in books:
        if book["id"] == book_id:
            changes = update.model_dump(exclude_unset=True)
            book.update(changes)
            return book
    raise HTTPException(status_code=404, detail="Book not found")


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            books.remove(book)
            return {"message": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")