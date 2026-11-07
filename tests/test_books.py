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
        assert result == [{'title':'Crime and punishment', 'author':'Dostoevsky', 'isbn':'9780140449136', 'year':2003, 'totalPages':None}]
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
        assert book['personalCategory'] == 'literature' and book['category'] == 'fiction'


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


def test_progress_updates_and_page_count_lookup_preserve_other_book_data(monkeypatch):
    data = {'title':'Progress book', 'author':'Writer', 'isbn':'9780140449136', 'language':'English', 'progress':20, 'status':'current', 'rating':8}
    monkeypatch.setattr(books, 'search_books', lambda isbn: [{'totalPages': 320}])
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        url = '/api/books/' + book['id']
        assert book['totalPages'] is None and book['currentPage'] is None
        assert client.post(url + '/page-count', json={}).json() == {'totalPages': 320}
        assert client.patch(url + '/progress', json={'progress':20, 'currentPage':80, 'totalPages':320}).status_code == 400
        updated = client.patch(url + '/progress', json={'progress':20, 'currentPage':80, 'totalPages':320, 'lastReadablePage':320}).json()
        assert updated['progress'] == 25 and updated['currentPage'] == 80 and updated['totalPages'] == 320
        assert updated['rating'] == 8 and updated['title'] == 'Progress book'
        assert client.patch(url + '/progress', json={'progress':20, 'currentPage':321, 'totalPages':320}).status_code == 400
        assert client.patch(url + '/progress', json={'progress':101}).status_code == 422
        updated = client.patch(url + '/progress', json={'progress':40}).json()
        assert updated['progress'] == 40 and updated['currentPage'] is None and updated['totalPages'] == 320
        assert client.get('/api/books').json()[0]['progress'] == 40
        assert client.patch('/api/books/missing/progress', json={'progress':30}).status_code == 404


def test_progress_page_count_unavailable_without_inventing_one(monkeypatch):
    monkeypatch.setattr(books, 'search_books', lambda isbn: [])
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json={'title':'Unknown', 'isbn':'9780140449136', 'language':'English', 'progress':10, 'status':'current'}).json()
        assert client.post('/api/books/' + book['id'] + '/page-count', json={}).json() == {'totalPages': None}
        assert client.get('/api/books').json()[0]['progress'] == 10


def test_book_cover_is_cached_per_isbn_and_works_offline(monkeypatch, tmp_path):
    from contextlib import contextmanager
    calls = []
    jpeg = b'\xff\xd8\xfftest-cover\xff\xd9'
    class Response:
        status_code = 200
        headers = {'content-type': 'image/jpeg'}
        def raise_for_status(self): pass
        def iter_bytes(self): yield jpeg
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @contextmanager
        def stream(self, method, url):
            calls.append(url)
            yield Response()
    monkeypatch.setattr(books.httpx, 'Client', Client)
    data = {'title':'Cover book', 'isbn':'9780140449136', 'language':'English', 'progress':25, 'status':'current'}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        url = '/api/books/' + book['id'] + '/cover'
        response = client.get(url)
        assert response.status_code == 200 and response.content == jpeg
        assert (tmp_path / 'book-covers' / '9780140449136.jpg').read_bytes() == jpeg
        assert client.get(url).content == jpeg and len(calls) == 1
        assert client.get('/api/books/missing/cover').status_code == 404
        assert client.put('/api/books/' + book['id'], json={**data, 'isbn':''}).status_code == 200
        assert client.get(url).status_code == 404
        assert len(calls) == 1


def test_book_cover_rejects_external_redirect_and_invalid_images(monkeypatch):
    from contextlib import contextmanager
    class Response:
        status_code = 302
        headers = {'location': 'http://127.0.0.1/private'}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @contextmanager
        def stream(self, method, url): yield Response()
    monkeypatch.setattr(books.httpx, 'Client', Client)
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json={'title':'Untrusted', 'isbn':'9780306406157', 'language':'English', 'progress':0, 'status':'current'}).json()
        assert client.get('/api/books/' + book['id'] + '/cover').status_code == 404


