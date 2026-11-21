import os

# Must be set BEFORE importing the app, so tests use a separate database
os.environ["BOOKS_DB"] = "test_books.db"

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_database():
    # Runs before every test: empty both tables so tests don't affect each other
    with main.get_db() as conn:
        conn.execute("DELETE FROM books")
        conn.execute("DELETE FROM users")
    yield


def auth_headers(username="ada", password="password123"):
    # Register (ignored if the user already exists), log in, return the token header
    client.post("/register", json={"username": username, "password": password})
    response = client.post("/login", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_books_require_login():
    response = client.get("/books")
    assert response.status_code == 401


def test_add_and_list_book():
    headers = auth_headers()
    response = client.post(
        "/books", json={"title": "Things Fall Apart", "author": "Chinua Achebe"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Things Fall Apart"

    response = client.get("/books", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_empty_title_is_rejected():
    response = client.post(
        "/books", json={"title": "", "author": "Someone"}, headers=auth_headers()
    )
    assert response.status_code == 422


def test_get_missing_book_returns_404():
    response = client.get("/books/999", headers=auth_headers())
    assert response.status_code == 404


def test_mark_book_as_read():
    headers = auth_headers()
    book = client.post("/books", json={"title": "Book", "author": "Author"}, headers=headers).json()
    response = client.put(f"/books/{book['id']}", json={"read": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["read"] is True


def test_read_filter():
    headers = auth_headers()
    client.post("/books", json={"title": "A", "author": "X"}, headers=headers)
    b = client.post("/books", json={"title": "B", "author": "Y"}, headers=headers).json()
    client.put(f"/books/{b['id']}", json={"read": True}, headers=headers)

    read_books = client.get("/books?read=true", headers=headers).json()
    unread_books = client.get("/books?read=false", headers=headers).json()

    assert len(read_books) == 1
    assert len(unread_books) == 1


def test_delete_book():
    headers = auth_headers()
    book = client.post("/books", json={"title": "Temp", "author": "Me"}, headers=headers).json()
    assert client.delete(f"/books/{book['id']}", headers=headers).status_code == 200
    assert client.get(f"/books/{book['id']}", headers=headers).status_code == 404


def test_users_cannot_see_each_others_books():
    ada = auth_headers("ada", "password123")
    bola = auth_headers("bola", "password456")

    book = client.post("/books", json={"title": "Private", "author": "Ada"}, headers=ada).json()

    assert client.get("/books", headers=bola).json() == []
    assert client.get(f"/books/{book['id']}", headers=bola).status_code == 404
    assert client.delete(f"/books/{book['id']}", headers=bola).status_code == 404