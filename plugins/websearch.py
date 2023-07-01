import random
import re
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import urllib


# Specify the path to the ChromeDriver
chrome_driver_path = "C:\chromedriver_win32\chromedriver.exe"

def google_search(query, api_key, cx):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    results = response.json()
    return results

def websearch(input_string, api_key, cx):
    pattern = r'\[(?:SEARCH|SEARCHING) FOR (.+)\]'
    match = re.match(pattern, input_string)
    if match:
        print("Searching for: " + match.group(1) + "\n")
        search_string = match.group(1)
        top_links = []
        search_results = []

        results = google_search(search_string, api_key, cx)
        x = 0
        for item in results.get('items', [])[:10]:
            search_result = f"Search result {x+1}: {item.get('link', 'No link available')} {item.get('title', 'No title available')} - {item.get('snippet', 'No snippet available')}\n\n"
            #print(search_result)
            top_links.append(item.get('link', 'No link available'))
            search_results.append(search_result)
            x += 1


        # Check if there are any results
        if len(top_links) == 0:
            # Check if the search_string is a URL
            url = urllib.parse.urlparse(search_string)
            if url.scheme and url.netloc:
                webvisit("[VISIT WEBSITE " + search_string + "]")
            return "No search results found."

        # print(f"Top links: {top_links}\n")
        number = random.randint(0, len(top_links) - 1)
        this_link = top_links[number]

        # Set up the Chrome options for headless browsing
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--enable-javascript")
        options.add_argument("--incognito")
        options.add_argument("--nogpu")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,1280")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-web-security")

        try:
            # Create a new instance of the Chrome WebDriver
            driver = webdriver.Chrome(executable_path=chrome_driver_path, options=options)
        except Exception as e:
            print(e)

        driver.get(this_link)

        # List of possible CSS selectors for cookie popups and accept buttons
        cookie_popup_selectors = [
            ".cookie-popup",
            ".cookie-notice",
            "#cookie-banner",
            "#cookie-law-info-bar"
        ]

        accept_button_selectors = [
            ".accept-button",
            ".cookie-accept",
            ".consent-give",
            ".cookie-agree",
            "button[data-cookiefirst-agree]"
        ]

        # Attempt to handle the cookie popup
        handled_popup = False
        for popup_selector in cookie_popup_selectors:
            if handled_popup:
                break

            try:
                cookie_popup = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, popup_selector))
                )

                for button_selector in accept_button_selectors:
                    try:
                        accept_button = cookie_popup.find_element(By.CSS_SELECTOR, button_selector)
                        accept_button.click()
                        handled_popup = True
                        break
                    except Exception as e:
                        continue
            except Exception as e:
                continue

        # Get the page source
        response = driver.page_source

        # Close the WebDriver instance
        driver.quit()

        html_data = response

        soup = BeautifulSoup(html_data, 'html.parser')
        for script in soup(['script', 'style', 'header', 'footer']):
            script.decompose()

        result = soup.get_text(strip=True)

        # Ensure the result doesn't have more than x characters
        if len(result) > 9500:
            result = result[:9500]

        beautified_result = "search result:" + result + "\n"

        # Combine the summary of top 5 results and the beautified result of the chosen link
        output = f" {''.join(search_results)} \ncontent of ({this_link}):\n {beautified_result}"
        return output
    else:
        print("Invalid input string format.\n")
        return "Invalid input string format."

    
def webvisit(input_string):
    print(f"Webvisit: {input_string}\n")
    pattern = r'\[(?:VISIT|VISITING) WEBSITE (.+)\]'

    match = re.match(pattern, input_string)
    if match:
        print("Visiting: " + match.group(1) + "\n")
        this_link = match.group(1)
        # Set up the Chrome options for headless browsing
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--enable-javascript")
        options.add_argument("--incognito")
        options.add_argument("--nogpu")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,1280")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-web-security")

        # Create a new instance of the Chrome WebDriver
        driver = webdriver.Chrome(executable_path=chrome_driver_path, options=options)

        driver.get(this_link)

        # List of possible CSS selectors for cookie popups and accept buttons
        cookie_popup_selectors = [
            ".cookie-popup",
            ".cookie-notice",
            "#cookie-banner",
            "#cookie-law-info-bar"
        ]

        accept_button_selectors = [
            ".accept-button",
            ".cookie-accept",
            ".consent-give",
            ".cookie-agree",
            "button[data-cookiefirst-agree]"
        ]

        # Attempt to handle the cookie popup
        handled_popup = False
        for popup_selector in cookie_popup_selectors:
            if handled_popup:
                break

            try:
                cookie_popup = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, popup_selector))
                )

                for button_selector in accept_button_selectors:
                    try:
                        accept_button = cookie_popup.find_element(By.CSS_SELECTOR, button_selector)
                        accept_button.click()
                        handled_popup = True
                        break
                    except Exception as e:
                        continue
            except Exception as e:
                continue

        # Get the page source
        response = driver.page_source

        # Close the WebDriver instance
        driver.quit()
        html_data = response

        soup = BeautifulSoup(html_data, 'html.parser')
        for script in soup(['script', 'style', 'header', 'footer']):
            script.decompose()

        result = soup.get_text(strip=True)

        # Ensure the result doesn't have more than x characters
        if len(result) > 10000:
            result = result[:10000]

        print("website result:" + result + "\n")
        return result
    else:
        print("Invalid input string format.\n")
        return "Invalid input string format."