def test_to_read_categories_edit_start_and_duplicate_handling():
    data = {'title':'Future Book', 'author':'A Writer', 'isbn':'', 'language':'English', 'category':'literature'}
    with TestClient(create_app()) as client:
        assert 'literature' in {item['id'] for item in client.get('/api/books/categories').json()}
        assert client.get('/api/books/to-read').json() == []
        result = client.post('/api/books/to-read', json=data)
        assert result.status_code == 201
        item = result.json()
        assert client.post('/api/books/to-read', json={**data, 'title':' future book '}).status_code == 409
        assert client.post('/api/books/to-read', json={**data, 'category':'invalid'}).status_code == 422
        url = '/api/books/to-read/' + item['id']
        assert client.put(url, json={**data, 'category':'education'}).json()['category'] == 'education'
    with TestClient(create_app()) as client:
        assert client.get('/api/books/to-read').json()[0]['category'] == 'education'
        assert client.put(url, json=data).status_code == 200
        result = client.post(url + '/start')
        assert result.status_code == 200
        assert result.json()['category'] == 'literature' and result.json()['status'] == 'current'
        assert result.json()['personalCategory'] == 'literature'
        assert client.get('/api/books/to-read').json() == []
        assert client.post(url + '/start').status_code == 404
        item = client.post('/api/books/to-read', json=data).json()
        assert client.post('/api/books/to-read/' + item['id'] + '/start').status_code == 409
        assert len(client.get('/api/books/to-read').json()) == 1
        assert client.delete('/api/books/to-read/' + item['id']).status_code == 204


def test_recommendation_skips_to_read_and_recent_suggestions(fake_openai):
    with TestClient(create_app()) as client:
        client.post('/api/books/to-read', json={'title':'Saved idea', 'author':'A Writer', 'language':'English', 'category':'work'})
        responses = iter([
            {'title':'Saved idea','author':'A Writer','language':'English','reason':'A'},
            {'title':'Earlier idea','author':'B Writer','language':'English','reason':'B'},
            {'title':'Fresh idea','author':'C Writer','language':'English','reason':'C'},
        ])
        fake_openai.reply(lambda _: json.dumps(next(responses)))
        result = client.post('/api/books/recommend', json={'category':'all', 'language':'English', 'exclude':[{'title':'Earlier idea','author':'B Writer'}]})
        assert result.status_code == 200 and result.json()['title'] == 'Fresh idea'
        assert len(fake_openai.calls) == 3
        assert 'Saved idea' in fake_openai.calls[0]['input'] and 'Earlier idea' in fake_openai.calls[0]['input']
        fake_openai.reply({'title':'Saved idea','author':'A Writer','language':'English','reason':'A'})
        result = client.post('/api/books/recommend', json={'category':'all', 'language':'English'})
        assert result.status_code == 502 and 'repeated' in result.json()['detail']


def test_personal_category_is_independent_and_legacy_updates_preserve_it():
    data = {'title':'Career book', 'language':'English', 'progress':15, 'status':'current', 'category':'legal', 'personalCategory':'education'}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        assert book['personalCategory'] == 'education' and book['category'] == 'legal'
        url = '/api/books/' + book['id']
        changed = client.put(url, json={**data, 'status':'done', 'personalCategory':'work'}).json()
        assert changed['personalCategory'] == 'work' and changed['category'] == 'legal'
        legacy = {key:value for key,value in data.items() if key != 'personalCategory'}
        changed = client.put(url, json={**legacy, 'status':'done'}).json()
        assert changed['personalCategory'] == 'work' and changed['category'] == 'legal'
        assert client.put(url, json={**data, 'personalCategory':'invalid'}).status_code == 422
    with TestClient(create_app()) as client:
        assert client.get('/api/books').json()[0]['personalCategory'] == 'work'


def test_last_readable_page_allows_manual_page_progress_and_preserves_catalogue_count():
    data = {'title':'Manual pages', 'language':'English', 'progress':20, 'status':'current', 'rating':8}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        url = '/api/books/' + book['id'] + '/progress'
        saved = client.patch(url, json={'progress':20, 'lastReadablePage':400}).json()
        assert saved['lastReadablePage'] == 400 and saved['progress'] == 20 and saved['totalPages'] is None
        result = client.patch(url, json={'progress':20, 'currentPage':100})
        assert result.json()['progress'] == 25 and result.json()['lastReadablePage'] == 400
        result = client.patch(url, json={'progress':25, 'currentPage':410, 'totalPages':450})
        assert result.status_code == 400 and 'must not exceed' in result.json()['detail']
        assert client.get('/api/books').json()[0]['currentPage'] == 100
        result = client.patch(url, json={'progress':25, 'currentPage':400, 'totalPages':450})
        assert result.json()['progress'] == 100 and result.json()['totalPages'] == 450
        result = client.patch(url, json={'progress':100, 'currentPage':100, 'lastReadablePage':None})
        assert result.status_code == 400
        result = client.patch(url, json={'progress':22, 'lastReadablePage':None})
        assert result.json()['lastReadablePage'] is None and result.json()['progress'] == 22
        assert client.patch(url, json={'progress':20, 'lastReadablePage':0}).status_code == 422
        assert client.get('/api/books').json()[0]['rating'] == 8


