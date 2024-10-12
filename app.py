from flask import Flask, render_template, request, jsonify
import requests
import re
from datetime import datetime, timezone
import threading
import codecs
import sqlite3
app = Flask(__name__)
results = []
stop_extraction = False

def get_group_posts(cookies, group_id):
    global results, stop_extraction
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'dpr': '1.25',
        'priority': 'u=0, i',
        'sec-ch-prefers-color-scheme': 'light',
        'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="129.0.6668.100", "Not=A?Brand";v="8.0.0.0", "Chromium";v="129.0.6668.100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'viewport-width': '759',
    }

    response = requests.get(f'https://www.facebook.com/groups/{group_id}', cookies=cookies, headers=headers)
    # Extracting necessary values
    try:
        end_cursor = re.search(r'"data":{"page_info":\{"end_cursor":"(.*?)"', response.text).group(1)
        rev = re.search(r'{"rev":(.*?)}', str(response.text)).group(1)
        hsi = re.search(r'"hsi":"(.*?)",', str(response.text)).group(1)
        fb_dtsg = re.search(r'"DTSGInitialData",\[\],{"token":"(.*?)"', str(response.text)).group(1)
        jazoest = re.search(r'&jazoest=(.*?)",', str(response.text)).group(1)
        lsd = re.search(r'"LSD",\[\],{"token":"(.*?)"', str(response.text)).group(1)
        spinr = re.search(r'"__spin_r":(.*?),', str(response.text)).group(1)
        spint = re.search(r'"__spin_t":(.*?),', str(response.text)).group(1)
    except AttributeError:
        return []

    c_user_value = cookies["c_user"]
    new_headers = {
        'x-fb-friendly-name': 'GroupsCometFeedRegularStoriesPaginationQuery',
        'x-fb-lsd': lsd,
    }
    headers.update(new_headers)

    while not stop_extraction:  # Check if we need to stop
        data = {
            'av': c_user_value,
            '__aaid': '0',
            '__user': c_user_value,
            '__a': '1',
            '__req': '6r',
            '__hs': '20008.HYP:comet_pkg.2.1..2.1',
            'dpr': '1',
            '__ccg': 'GOOD',
            '__rev': rev,
            '__hsi': hsi,
            '__comet_req': '15',
            'fb_dtsg': fb_dtsg,
            'jazoest': jazoest,
            'lsd': lsd,
            '__spin_r': spinr,
            '__spin_b': 'trunk',
            '__spin_t': spint,
            'qpl_active_flow_ids': '431626709',
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'GroupsCometFeedRegularStoriesPaginationQuery',
            'variables': '{"count":3,"cursor":"'+end_cursor+'","feedLocation":"GROUP","feedType":"DISCUSSION","feedbackSource":0,"focusCommentID":null,"privacySelectorRenderLocation":"COMET_STREAM","renderLocation":"group","scale":1,"sortingSetting":"TOP_POSTS","stream_initial_count":1,"useDefaultActor":false,"useGroupFeedWithEntQL_EXPERIMENTAL":false,"id":"'+group_id+'","__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":false,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__IncludeCommentWithAttachmentrelayprovider":true,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__EventCometCardImage_prefetchEventImagerelayprovider":false}',
            'server_timestamps': 'true',
            'doc_id': '8531436683610816',
        }
        response = requests.post('https://www.facebook.com/api/graphql/', cookies=cookies, headers=headers, data=data)

        # Extracting post data
        usernames = re.findall(r'","owning_profile":\{"__typename":"User","name":"(.*?)"', response.text)
        comment_counts = re.findall(r'true,"comment_rendering_instance":\{"comments":\{"total_count":(\d+)', response.text)
        reaction_counts = re.findall(r'\[\]\},"reaction_count":\{"count":(\d+)', response.text)
        profile_urls = [url.replace('\\/', '/') for url in re.findall(r'"profile_url":"(https:\\/\\/www\.facebook\.com\\/[^"]+)"', response.text)]
        post_urls = re.findall(r'{"__typename":"Story","url":"(https:\\/\\/www\.facebook\.com\\/groups\\/[^"]+)"', response.text)
        creation_times = re.findall(r'"creation_time":(\d+)', response.text)
        messages = re.findall(r'"message":\{"text":"(.*?)"', response.text)

        for i in range(len(usernames)):
            post_data = {
                'username': usernames[i],
                'comment_count': comment_counts[i],
                'reaction_count': reaction_counts[i],
                'profile_url': profile_urls[i],
                'post_url': post_urls[i].replace('\\', ''),
                'message': (codecs.decode(messages[i].encode('utf-8'), 'raw_unicode_escape') 
                            if i < len(messages) else ''),  # Check if message exists
                'creation_time': datetime.fromtimestamp(int(creation_times[i]), timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            }
            results.append(post_data)

        try:
            end_cursor = re.search(r',"data":{"page_info":\{"end_cursor":"(.*?)"', response.text).group(1)
        except AttributeError:
            break  # Exit the loop if there's no more data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    global stop_extraction
    stop_extraction = False  # Reset the stop flag

    cookies = request.form.get('cookies')
    group_link = request.form.get('group_link')

    # Validate cookies format and split
    try:
        cookies_dict = dict(item.split('=') for item in cookies.split(';') if '=' in item)
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': "Invalid cookies format. Please ensure the format is key=value; ..."
        })

    # Start the extraction in a new thread
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