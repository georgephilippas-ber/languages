from playwright.sync_api import expect


def test_read_modes_and_summary_length(page, server):
    requests = []
    def read(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'topic': 'physics', 'title': 'Article', 'publication': 'Test', 'url': '',
                            'publishedAt': '2026-10-29', 'retrievedAt': '2026-10-30',
                            'summary': 'A useful passage.', 'words': ['useful']})
    page.route('**/api/read', read)
    page.goto(server[0] + '/')
    page.locator('header').get_by_role('button', name='Read', exact=True).click()
    page.get_by_role('menuitem', name='Summarize a webpage and read').click()
    expect(page.get_by_label('Summary length')).to_have_value('100')
    page.get_by_label('Summary length').select_option('150')
    page.get_by_label('Webpage URL').fill('https://example.com/article')
    page.get_by_role('button', name='Summarize webpage').click()
    expect(page.get_by_text('A useful passage.')).to_be_visible()
    assert requests[-1]['mode'] == 'url' and requests[-1]['summaryWords'] == 150
    page.locator('header').get_by_role('button', name='Read', exact=True).click()
    page.get_by_role('menuitem', name='Read pasted article text').click()
    page.get_by_label('Article text').fill('A useful passage.')
    expect(page.get_by_label('Summary length')).to_have_count(0)
    page.get_by_role('button', name='Analyze article').click()
    assert requests[-1]['mode'] == 'text' and requests[-1]['source'] == 'A useful passage.'
