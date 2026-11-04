import httpx
from playwright.sync_api import sync_playwright, expect


def test_local_link_in_webkit_without_cookies(server):
    url, _ = server
    with httpx.Client(trust_env=False) as client:
        status = client.post(url + '/api/device/start').json()
        try:
            with sync_playwright() as playwright:
                browser = playwright.webkit.launch()
                context = browser.new_context()
                page = context.new_page()
                response = page.goto(status['localUrl'])
                assert response.status == 200
                assert response.request.redirected_from is None
                assert context.cookies() == []
                expect(page.get_by_role('button', name='Languages menu')).to_be_visible()
                assert page.request.get(status['localUrl'] + '/api/meta').status == 200
                context.close()
                browser.close()
        finally:
            client.post(url + '/api/device/revoke')
