from playwright.sync_api import sync_playwright
import json

def get_all_page_styles(url):
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        # Execute JS to crawl the DOM and get all computed styles
        page_data = page.evaluate("""
            () => {
                const allElements = document.querySelectorAll('*');
                const results = [];
                
                allElements.forEach((el, index) => {
                    const style = window.getComputedStyle(el);
                    const styleObject = {};
                    
                    // Grab all computed properties
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

print("Data saved to page_styles.json")