import json
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
import src.books as books


@pytest.fixture(autouse=True)
def isolated_books(tmp_path, monkeypatch):
    monkeypatch.setattr(books, 'DATA_ROOT', str(tmp_path))


def test_library_persists_and_status_is_explicit():
    data = {'title':'  A Book  ', 'author':'An Author', 'isbn':'', 'language':'Greek', 'progress':42, 'status':'current', 'category':'engineering'}
    with TestClient(create_app()) as client:
        assert client.get('/api/books').json() == []
        response = client.post('/api/books', json=data)
        assert response.status_code == 201
        book = response.json()
        assert book['title'] == 'A Book' and book['language'] == 'Greek' and book['category'] == 'engineering'
        identifier = book['id']
        response = client.put('/api/books/' + identifier, json={**data, 'status':'done'})
        assert response.status_code == 200 and response.json()['progress'] == 42
        assert client.post('/api/books', json={**data, 'progress':101}).status_code == 422
        assert client.post('/api/books', json={**data, 'category':'invented'}).status_code == 400
        assert client.post('/api/books', json={**data, 'title':'  '}).status_code == 400
    with TestClient(create_app()) as client:
        assert client.get('/api/books').json()[0]['status'] == 'done'
        assert client.delete('/api/books/' + identifier).status_code == 204
        assert client.delete('/api/books/' + identifier).status_code == 404
        assert client.get('/api/books').json() == []


def test_isbn_uses_edition_and_title_search_uses_work(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs['params']))
        if url.endswith('/api/books'):
            return httpx.Response(200, request=httpx.Request('GET', url), json={'ISBN:9780140449136': {'title':'Crime and punishment', 'authors':[{'name':'Dostoevsky'}], 'publish_date':'2003'}})
        return httpx.Response(200, request=httpx.Request('GET', url), json={'docs':[{'title':'Pride and Prejudice', 'author_name':['Jane Austen'], 'first_publish_year':1813}]})
    monkeypatch.setattr(books.httpx, 'get', get)
    with TestClient(create_app()) as client:
        result = client.get('/api/books/search', params={'q':'978-0-14-044913-6'}).json()
        assert result == [{'title':'Crime and punishment', 'author':'Dostoevsky', 'isbn':'9780140449136', 'year':2003}]
        result = client.get('/api/books/search', params={'q':'pride prejud'}).json()
        assert result[0]['title'] == 'Pride and Prejudice' and result[0]['isbn'] == ''
        assert calls[1][1]['title'] == 'pride prejud'
        assert client.get('/api/books/search', params={'q':' '}).status_code == 400


def test_recommendation_uses_library_and_category(fake_openai):
    fake_openai.reply({'title':'A Recommendation', 'author':'A Writer', 'language':'French', 'reason':'A natural next step.'})
    with TestClient(create_app()) as client:
        client.post('/api/books', json={'title':'Existing', 'author':'A Writer', 'language':'French', 'progress':75, 'status':'current', 'category':'economics', 'rating':8})
        result = client.post('/api/books/recommend', json={'category':'self-improvement', 'language':'French'})
        assert result.status_code == 200 and result.json()['title'] == 'A Recommendation'
        prompt = fake_openai.calls[-1]['input']
        assert 'Existing' in prompt and 'Self-improvement' in prompt and 'French' in prompt
        assert json.loads(prompt.split('Library: ', 1)[1])[0]['progress'] == 75
        assert json.loads(prompt.split('Library: ', 1)[1])[0]['rating'] == 8
        fake_openai.reply('not json')
        assert client.post('/api/books/recommend', json={'category':'all', 'language':'Any'}).status_code == 502


def test_custom_subject_remains_available_when_empty():
    with TestClient(create_app()) as client:
        categories = client.get('/api/books/categories').json()
        assert {'financial', 'legal', 'engineering', 'economics', 'self-improvement'} <= {item['id'] for item in categories}
        created = client.post('/api/books/categories', json={'name':'  Cognitive Science  '})
        assert created.status_code == 201
        assert created.json() == {'id':'cognitive-science', 'name':'Cognitive Science', 'group':'nonfiction'}
        book = client.post('/api/books', json={'title':'A Book','language':'English','progress':0,'status':'current','category':'cognitive-science'}).json()
        assert client.delete('/api/books/' + book['id']).status_code == 204
    with TestClient(create_app()) as client:
        assert 'cognitive-science' in {item['id'] for item in client.get('/api/books/categories').json()}
        assert client.get('/api/books').json() == []