def test_current_limit_preserves_existing_books_and_blocks_all_entry_paths(monkeypatch):
    data = {'title':'Book', 'author':'Writer', 'language':'English', 'progress':25, 'status':'current', 'category':'legal', 'rating':8}
    with TestClient(create_app()) as client:
        monkeypatch.setattr(books, 'CURRENT_BOOK_LIMIT', 7)
        existing = [client.post('/api/books', json={**data, 'title':f'Book {i}'}).json() for i in range(7)]
        monkeypatch.setattr(books, 'CURRENT_BOOK_LIMIT', 5)
        waiting = client.post('/api/books/to-read', json={'title':'Waiting', 'author':'Writer', 'language':'English', 'category':'work'}).json()
        done = client.post('/api/books', json={**data, 'title':'Completed', 'status':'done'}).json()
        assert len([b for b in client.get('/api/books').json() if b['status']=='current']) == 7
        assert client.post('/api/books', json={**data, 'title':'Extra'}).status_code == 409
        assert client.put('/api/books/' + done['id'], json={**data, 'title':'Completed'}).status_code == 409
        assert client.post('/api/books/to-read/' + waiting['id'] + '/start').status_code == 409
        assert len(client.get('/api/books/to-read').json()) == 1
        assert client.put('/api/books/missing', json=data).status_code == 404
        assert client.put('/api/books/' + existing[0]['id'], json={**data, 'title':'Updated 0', 'rating':9}).status_code == 200
        for i in range(3):
            assert client.put('/api/books/' + existing[i]['id'], json={**data, 'title':f'Book {i}', 'status':'done'}).status_code == 200
        assert client.post('/api/books/to-read/' + waiting['id'] + '/start').status_code == 200
        assert len([b for b in client.get('/api/books').json() if b['status']=='current']) == 5
        assert client.post('/api/books', json={**data, 'title':'Another'}).status_code == 409


def test_current_limit_is_atomic_for_simultaneous_additions():
    from concurrent.futures import ThreadPoolExecutor
    data = {'title':'Book', 'author':'Writer', 'language':'English', 'progress':0, 'status':'current'}
    with TestClient(create_app()) as client:
        for i in range(4):
            assert client.post('/api/books', json={**data, 'title':f'Book {i}'}).status_code == 201
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda i: client.post('/api/books', json={**data, 'title':f'New {i}'}).status_code, range(2)))
        assert sorted(statuses) == [201, 409]
        assert len([b for b in client.get('/api/books').json() if b['status']=='current']) == 5


def test_book_input_validation_checks_isbn_whitespace_and_numbers():
    data = {'title':'Book', 'language':'English', 'progress':0, 'status':'current'}
    with TestClient(create_app()) as client:
        assert client.post('/api/books', json={**data, 'title':'  '}).status_code == 400
        assert client.post('/api/books', json={**data, 'language':'  '}).status_code == 400
        assert client.post('/api/books', json={**data, 'isbn':'9780306406158'}).status_code == 400
        assert client.post('/api/books', json={**data, 'isbn':'4006381333931'}).status_code == 400
        assert client.post('/api/books', json={**data, 'isbn':'0-306-40615-2'}).status_code == 201
        assert client.post('/api/books', json={**data, 'progress':True}).status_code == 422
        assert client.post('/api/books', json={**data, 'progress':1.5}).status_code == 422
        assert client.post('/api/books/to-read', json={'title':'Book','language':'English','category':'work','isbn':'9780306406158'}).status_code == 400
        assert client.get('/api/books/search', params={'q':'9780306406158'}).status_code == 400


