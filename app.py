from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI
import os
import logging
import sys
from flask_talisman import Talisman
from dotenv import load_dotenv
import json
import re
import time
from functools import wraps

# Load environment variables
load_dotenv()

# Configure Flask app with production settings
app = Flask(__name__)
app.config['ENV'] = 'production'
app.config['DEBUG'] = False



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Add security headers
Talisman(app, 
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"],
    },
    force_https=False  # Set to True in production with SSL
)

# Configure rate limiting with memory storage instead of Redis
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2 per minute", "30 per hour"],
    storage_uri="memory://"
)

# Configure OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(
    api_key=api_key,
    timeout=30.0,  # 30 seconds timeout
    max_retries=2,
    base_url="https://api.openai.com/v1"
)

# Lijst met niet-toegestane woorden en thema's
BLOCKED_TERMS = [
    'nsfw', 'xxx', 'seks', 'naakt', 'erotisch', 'erotiek', 'pornografie',
    'expliciet', 'adult', '18+', 'mature', 'seksueel'
]

def contains_blocked_content(text):
    """Check if text contains any blocked terms"""
    text = text.lower()
    return any(term in text for term in BLOCKED_TERMS)

def retry_on_rate_limit(max_retries=3, initial_wait=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if 'rate limit' in str(e).lower() and retries < max_retries - 1:
                        wait_time = initial_wait * (2 ** retries)  # Exponential backoff
                        time.sleep(wait_time)
                        retries += 1
                        continue
                    if 'rate limit' in str(e).lower():
                        return jsonify({
                            "error": "Het systeem is momenteel erg druk. Probeer het over enkele minuten opnieuw.",
                            "success": False,
                            "rate_limit": True
                        }), 429
                    return jsonify({
                        "error": "Er is een fout opgetreden. Probeer het opnieuw.",
                        "success": False
                    }), 500
            return jsonify({
                "error": "Maximum aantal pogingen bereikt. Probeer het later opnieuw.",
                "success": False
            }), 429
        return wrapper
    return decorator

def error_response(message, status_code):
    """Standardized error response"""
    response = jsonify({
        'error': message,
        'status_code': status_code
    })
    response.status_code = status_code
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate-poem', methods=['POST'])
@limiter.limit("2 per minute")
@retry_on_rate_limit()
def generate_poem():
    try:
        data = request.json
        theme = data.get('theme', '').strip()
        style = data.get('style', '').strip()
        mood = data.get('mood', '').strip()
        season = data.get('season', '').strip()
        length = data.get('length', 'medium').strip()
        recipient = data.get('recipient', '').strip()
        excluded_words = data.get('excluded_words', '').strip()

        # Verwerk uitgesloten woorden
        excluded_words_list = [word.strip().lower() for word in excluded_words.split(',') if word.strip()] if excluded_words else []

        # Controleer op ongepaste inhoud
        for field in [theme, style, mood, recipient] + excluded_words_list:
            if contains_blocked_content(field):
                return jsonify({
                    "error": "Sorry, dit type inhoud is niet toegestaan.",
                    "success": False
                }), 400

        # Construct the prompt with safety instructions
        system_prompt = """Je bent een ervaren dichter die prachtige Nederlandse gedichten schrijft.
        Je schrijft alleen familie-vriendelijke, gepaste gedichten.
        Vermijd onder alle omstandigheden ongepaste, seksuele of expliciete inhoud.
        Focus op positieve, opbouwende en inspirerende thema's.

        Volg deze regels voor specifieke stijlen:
        - Voor 'haiku': Schrijf precies 3 regels met 5-7-5 lettergrepen, vaak over natuur of seizoenen
        - Voor 'limerick': Schrijf 5 regels met rijmschema aabba, humoristisch maar gepast
        - Voor 'sonnet': Schrijf 14 regels met rijmschema abab cdcd efef gg
        - Voor 'acrostichon': Zorg dat de eerste letters van elke regel het opgegeven thema of de naam van de ontvanger vormen
        - Voor 'kinderlijk': Gebruik eenvoudige woorden en korte zinnen, maak het speels en begrijpelijk voor kinderen
        - Voor 'rijmend': Zorg voor een duidelijk rijmschema door het hele gedicht
        """

        # Construct the user prompt
        prompt = f"Schrijf een gepast, familie-vriendelijk {style} gedicht"
        if recipient:
            prompt += f" voor {recipient}"
        if theme:
            prompt += f" over {theme}"
        if mood:
            prompt += f" met een {mood} stemming"
        if season:
            prompt += f" passend bij het seizoen {season}"
        if length:
            prompt += f". Het gedicht moet {length} lang zijn"
        
        if excluded_words_list:
            prompt += f". Vermijd de volgende woorden in het gedicht: {', '.join(excluded_words_list)}"
        
        prompt += ". Zorg ervoor dat de inhoud volledig gepast is voor alle leeftijden."

        # Call OpenAI API with new client
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Gebruik een ander model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        poem = response.choices[0].message.content.strip()
        
        # Extra veiligheidscheck op gegenereerde output
        if contains_blocked_content(poem):
            return jsonify({
                "error": "Er is een fout opgetreden bij het genereren van het gedicht. Probeer het opnieuw.",
                "success": False
            }), 400

        return jsonify({"poem": poem, "success": True})

    except Exception as e:
        logging.error(f"Error generating poem: {str(e)}")
        return jsonify({
            "error": "Er is een fout opgetreden. Probeer het over enkele minuten opnieuw.",
            "success": False
        }), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    logging.warning(f"Rate limit exceeded for IP: {get_remote_address()}")
    return error_response("Te veel verzoeken. Probeer het later opnieuw.", 429)

@app.errorhandler(500)
def internal_server_error(e):
    logging.error(f"Server error: {str(e)}")
    return error_response("Er is een serverfout opgetreden. Probeer het later opnieuw.", 500)

@app.errorhandler(404)
def not_found_error(e):
    logging.info(f"Page not found: {request.url}")
    return error_response("Pagina niet gevonden.", 404)

# Remove development server code
# Zorg dat de port correct wordt opgepikt
port = os.getenv('PORT', '8000')
if not port:
    port = '8000'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(port))

