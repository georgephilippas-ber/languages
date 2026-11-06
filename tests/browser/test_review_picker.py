import re
from playwright.sync_api import expect


def test_review_picker_loads_category_without_file_scope(page, server):
    requests = []
    def flashcards(route):
        selection = route.request.post_data_json['files']
        requests.append(selection)
        route.fulfill(json={'source': 'synthetic', 'cards': [{'isDue': False, 'isNew': True, 'state': {'dueAt': None}} for _ in range(3 if selection == 'legal' else 12)]})
    page.route('**/api/flashcards', flashcards)
    page.goto(server[0] + '/review')
    group = page.get_by_role('group', name='Vocabulary category')
    expect(group.get_by_role('button', name=re.compile('^All'))).to_have_attribute('aria-pressed', 'true')
    group.get_by_role('button', name=re.compile('^Legal')).click()
    expect(page.get_by_text('3 in the deck')).to_be_visible()
    assert requests[-1] == 'legal'
    expect(page.get_by_role('group', name=re.compile('^Files in'))).to_have_count(0)