def test_legacy_invalid_isbn_does_not_block_unrelated_edits():
    data = {'title':'Old book', 'language':'English', 'progress':0, 'status':'current'}
    with TestClient(create_app()) as client:
        item = client.post('/api/books', json=data).json()
        db = books._connection()
        try:
            db.execute('UPDATE books SET isbn=? WHERE id=?', ('bad-old-isbn', item['id']))
            db.commit()
        finally:
            db.close()
        url = '/api/books/' + item['id']
        assert client.put(url, json={**data, 'isbn':'bad-old-isbn', 'title':'Updated book'}).status_code == 200
        assert client.put(url, json={**data, 'isbn':'different-bad-isbn'}).status_code == 400


def test_legacy_page_without_last_page_remains_intact():
    data = {'title':'Legacy pages', 'language':'English', 'progress':25, 'status':'current'}
    with TestClient(create_app()) as client:
        book = client.post('/api/books', json=data).json()
        db = books._connection()
        try:
            db.execute('UPDATE books SET current_page=80, total_pages=320 WHERE id=?', (book['id'],))
            db.commit()
        finally:
            db.close()
        before = client.get('/api/books').json()[0]
        assert before['currentPage'] == 80 and before['lastReadablePage'] is None and before['progress'] == 25
        result = client.patch('/api/books/' + book['id'] + '/progress', json={'progress':25, 'currentPage':80, 'totalPages':320})
        assert result.status_code == 400
        after = client.get('/api/books').json()[0]
        assert after['currentPage'] == 80 and after['lastReadablePage'] is None and after['progress'] == 25


def test_book_edit_progress_and_notes_move_to_top_persistently():
    data = {'title':'First', 'author':'Writer', 'language':'English', 'progress':0, 'status':'current', 'category':'other'}
    with TestClient(create_app()) as client:
        first = client.post('/api/books', json=data).json()
        second = client.post('/api/books', json={**data, 'title':'Second'}).json()
        assert [item['id'] for item in client.get('/api/books').json()] == [second['id'], first['id']]
        assert client.patch('/api/books/' + first['id'] + '/progress', json={'progress':25}).status_code == 200
        assert [item['id'] for item in client.get('/api/books').json()] == [first['id'], second['id']]
        notes_url = '/api/books/' + second['id'] + '/notes'
        assert client.put(notes_url, json={'markdown':'# Notes', 'revision':0}).status_code == 200
        assert [item['id'] for item in client.get('/api/books').json()] == [second['id'], first['id']]
        assert client.put('/api/books/' + first['id'], json={**data, 'title':'Edited'}).status_code == 200
        assert [item['id'] for item in client.get('/api/books').json()] == [first['id'], second['id']]
        assert client.put(notes_url, json={'markdown':'Conflict', 'revision':0}).status_code == 409
        assert [item['id'] for item in client.get('/api/books').json()] == [first['id'], second['id']]
    with TestClient(create_app()) as client:
        assert [item['id'] for item in client.get('/api/books').json()] == [first['id'], second['id']]


def test_to_read_edits_move_book_to_top_and_preserve_original_creation_date():
    data = {'title':'First waiting', 'author':'Writer', 'language':'English', 'category':'work'}
    with TestClient(create_app()) as client:
        first = client.post('/api/books/to-read', json=data).json()
        second = client.post('/api/books/to-read', json={**data, 'title':'Second waiting'}).json()
        assert [item['id'] for item in client.get('/api/books/to-read').json()] == [second['id'], first['id']]
        result = client.put('/api/books/to-read/' + first['id'], json={**data, 'category':'education'}).json()
        assert result['createdAt'] == first['createdAt'] and result['updatedAt'] >= first['updatedAt']
        assert [item['id'] for item in client.get('/api/books/to-read').json()] == [first['id'], second['id']]
    with TestClient(create_app()) as client:
        assert [item['id'] for item in client.get('/api/books/to-read').json()] == [first['id'], second['id']]


def test_legacy_to_read_schema_migrates_without_losing_entries(tmp_path):
    from sqlite3 import connect
    db = connect(tmp_path / 'books.db')
    db.execute('CREATE TABLE to_read (id TEXT PRIMARY KEY, title TEXT, author TEXT, isbn TEXT, language TEXT, category TEXT, created_at TEXT)')
    db.execute("INSERT INTO to_read VALUES ('old', 'Old', 'Writer', '', 'English', 'work', '2020-01-01T00:00:00+00:00')")
    db.commit(); db.close()
    with TestClient(create_app()) as client:
        item = client.get('/api/books/to-read').json()[0]
        assert item['title'] == 'Old' and item['updatedAt'] == item['createdAt']
