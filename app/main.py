"""Flask-API för Vi1.0 dagboksloggar med enkla, välkommenterade funktioner."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

from .database import current_timestamp, execute, fetch_rows, initialize_database

try:
    # OpenAI är valfritt. API-nyckel behövs om funktionen ska användas.
    from openai import OpenAI
except ImportError:  # pragma: no cover - vi ignorerar om paketet inte finns installerat
    OpenAI = None  # type: ignore


def create_app() -> Flask:
    """Skapar och returnerar en konfigurerad Flask-app."""

    load_dotenv()  # Läser in variabler från eventuell .env-fil
    initialize_database()

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False  # Behåll svenska tecken korrekt

    # Aktivera enkel loggning till konsolen så man ser vad som händer.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    @app.route("/logs", methods=["POST"])
    def add_log() -> tuple:
        """Tar emot JSON med dagboksdata och sparar i databasen."""

        data = request.get_json(silent=True)
        if not data:
            raise BadRequest("Skicka JSON-data i body, t.ex. {\"text\": ...}")

        text = str(data.get("text", "")).strip()
        mood = str(data.get("mood", "")).strip().lower()
        tag = str(data.get("tag", "")).strip().lower()
        entry_date = str(data.get("date", "")).strip()

        if not text:
            raise BadRequest("Fältet 'text' måste fyllas i.")
        if not mood:
            raise BadRequest("Fältet 'mood' måste fyllas i.")
        if not tag:
            raise BadRequest("Fältet 'tag' måste fyllas i.")

        # Om datum inte skickas används dagens datum.
        if entry_date:
            try:
                parsed_date = datetime.fromisoformat(entry_date).date()
            except ValueError as error:
                raise BadRequest("Datum måste vara i ISO-format, t.ex. 2024-05-25.") from error
        else:
            parsed_date = datetime.utcnow().date()

        entry_date_str = parsed_date.isoformat()
        created_at = current_timestamp()

        new_id = execute(
            """
            INSERT INTO diary_logs (entry_date, text, mood, tag, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry_date_str, text, mood, tag, created_at),
        )

        logging.info("Ny dagboksnotering skapad med id %s", new_id)

        return (
            jsonify(
                {
                    "message": "Logg sparad",
                    "log": {
                        "id": new_id,
                        "entry_date": entry_date_str,
                        "text": text,
                        "mood": mood,
                        "tag": tag,
                        "created_at": created_at,
                    },
                }
            ),
            201,
        )

    @app.route("/logs/recent", methods=["GET"])
    def get_recent_logs() -> tuple:
        """Returnerar de 20 senaste loggarna (eller färre om färre finns)."""

        rows = fetch_rows(
            """
            SELECT * FROM diary_logs
            ORDER BY datetime(created_at) DESC
            LIMIT 20
            """
        )
        return jsonify({"count": len(rows), "logs": rows}), 200

    @app.route("/logs/search", methods=["GET"])
    def search_logs() -> tuple:
        """Sök loggar med valfria filter för text (q), tema (tag) eller känsla (mood)."""

        query_text = str(request.args.get("q", "")).strip().lower()
        mood = str(request.args.get("mood", "")).strip().lower()
        tag = str(request.args.get("tag", "")).strip().lower()

        sql = "SELECT * FROM diary_logs WHERE 1=1"
        parameters: List[str] = []

        if query_text:
            sql += " AND LOWER(text) LIKE ?"
            parameters.append(f"%{query_text}%")
        if mood:
            sql += " AND mood = ?"
            parameters.append(mood)
        if tag:
            sql += " AND tag = ?"
            parameters.append(tag)

        sql += " ORDER BY datetime(created_at) DESC"

        rows = fetch_rows(sql, parameters)
        return jsonify({"count": len(rows), "logs": rows}), 200

    @app.route("/logs/weekly-summary", methods=["GET"])
    def weekly_summary() -> tuple:
        """Summerar känslolägen och teman för de senaste sju dagarna."""

        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=6)

        rows = fetch_rows(
            """
            SELECT * FROM diary_logs
            WHERE date(entry_date) BETWEEN ? AND ?
            ORDER BY date(entry_date) ASC
            """,
            (week_ago.isoformat(), today.isoformat()),
        )

        mood_summary: Dict[str, int] = {}
        tag_summary: Dict[str, int] = {}

        for row in rows:
            mood_summary[row["mood"]] = mood_summary.get(row["mood"], 0) + 1
            tag_summary[row["tag"]] = tag_summary.get(row["tag"], 0) + 1

        return (
            jsonify(
                {
                    "entries": len(rows),
                    "from_date": week_ago.isoformat(),
                    "to_date": today.isoformat(),
                    "mood_summary": mood_summary,
                    "tag_summary": tag_summary,
                }
            ),
            200,
        )

    @app.route("/logs/suggestions", methods=["GET"])
    def suggestions() -> tuple:
        """Ger enkla förslag på ritualer/åtgärder utifrån senaste loggarna."""

        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=6)

        recent_logs = fetch_rows(
            """
            SELECT * FROM diary_logs
            WHERE date(entry_date) BETWEEN ? AND ?
            ORDER BY date(entry_date) DESC
            """,
            (week_ago.isoformat(), today.isoformat()),
        )

        suggestions_map = {
            "oro": [
                "Testa 5-minuters andningsövning.",
                "Skriv ner tre saker som känns trygga just nu.",
            ],
            "ångest": [
                "Gör en långsam kroppsscanning och märk vad som känns neutralt.",
                "Kontakta en vän eller vägledare för ett kort check-in.",
            ],
            "hopp": [
                "Planera en liten firande-ritual, t.ex. tända ett ljus och skriva vad du hoppas på.",
                "Dela känslan med någon – sprid hoppet.",
            ],
            "motstånd": [
                "Bryt ner uppgiften i mikro-steg och välj ett att göra direkt.",
                "Skapa en trygg plats: musik, filt, värme – och börja om 5 minuter.",
            ],
            "glädje": [
                "Fira framsteg! Dansa, sjung eller gör något lekfullt i 2 minuter.",
            ],
            "trött": [
                "Planera en micro-paus med stretch eller vila ögon i 3 minuter.",
            ],
        }

        found_moods = {log["mood"] for log in recent_logs}
        found_tags = {log["tag"] for log in recent_logs}

        response: Dict[str, Dict[str, List[str]]] = {"moods": {}, "tags": {}}

        # För varje hittat känsloläge, hämta passande förslag
        mood_suggestions = {}
        for mood in found_moods:
            mood_suggestions[mood] = suggestions_map.get(mood, [
                "Ta en kort paus och känn efter hur kroppen känns.",
                "Skriv tre meningar om vad du behöver just nu.",
            ])

        # För taggar använder vi samma uppsättning men ger unik text
        tag_suggestions = {}
        for tag in found_tags:
            tag_suggestions[tag] = [
                f"Fundera på en ritual kopplad till temat '{tag}'.",
                "Utforska hur temat visar sig i vardagen med en kort anteckning.",
            ]

        response["moods"] = mood_suggestions
        response["tags"] = tag_suggestions

        return jsonify(response), 200

    @app.route("/activity/latest", methods=["GET"])
    def latest_activity() -> tuple:
        """Visar när senaste loggen sparades och hur många timmar sedan det var."""

        rows = fetch_rows(
            """
            SELECT * FROM diary_logs
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """
        )

        if not rows:
            return jsonify({"message": "Inga loggar ännu", "hours_since_last": None}), 200

        latest_log = rows[0]
        last_time = datetime.fromisoformat(latest_log["created_at"])
        hours_since = (datetime.utcnow() - last_time).total_seconds() / 3600

        reminder = None
        if hours_since > 3:
            reminder = "Det har gått mer än 3 timmar sedan senaste kontakten. Vill du checka in?"

        return (
            jsonify(
                {
                    "last_log": latest_log,
                    "hours_since_last": round(hours_since, 2),
                    "reminder": reminder,
                }
            ),
            200,
        )

    @app.route("/logs/audio", methods=["POST"])
    def add_log_from_audio() -> tuple:
        """Tar emot en ljudfil och försöker transkribera den till text."""

        audio_file = request.files.get("audio")
        if audio_file is None:
            raise BadRequest("Skicka en fil i fältet 'audio'.")

        if OpenAI is None:
            return (
                jsonify(
                    {
                        "message": "Installera paketet 'openai' och sätt OPENAI_API_KEY för att använda denna funktion.",
                        "transcription": None,
                    }
                ),
                501,
            )

        # Läser filens binära data till ett minnesobjekt som OpenAI kan använda.
        audio_bytes = io.BytesIO(audio_file.read())
        audio_bytes.name = audio_file.filename or "voice_note.m4a"

        try:
            client = OpenAI()
        except Exception as error:  # pragma: no cover - täcker fall utan API-nyckel
            logging.error("Kunde inte skapa OpenAI-klient: %s", error)
            raise BadRequest("OPENAI_API_KEY saknas eller är ogiltig.") from error

        try:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_bytes,
            )
        except Exception as error:  # pragma: no cover - nätverksfel hanteras här
            logging.error("Misslyckad transkribering: %s", error)
            raise BadRequest("Kunde inte transkribera ljudet. Kontrollera API-nyckel och format.") from error

        text = transcript.text.strip() if transcript and getattr(transcript, "text", "") else ""

        if not text:
            raise BadRequest("Transkriberingen returnerade ingen text.")

        # Standardmood/tagg när man loggar via röst - användaren kan redigera efteråt.
        new_id = execute(
            """
            INSERT INTO diary_logs (entry_date, text, mood, tag, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().date().isoformat(),
                text,
                "okänd",
                "audio",
                current_timestamp(),
            ),
        )

        return (
            jsonify(
                {
                    "message": "Ljud loggat",
                    "transcription": text,
                    "log_id": new_id,
                }
            ),
            201,
        )

    # En enkel hälsningsruta för att visa att servern fungerar
    @app.route("/", methods=["GET"])
    def home() -> tuple:
        """Ger grundinfo om API:et och länkar till viktiga endpoints."""

        endpoints = {
            "POST /logs": "Lägg till dagbokslogg",
            "GET /logs/recent": "Hämta de senaste loggarna",
            "GET /logs/search": "Sök loggar",
            "GET /logs/weekly-summary": "Summera vecka",
            "GET /logs/suggestions": "Få ritualförslag",
            "GET /activity/latest": "Se senaste aktivitet",
            "POST /logs/audio": "Logga via ljud (bonus)",
        }

        return (
            jsonify(
                {
                    "message": "Vi1.0 dagboks-API är igång!",
                    "endpoints": endpoints,
                }
            ),
            200,
        )

    return app


# Gör det möjligt att köra `python -m app.main` direkt.
if __name__ == "__main__":  # pragma: no cover - endast för manuell körning
    create_app().run(debug=True)
