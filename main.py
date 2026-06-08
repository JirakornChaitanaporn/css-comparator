import requests as req
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

gemini_key = os.getenv("GEMINI_KEY")

if not gemini_key:
    raise ValueError("GEMINI_KEY is missing. Set it in your environment or .env file before running.")

client = genai.Client(api_key=gemini_key)

# html_css = input("Please enter the inspected html css\n")
# print("finish input")
# file_key = "kj3FtMYX9GXB9OiiXISnDf"


def load_css_as_string(file_path):
    print("loading css")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            css_content = file.read()
            return css_content
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None

css = load_css_as_string("newPR.css")

from playwright.sync_api import sync_playwright
import json

def get_all_page_styles(url):
    # Retrieve credentials safely from your .env file
    web_user = os.getenv("WEB_USER", "your_default_username")
    web_pass = os.getenv("WEB_PASS", "your_default_password")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        state_file = "state.json"
        if os.path.exists(state_file):
            print(f"Using existing storage state: {state_file}")
            context = browser.new_context(storage_state=state_file)
            page = context.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
        else:
            context = browser.new_context()
            page = context.new_page()
            print(f"Navigating to protected route: {url}")
            page.goto(url)

            # The browser may be redirected to the login page — attempt automated login if creds exist
            print("Checking for login form...")
            try:
                page.wait_for_selector("input[name='username']", timeout=60000)
                page.fill("input[name='username']", web_user or "")
                page.wait_for_selector("input[name='password']", timeout=30000)
                page.fill("input[name='password']", web_pass or "")
                page.click("button[type='submit']")
                page.wait_for_load_state("networkidle")
                if page.url != url:
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                # Persist storage state for future headless runs
                context.storage_state(path=state_file)
                print(f"Saved storage state to {state_file}")
            except Exception:
                print("Login form not detected or login failed; continuing without saving state.")

        print("Successfully authenticated or reached target. Executing DOM style crawling...")

        # 3. Execute JS to crawl the DOM
        page_data = page.evaluate("""
            () => {
                const allElements = document.querySelectorAll('*');
                const results = [];
                
                allElements.forEach((el, index) => {
                    const style = window.getComputedStyle(el);
                    const styleObject = {};
                    
                    for (let i = 0; i < style.length; i++) {
                        const prop = style[i];
                        styleObject[prop] = style.getPropertyValue(prop);
                    }
                    
                    results.push({
                        tag: el.tagName,
                        classes: Array.from(el.classList),
                        styles: styleObject
                    });
                });
                return results;
            }
        """)
        
        context.close()
        browser.close()
        return page_data
    
# Filtering utility to keep Gemini prompts clean
def filter_relevant_styles(element_data):
    relevant = {'width', 'height', 'background-color', 'font-size', 'color', 'padding', 'margin', 'font-weight'}
    for item in element_data:
        item['styles'] = {k: v for k, v in item['styles'].items() if k in relevant}
    return element_data

# --- Execution ---
target_url = "https://ecms-author.be8-customdev.com/editor.html/content/kasikornbank/th/th/kwealth/news-pr-list.html"
raw_data = get_all_page_styles(target_url)
clean_data = filter_relevant_styles(raw_data)

# Save to a file to avoid terminal clutter
with open("page_styles.json", "w") as f:
    json.dump(clean_data, f, indent=2)
    
# 1. Load the cleaned JSON data we just generated
with open("page_styles.json", "r") as f:
    live_styles = json.load(f)

# 2. Prepare the prompt for Gemini
# We convert the JSON to a string so the model can parse it
comparison_prompt = f"""
You are an expert Frontend Developer. Compare the intended CSS styling with the 
actual live computed styles from the website.

### Intended CSS (from newPR.css):
{css}

### Live Computed Styles (from web):
{json.dumps(clean_data[:20], indent=2)} 

### Task:
1. Compare the 'Intended CSS' with the 'Live Computed Styles'.
2. Explain CSS class by class in the 'Live Computed Styles' what and how to improve styling include all element of css inside class(tell them how to make it match the intended design)(makesure u do all)
3. make a nice table to report it each table say html_tag, class, element, attribute, how to set those number, what else to improve, what is the issue
4. keep in mind that the number of element would not match cuz one is frontend demo and one is figma design
5. If the values match, ignore them. Only report the mismatches.
6. This is reponsive design not a fix design
"""

# 3. Call Gemini
try:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=comparison_prompt
    )
    print("\n--- DESIGN AUDIT REPORT ---")
    # print(response.text)
except APIError as e:
    print(f"API Error: {e}")
    
def save_report_to_file(report_text, filename="DesignAuditReport.md"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Design Audit Report\n\n")
            f.write(report_text)
        print(f"\nReport successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")

# Call this after receiving the response from Gemini
if response.text:
    save_report_to_file(response.text)