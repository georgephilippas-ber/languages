import re
from playwright.sync_api import expect


def test_review_category_scopes_load_the_selected_cards(page, server):
    url, _ = server
    requests = []
    def metadata(route):
        response = route.fetch()
        body = response.json()
        english = next(lang for lang in body['languages'] if lang['code'] == 'EN')
        english['files'] = [{'number': 1, 'name': 'english-1.md', 'terms': 12}] + [
            {'number': f'phrasal-verbs:{n}', 'name': f'english-phrasal-verbs-{n}.md', 'terms': 2}
            for n in range(1, 5)]
        route.fulfill(response=response, json=body)
    def flashcards(route):
        selection = route.request.post_data_json['files']
        requests.append(selection)
        count = {'all': 20, 'phrasal-verbs': 8, 'phrasal-verbs:current': 2, 'phrasal-verbs:latest': 4, 'legal': 0}[selection]
        route.fulfill(json={'source': 'synthetic', 'cards': [
            {'isDue': False, 'isNew': True, 'state': {'dueAt': None}} for _ in range(count)]})
    page.route('**/api/meta', metadata)
    page.route('**/api/flashcards', flashcards)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(url + '/')
    page.get_by_role('button', name='EN', exact=True).click()
    page.goto(url + '/review')
    categories = page.get_by_role('group', name='Vocabulary category')
    expect(categories.get_by_role('button', name=re.compile('^All categories'))).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_text('20 in the deck')).to_be_visible()
    categories.get_by_role('button', name=re.compile('^Phrasal Verbs')).click()
    scopes = page.get_by_role('group', name='Files in Phrasal Verbs')
    expect(scopes.get_by_role('button', name=re.compile('^Last file'))).to_contain_text('2 terms')
    expect(scopes.get_by_role('button', name=re.compile('^Last two files'))).to_contain_text('4 terms')
    expect(scopes.get_by_role('button', name=re.compile('^Entire category'))).to_contain_text('8 terms')
    expect(page.get_by_text('8 in the deck')).to_be_visible()
    scopes.get_by_role('button', name=re.compile('^Last file')).click()
    expect(page.get_by_text('2 in the deck')).to_be_visible()
    assert requests[-1] == 'phrasal-verbs:current'
    scopes.get_by_role('button', name=re.compile('^Last two files')).click()
    expect(page.get_by_text('4 in the deck')).to_be_visible()
    assert requests[-1] == 'phrasal-verbs:latest'
    page.reload()
    expect(page.get_by_text('4 in the deck')).to_be_visible()
    expect(scopes.get_by_role('button', name=re.compile('^Last two files'))).to_have_attribute('aria-pressed', 'true')
    categories.get_by_role('button', name=re.compile('^Legal')).click()
    expect(page.get_by_text('0 in the deck')).to_be_visible()
    expect(page.get_by_role('button', name='Browse')).to_be_disabled()
    categories.get_by_role('button', name=re.compile('^All categories')).click()
    expect(page.get_by_text('20 in the deck')).to_be_visible()
    assert requests[-1] == 'all'
    expect(page.get_by_role('group', name=re.compile('^Files in'))).to_have_count(0)
