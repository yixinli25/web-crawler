from bs4 import BeautifulSoup
from queue import Queue
from tenacity import retry, stop_after_attempt, wait_exponential
import requests
import re
import csv

target_url = "https://www.scrapingcourse.com/ecommerce/"

url_pattern = re.compile(r"/page/\d+/")

product_data = []

max_crawl = 20

visited_urls = set()

high_priority_queue = Queue()
low_priority_queue = Queue()

high_priority_queue.put(target_url)
low_priority_queue.put(target_url)

session = requests.Session()

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=5, min=4, max=5)
)

def fetch_url(url):
    response = session.get(url)
    response.raise_for_status()
    return response

def crawler():
    
    crawl_count = 0

    while (not high_priority_queue.empty() or not low_priority_queue.empty()) and crawl_count < max_crawl:
        if not high_priority_queue.empty():
            curr_url = high_priority_queue.get()
        elif not low_priority_queue.empty():
            curr_url = low_priority_queue.get()
        else:
            break

        if curr_url in visited_urls:
            continue

        visited_urls.add(curr_url)

        response = fetch_url(curr_url)

        soup = BeautifulSoup(response.text, "html.parser")

        for link_element in soup.find_all("a", href=True):
            url = link_element["href"]

            if not url.startswith("http"):
                absolute_url = requests.compat.urljoin(target_url, url)
            else:
                absolute_url = url

            if (
                absolute_url.startswith(target_url)
                and absolute_url not in visited_urls
            ):
                if url_pattern.search(absolute_url):
                    high_priority_queue.put(absolute_url)
                else:
                    low_priority_queue.put(absolute_url)

        if url_pattern.search(curr_url):
            product_containers = soup.find_all("li", class_="product")

            for product in product_containers:
                data = {
                    "Url": product.find("a", class_="woocommerce-LoopProduct-link")["href"],
                    "Image": product.find("img", class_="product-image")["src"],
                    "Name": product.find("h2", class_="product-name").get_text(),
                    "Price": product.find("span", class_="price").get_text()
                }

                product_data.append(data)

        crawl_count += 1

crawler()

csv_file_name = "products.csv"

with open(csv_file_name, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["Url", "Image", "Name", "Price"])
    writer.writeheader()
    writer.writerows(product_data)