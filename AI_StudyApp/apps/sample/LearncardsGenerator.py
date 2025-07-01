import os
import requests
from dotenv import load_dotenv
from .DocumentManager import DocumentManager
from .Utils import extract_and_parse_json

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")
MAX_PROMPT_TRYS = 3
if not BACKEND_URL:
    raise ValueError("BACKEND_URL is not set in the .env file")


class LearnCardsGenerator:
    """Handles the creation of learning cards from uploaded PDFs."""

    def __init__(self):
        self.document_manager = DocumentManager()
        self.doc_ids = []

    def ask_chatbot(self, oldResponse, complexity, topicInput, numCards, retryText):
        """Sends a request to the chatbot to generate learning cards based on uploaded documents."""
        message = (
            f"Du bist 'Carl The Learncard Creator', ein fortschrittlicher Assistent, der darauf spezialisiert ist, "
            f"Lernkarten basierend auf hochgeladenen PDF-Dateien zu erstellen. "
            f"Erstelle {numCards} Lernkarten."
        )
        if topicInput:
            message += f" Der Themenschwerpunkt ist: {topicInput}."
        if retryText:
            message += f" Außerdem sollen die folgenden Verbesserungswünsche umgesetzt werden: {retryText}"
        if oldResponse:
            message += f" Hier sind die vorherigen Lernkarten: {oldResponse}"

        message += f" Die relevanten Dokumente haben die IDs: {', '.join(map(str, self.doc_ids))}."
        message += """
            Deine Antwort **muss ein valides JSON-Format haben**. Antworte **nur** mit JSON, ohne zusätzliche Erklärungen, Kommentare oder Markdown-Formatierung.
            Die json-Marker ```json``` dürfen auf keinen Fall fehlen.
            Hier ist das **genaue JSON-Format**, das du zurückgeben sollst:

            ```json
            [
                {"question": "Was ist das Ohmsche Gesetz?", "answer": "Das Ohmsche Gesetz besagt, dass die Spannung in einem Leiter direkt proportional zum Strom ist: U = R * I."},
                {"question": "Was ist die Funktion eines Kondensators?", "answer": "Ein Kondensator speichert elektrische Energie in einem elektrischen Feld."}
            ]
            ```
            """
        payload = {
            "message": message,
            "model": "llama-3.1-8b-instant",
            "document_ids": self.doc_ids,
        }

        retry_count = 0
        while retry_count <= MAX_PROMPT_TRYS:
            print(f"Attempt {retry_count + 1}: Sending request to chatbot...")

            payload = {"message": message, "model": "llama-3.1-8b-instant", "document_ids": self.doc_ids}
            response = requests.post(f"{BACKEND_URL}/api/chat", json=payload)

            if response.status_code == 200:
                chatbot_response = response.json().get("message", "")

                # Try parsing JSON
                learncardsJSON, errorMessage = extract_and_parse_json(chatbot_response)

                if self.validate_json_structure(learncardsJSON):
                    return learncardsJSON  # Return valid JSON

            print("Invalid JSON received. Retrying...")
            retry_count += 1

        raise Exception("Chatbot response did not return valid JSON after multiple attempts.")

    def validate_json_structure(self, data):
        """Validates that the JSON response has the expected structure."""
        if not isinstance(data, list):
            return False

        for item in data:
            if not isinstance(item, dict) or "question" not in item or "answer" not in item:
                return False

        return True  # JSON is valid


    def retry_learncards(self, old_response, numCards, complexity, topicInput, retryText):
            try:
                # Generate learncards via chatbot
                learncards_text = self.ask_chatbot(old_response, complexity, topicInput, numCards, retryText)

                return learncards_text, None
            except Exception as e:
                print("Exception:", e)
                return None, str(e)

    def create_learncards(self, file_names, numCards, complexity, topicInput):
        """Uploads PDFs and generates learning cards."""
        try:
            # Upload PDFs and get document IDs
            self.doc_ids = self.document_manager.upload_pdfs(file_names)

            # Generate learncards via chatbot
            learncards_text = self.ask_chatbot(None, topicInput, complexity, numCards, None)

            # Cleanup uploaded files
            for file_name in file_names:
                os.remove(file_name)

            print("Files deleted")
            return learncards_text, None
        except Exception as e:
            print("Exception:", e)
            return [], str(e)
