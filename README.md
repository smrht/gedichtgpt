# GedichtGPT

Een moderne web applicatie voor het genereren van Nederlandse gedichten met behulp van AI.

## Functionaliteiten

- Genereer gedichten op basis van thema
- Kies uit verschillende stijlen (modern, klassiek, romantisch, haiku, sonnet)
- Pas de stemming aan (vrolijk, melancholisch, romantisch, etc.)
- Seizoensgebonden gedichten
- Kies de gewenste lengte van het gedicht
- Mobiel-vriendelijke interface
- Rate limiting om overbelasting te voorkomen

## Installatie

1. Clone de repository
2. Maak een virtuele omgeving aan:
```bash
python -m venv venv
source venv/bin/activate  # Voor Unix/macOS
```

3. Installeer de benodigde packages:
```bash
pip install -r requirements.txt
```

4. Maak een .env bestand aan op basis van .env.example:
```bash
cp .env.example .env
```

5. Voeg je OpenAI API key toe aan het .env bestand

## Gebruik

1. Start de applicatie:
```bash
python app.py
```

2. Open je browser en ga naar `http://localhost:5000`

3. Vul de gewenste velden in en klik op "Genereer Gedicht"

## Technische Details

- Backend: Python Flask
- Frontend: HTML, TailwindCSS, JavaScript
- AI: OpenAI GPT-3.5
- Rate Limiting: Flask-Limiter
- Caching: Redis (optioneel)
