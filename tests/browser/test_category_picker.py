import re
import pytest
from playwright.sync_api import expect


@pytest.mark.parametrize('path', ['/quiz', '/typed', '/writing', '/prepositions', '/articles', '/review'])
def test_category_picker_defaults_to_all_without_file_choices(page, server, path):
    page.goto(server[0] + path)
    group = page.get_by_role('group', name='Vocabulary category')
    expect(group.get_by_role('button', name=re.compile('^All'))).to_have_attribute('aria-pressed', 'true')
    for name in ('General', 'Legal', 'Financial'):
        button = group.get_by_role('button', name=re.compile('^' + name))
        expect(button).to_be_visible()
        button.click()
        expect(button).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_role('group', name=re.compile('^Files in'))).to_have_count(0)
    expect(page.get_by_role('button', name=re.compile('^Last file'))).to_have_count(0)


def test_legacy_file_selection_becomes_category(page, server):
    page.goto(server[0] + '/')
    page.evaluate("localStorage.setItem('languages.settings.typed', JSON.stringify({level:'C1', count:8, files:'legal:3'}))")
    page.goto(server[0] + '/typed')
    expect(page.get_by_role('group', name='Vocabulary category').get_by_role('button', name=re.compile('^Legal'))).to_have_attribute('aria-pressed', 'true')
