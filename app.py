from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import sys
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5 per minute", "100 per hour"]
)

# Configure OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Lijst met niet-toegestane woorden en thema's (voeg hier meer aan toe indien nodig)
BLOCKED_TERMS = [
    'nsfw', 'xxx', 'seks', 'naakt', 'erotisch', 'erotiek', 'pornografie',
    'expliciet', 'adult', '18+', 'mature', 'seksueel'
]

def contains_blocked_content(text):
    """Check if text contains any blocked terms"""
    text = text.lower()
    return any(term in text for term in BLOCKED_TERMS)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate-poem', methods=['POST'])
@limiter.limit("5 per minute")
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
            model="gpt-4o-mini",
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
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    # Get port from command line argument or use default 8000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    app.run(debug=True, port=port)
