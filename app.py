from flask import Flask, render_template, request, jsonify
import requests
import threading
from bs4 import BeautifulSoup

app = Flask(__name__)
results = []
stop_extraction = False
results_set = set()  # To keep track of unique post links

def extract_articles(soup):
    articles = []
    container = soup.find(id="m_group_stories_container")
    
    if container:
        for article in container.find_all('article', {'data-ft': lambda x: x and '"tn":"-R"' in x}):
            caption = article.find('div', class_='ds')
            caption_text = caption.get_text(strip=True) if caption else "No Caption"
            
            comments_tag = article.find('a', string=lambda text: text and "Comments" in text)
            comments_text = comments_tag.get_text(strip=True) if comments_tag else "0 comments"
            
            reactions_tag = article.find('a', {'aria-label': True})
            reactions_text = reactions_tag['aria-label'] if reactions_tag else "0 reactions"

            publish_date_tag = article.find('abbr')
            publish_date = publish_date_tag.get_text(strip=True) if publish_date_tag else "Unknown date"
            
            strong_tag = article.find('strong')
            link_tag = strong_tag.find('a') if strong_tag else None
            profile_name = link_tag.get_text(strip=True) if link_tag else "No name available"
            
            post_link_tag = article.find('a', string="Full Story")
            post_link = post_link_tag['href'] if post_link_tag else "No post link available"
            modified_url = post_link.replace("mbasic", "www").replace('permalink','posts').split("?")[0]

            if modified_url not in results_set:  # Check for uniqueness
                results_set.add(modified_url)
                articles.append({
                    'caption': caption_text,
                    'comments': comments_text,
                    'reactions': reactions_text,
                    'publish_date': publish_date,
                    'profile_name': profile_name,
                    'post_link': modified_url
                })
    else:
        print("Container with ID 'm_group_stories_container' not found.")

    return articles

def get_group_posts(cookies, group_id):
    global results, stop_extraction
    headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    # 'cookie': 'sb=CH3pZiUjYZKwRMrouMI8DTrr; datr=CH3pZiddhpPJjJU47hltJwAl; c_user=100010218577436; ps_l=1; ps_n=1; m_page_voice=100010218577436; dpr=1.25; wd=1536x695; xs=31%3ASI7fq8Wa2nYnnA%3A2%3A1726580299%3A-1%3A6559%3A%3AAcUPQIiU8kTzPHFSu_94Djkw9pFrjR-gmHTzF4v0g1M; fr=1XfyqjUoZy98uUGhu.AWWRrg34FKNi_oqKvGSULpstrL0.BnJf2v..AAA.0.0.BnJf25.AWVyhjHABFo; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1730543036306%2C%22v%22%3A1%7D',
    'dpr': '1.25',
    'priority': 'u=0, i',
    'referer': 'https://mbasic.facebook.com/groups/?category=membership&ref_component=mbasic_home_header&ref_page=%2Fwap%2Fhome.php&refid=8',
    'sec-ch-prefers-color-scheme': 'light',
    'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    'sec-ch-ua-full-version-list': '"Chromium";v="130.0.6723.92", "Google Chrome";v="130.0.6723.92", "Not?A_Brand";v="99.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"15.0.0"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'viewport-width': '1105',
}

    response = requests.get(f'https://mbasic.facebook.com/groups/{group_id}', cookies=cookies, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    results.extend(extract_articles(soup))
    
    while not stop_extraction:
        try:
            see_more_link_tag = soup.find('a', href=lambda x: x and 'bacr=' in x)
            if see_more_link_tag:
                see_more_link = see_more_link_tag['href']
                response = requests.get(f'https://mbasic.facebook.com{see_more_link}', cookies=cookies, headers=headers)
                soup = BeautifulSoup(response.text, "html.parser")
                results.extend(extract_articles(soup))
            else:
                break
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    global results, stop_extraction, results_set
    stop_extraction = False  # Reset the stop flag
    results.clear()  # Clear results for new extraction
    results_set.clear()  # Clear the unique set

    cookies = request.form.get('cookies')
    group_link = request.form.get('group_link')

    try:
        cookies_dict = dict(item.split('=') for item in cookies.split(';') if '=' in item)
    except ValueError:
        return jsonify({'status': 'error', 'message': "Invalid cookies format. Please ensure the format is key=value; ..."})
    
    extraction_thread = threading.Thread(target=get_group_posts, args=(cookies_dict, group_link))
    extraction_thread.start()

    return jsonify({'status': 'started'})

@app.route('/stop', methods=['POST'])
def stop():
    global stop_extraction
    stop_extraction = True
    return jsonify({'status': 'stopped'})

@app.route('/results')
def get_results():
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