def test_book_lookup_and_storage_do_not_require_an_ai_model(monkeypatch):
    monkeypatch.setattr('backend.app.available_models', lambda: (_ for _ in ()).throw(AssertionError('AI lookup should not run')))
    monkeypatch.setattr('backend.app.search_books', lambda query: [{'title':'A Book', 'author':'Writer', 'isbn':'', 'year':None}])
    with TestClient(create_app()) as client:
        headers = {'X-OpenAI-Model': 'saved-model'}
        assert client.get('/api/books/search?q=book', headers=headers).status_code == 200
        assert client.get('/api/books', headers=headers).status_code == 200
        assert client.post('/api/books', headers=headers, json={'title':'A Book','language':'English','progress':0,'status':'current'}).status_code == 201


def test_ratings_are_optional_editable_and_validated():
    data = {'title': 'Rated book', 'language': 'English', 'progress': 5, 'status': 'current', 'rating': 8}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        assert book['rating'] == 8
        url = '/api/books/' + book['id']
        assert client.put(url, json={**data, 'rating': 7}).json()['rating'] == 7
        assert client.put(url, json={**data, 'rating': None}).json()['rating'] is None
        for invalid in (0, 11):
            assert client.put(url, json={**data, 'rating': invalid}).status_code == 422
        assert client.get('/api/books').json()[0]['progress'] == 5


def test_old_library_is_migrated_without_losing_books(tmp_path):
    from sqlite3 import connect
    db = connect(tmp_path / 'books.db')
    db.execute("CREATE TABLE books (id TEXT PRIMARY KEY, title TEXT, author TEXT, isbn TEXT, language TEXT, progress INTEGER, status TEXT, created_at TEXT, updated_at TEXT, category TEXT)")
    db.execute("INSERT INTO books VALUES ('old', 'Existing', 'Writer', '', 'French', 25, 'current', 'date', 'date', 'fiction')")
    db.commit()
    db.close()
    with TestClient(create_app()) as client:
        book = client.get('/api/books').json()[0]
        assert book['title'] == 'Existing' and book['progress'] == 25 and book['rating'] is None


def test_book_notes_are_independent_and_detect_conflicts():
    data = {'title': 'Book', 'language': 'English', 'progress': 25, 'status': 'current'}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        other = client.post('/api/books', json={**data, 'title': 'Other'}).json()
        url = '/api/books/' + book['id'] + '/notes'
        assert client.get(url).json() == {'markdown': '', 'revision': 0}
        assert client.get('/api/books/missing/notes').status_code == 404
        assert client.put('/api/books/missing/notes', json={'markdown': 'x', 'revision': 0}).status_code == 404
        saved = client.put(url, json={'markdown': '# Ideas\n\n**A** $x^2$', 'revision': 0})
        assert saved.status_code == 200 and saved.json()['revision'] == 1
        assert client.put(url, json={'markdown': 'stale', 'revision': 0}).status_code == 409
        assert client.get(url).json()['markdown'] == '# Ideas\n\n**A** $x^2$'
        assert client.get('/api/books/' + other['id'] + '/notes').json()['markdown'] == ''
        assert client.put('/api/books/' + book['id'], json={**data, 'progress': 40}).status_code == 200
        assert client.get(url).json()['revision'] == 1
        assert client.put(url, json={'markdown': '', 'revision': 1}).json()['revision'] == 2
        assert client.delete('/api/books/' + book['id']).status_code == 204
        assert client.get(url).status_code == 404
        connection = books._connection()
        try:
            assert connection.execute('SELECT COUNT(*) FROM book_notes').fetchone()[0] == 0
        finally:
            connection.close()
