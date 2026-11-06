import re
from pathlib import Path

from playwright.sync_api import expect
from src.domain import DATA_ROOT


def test_category_is_english_only_and_safe_when_switching_languages(page, server):
    seed = Path(__file__).resolve().parents[2] / 'seed'
    directory = Path(DATA_ROOT) / 'vocabulary' / 'english'
    for number in (1, 2):
        (directory / f'english-phrasal-verbs-{number}.md').write_text(
            (seed / f'en-phrasal-verbs-{number}.md').read_text(encoding='utf-8'), encoding='utf-8')
    url, _ = server
    page.goto(url + '/')
    page.get_by_role('button', name='EN', exact=True).click()
    page.goto(url + '/typed')
    option = page.get_by_role('button', name=re.compile(r'^Phrasal Verbs'))
    expect(option).to_be_visible()
    expect(option).to_contain_text('50 terms')
    option.click()
    expect(option).to_have_attribute('aria-pressed', 'true')
    page.goto(url + '/review')
    review_option = page.get_by_role('button', name='Phrasal Verbs', exact=True)
    expect(review_option).to_be_visible()
    review_option.click()
    expect(review_option).to_have_attribute('aria-pressed', 'true')
    page.goto(url + '/add')
    category = page.get_by_label('Category')
    category.select_option('phrasal-verbs')
    expect(category).to_have_value('phrasal-verbs')
    expect(page.get_by_text('english-phrasal-verbs-3.md', exact=False)).to_be_visible()
    page.get_by_role('button', name='DE', exact=True).click()
    page.goto(url + '/review')
    expect(page.get_by_role('button', name='Phrasal Verbs', exact=True)).to_have_count(0)
    page.goto(url + '/add')
    expect(category).to_have_value('general')
    expect(category.locator('option[value="phrasal-verbs"]')).to_have_count(0)
    page.goto(url + '/typed')
    expect(page.get_by_role('button', name=re.compile(r'^Phrasal Verbs'))).to_have_count(0)
    page.get_by_role('button', name='FR', exact=True).click()
    page.goto(url + '/add')
    expect(category).to_have_value('general')
    expect(category.locator('option[value="phrasal-verbs"]')).to_have_count(0)
    page.get_by_role('button', name='EN', exact=True).click()
    page.goto(url + '/add')
    expect(category).to_have_value('phrasal-verbs')
