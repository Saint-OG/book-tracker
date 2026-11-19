import os

# Must be set BEFORE importing the app, so tests use a separate database
os.environ["BOOKS_DB"] = "test_books.db"

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_database():
    # Runs before every test: empty the table so tests don't affect each other
    with main.get_db() as conn:
        conn.execute("DELETE FROM books")
    yield


def test_add_and_list_book():
    response = client.post("/books", json={"title": "Things Fall Apart", "author": "Chinua Achebe"})
    assert response.status_code == 201
    assert response.json()["title"] == "Things Fall Apart"

    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_empty_title_is_rejected():
    response = client.post("/books", json={"title": "", "author": "Someone"})
    assert response.status_code == 422


def test_get_missing_book_returns_404():
    response = client.get("/books/999")
    assert response.status_code == 404


def test_mark_book_as_read():
    book = client.post("/books", json={"title": "Book", "author": "Author"}).json()
    response = client.put(f"/books/{book['id']}", json={"read": True})
    assert response.status_code == 200
    assert response.json()["read"] is True


def test_read_filter():
    client.post("/books", json={"title": "A", "author": "X"})
    b = client.post("/books", json={"title": "B", "author": "Y"}).json()
    client.put(f"/books/{b['id']}", json={"read": True})

    read_books = client.get("/books?read=true").json()
    unread_books = client.get("/books?read=false").json()

    assert len(read_books) == 1
    assert len(unread_books) == 1


def test_delete_book():
    book = client.post("/books", json={"title": "Temp", "author": "Me"}).json()
    assert client.delete(f"/books/{book['id']}").status_code == 200
    assert client.get(f"/books/{book['id']}").status_code == 404