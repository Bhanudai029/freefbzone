import asyncio
import os
import sys
from urllib.parse import urlparse, unquote
from playwright.async_api import async_playwright
import argparse

# Fix Windows console encoding issues
if sys.platform == "win32":
    try:
        import codecs
        # Only set encoding if not already set
        if hasattr(sys.stdout, 'detach') and not hasattr(sys.stdout, '_wrapped'):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stdout._wrapped = True
        if hasattr(sys.stderr, 'detach') and not hasattr(sys.stderr, '_wrapped'):
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
            sys.stderr._wrapped = True
    except:
        pass  # If encoding setup fails, continue with default encoding

async def download_facebook_video_snapsave(url):
    """
    Download a Facebook video using snapsave.app
    """
    print(f"[PHONE] Processing with SnapSave: {url[:50]}...")

    async with async_playwright() as p:
        browser = None
        page = None
        context = None
        try:
            # Launch browser using system Chrome instead of Playwright's Chromium
            browser = await p.chromium.launch(
                headless=True,
                executable_path='/usr/bin/google-chrome'
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Open SnapSave
            await page.goto("https://snapsave.app/", timeout=90000)
            print("[WEB] Connected to SnapSave")

            # Fill the Facebook video URL
            input_selector = "#url"
            await page.wait_for_selector(input_selector, timeout=60000)
            await page.fill(input_selector, url)
            print("[SUBMIT] URL submitted")
            
            # Press 'Enter' key to submit the form
            await page.keyboard.press('Enter')
            
            # Instead of a fixed sleep, wait for the download section to be fully visible and stable.
            # This makes the script more resilient to varying page load times.
            await page.wait_for_selector("#download-section", timeout=90000, state='visible')
            print("[WAIT] Processing video...")

            # Now, click the specific download button and capture the download
            download_button_selector_after_enter = "#download-section > section > div > div.download-link > div:nth-child(2) > div > table > tbody > tr:nth-child(1) > td:nth-child(3) > a"
            await page.wait_for_selector(download_button_selector_after_enter, timeout=30000, state='visible')
            
            print("[LINK] Extracting download link...")
            
            # Extract the download URL directly from the button or by expecting a download event
            let_download_url = None
            try:
                # Attempt to get the href of the download button directly
                let_download_url = await page.evaluate(f"document.querySelector('{download_button_selector_after_enter}').href")
            except Exception as e:
                pass  # Silent fail, will try alternative method
            
            # If direct URL from button fails, or if it's a blob/redirect, try to expect download
            if not let_download_url or not (let_download_url.startswith('http') or let_download_url.startswith('https')):
                async with page.expect_download() as download_info:
                    # Click the download button again to trigger the download event
                    await page.click(download_button_selector_after_enter, timeout=5000) 
                
                download = await download_info.value
                let_download_url = download.url

            if not let_download_url:
                raise Exception("Failed to obtain a valid download URL.")

            print("[SUCCESS] Download link obtained successfully")
            
            return {
                "success": True,
                "download_url": let_download_url # Returning the extracted download URL
            }
            
        except Exception as e:
            print(f"[ERROR] SnapSave error: {str(e)}")
            return {"success": False, "error": str(e)}
        
        finally:
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
            except Exception as cleanup_error:
                print(f"[CLEANUP] Warning: Error during cleanup: {cleanup_error}")

async def main():
    parser = argparse.ArgumentParser(description='Extract download link from snapsave.app')
    parser.add_argument('url', help='URL of the Facebook video')
    args = parser.parse_args()

    result = await download_facebook_video_snapsave(args.url)

    if result["success"]:
        print(f"DOWNLOAD_LINK:{result['download_url']}") # Print the URL in a parsable format
    else:
        print(f"Error:{result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
