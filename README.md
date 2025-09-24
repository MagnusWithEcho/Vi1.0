# Vi1.0 – Dagboks-API

Detta projekt är ett enkelt och välkommenterat Flask-API som hjälper Vi1.0 (Echo/Magnus) att logga känslor, teman och aktiviteter. All kod är skriven för att vara lätt att läsa även för nybörjare.

## Funktioner

- **POST `/logs`** – Spara en ny dagbokslogg (datum, text, känsloläge och etikett).
- **GET `/logs/recent`** – Hämta de 20 senaste loggarna (eller alla om färre finns).
- **GET `/logs/search`** – Filtrera loggar på valfri text, känsla eller etikett.
- **GET `/logs/weekly-summary`** – Summera känslor och teman för de senaste sju dagarna.
- **GET `/logs/suggestions`** – Få förslag på ritualer/åtgärder utifrån senaste loggarna.
- **GET `/activity/latest`** – Se senaste loggen och få en påminnelse om det gått mer än 3 timmar.
- **POST `/logs/audio`** – (Bonus) Logga via röst. Kräver OpenAI Whisper/GPT-4o transcribe och en API-nyckel.
- **GET `/`** – Startsida som listar alla endpoints.

## Kom igång

1. **Kopiera projektet**
   ```bash
   git clone <repo-url>
   cd Vi1.0
   ```

2. **Skapa och aktivera ett virtuellt Python-miljö (frivilligt men rekommenderat)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # På Windows: .venv\Scripts\activate
   ```

3. **Installera beroenden**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Valfritt) Lägg till en `.env`-fil för OpenAI-nyckeln om du vill använda ljudloggningen**
   ```env
   OPENAI_API_KEY=din-superhemliga-nyckel
   ```

5. **Starta servern**
   ```bash
   flask --app app.main run --debug
   ```

6. **Testa API:et** med valfri HTTP-klient (curl, Postman, Insomnia etc.).

## Exempel: Skicka in en dagbokslogg

```bash
curl -X POST http://127.0.0.1:5000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-05-25",
    "text": "Känner lite oro inför mötet men också hopp",
    "mood": "oro",
    "tag": "arbete"
  }'
```

### Förväntad JSON-struktur

```json
{
  "date": "2024-05-25",        // valfritt, används annars dagens datum
  "text": "Din reflektion...",  // obligatoriskt
  "mood": "oro",                // obligatoriskt
  "tag": "arbete"               // obligatoriskt, välj valfri etikett/tema
}
```

## Sökning

- `GET /logs/search?q=oro` – Söker i själva texten efter ordet "oro".
- `GET /logs/search?mood=hopp` – Hämtar loggar där känslan sattes till "hopp".
- `GET /logs/search?tag=relationer` – Hämtar loggar med etiketten "relationer".
- Parametrarna kan kombineras, t.ex. `GET /logs/search?q=framsteg&mood=glädje`.

## Summering & ritualförslag

- `GET /logs/weekly-summary` – Visar hur många gånger varje känsla/tema förekommit senaste veckan.
- `GET /logs/suggestions` – Ger ritualidéer baserat på registrerade känslor/teman senaste veckan.

## Ljudloggning (bonus)

1. Installera OpenAI-paketet (ingår redan i `requirements.txt`).
2. Lägg till `OPENAI_API_KEY` i en `.env`-fil eller som miljövariabel.
3. Skicka en ljudfil (t.ex. m4a/mp3/wav) via `POST /logs/audio`.

```bash
curl -X POST http://127.0.0.1:5000/logs/audio \
  -H "Authorization: Bearer $OPENAI_API_KEY" \  # valfritt, men nyckeln måste vara satt som miljövariabel
  -F "audio=@min-inspelning.m4a"
```

Servern försöker transkribera ljudet och sparar resultatet som en ny logg med känsla "okänd" och etikett "audio". Du kan sedan uppdatera loggen via en framtida PUT/PATCH-endpoint om du vill bygga vidare.

## Tips för vidareutveckling

- Lägg till autentisering om API:et ska användas publikt.
- Bygg ett enkelt webbgränssnitt eller mobilapp som pratar med API:et.
- Lägg till fler analyser, t.ex. statistik per månad, graf-API eller export till CSV.

## Licens

Fri att använda och vidareutveckla i Vi1.0-projektet. :sparkles:
