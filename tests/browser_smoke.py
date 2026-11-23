"""Exercise retained data, custom coordinates, safe search and mobile map layout."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT/'dist',Path(temporary)/'example-tool')
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temporary));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
                # CI never downloads third-party map tiles. Test data/markers remain real.
                page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/example-tool/')
                expect(page.locator('#save')).to_be_enabled(timeout=30000)
                expect(page.locator('#source-summary')).to_contain_text('locations')
                assert int(page.locator('#near-count').inner_text().replace(',',''))>0
                expect(page.locator('#map canvas')).to_be_visible()
                page.get_by_role('button',name='Halifax',exact=True).click()
                expect(page.locator('#lat')).to_have_value('44.6488')
                expect(page.locator('#status')).to_contain_text('44.6488')
                page.locator('#query').fill('<img src=x onerror=alert(1)>')
                expect(page.locator('#empty')).to_be_visible();assert page.locator('#results img').count()==0
                page.get_by_role('button',name='Reset filters',exact=True).click()
                page.locator('#lat').fill('48.4284');page.locator('#lon').fill('-123.3656')
                page.get_by_role('button',name='Find nearby locations',exact=True).click()
                expect(page.locator('#status')).to_contain_text('48.4284')
                assert int(page.locator('#near-count').inner_text().replace(',',''))>0
                with page.expect_download() as download:page.locator('#save').click()
                saved=Path(temporary)/'capture.json';download.value.save_as(saved)
                page.locator('#import').set_input_files(str(saved));expect(page.locator('#capture')).to_have_value('import-1')
                expect(page.locator('#change-summary')).to_contain_text('0 added')
                page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
                assert not errors,errors;browser.close()
            print('Browser checks passed: real capture, custom place, search, import/export and mobile map.')
        finally:server.shutdown()
if __name__=='__main__':main()
