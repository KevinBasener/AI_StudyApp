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


class ExamGenerator:
    """Handles the creation of exams from uploaded PDFs."""

    def __init__(self):
        self.document_manager = DocumentManager()
        self.doc_ids = []

    def ask_chatbot(self, oldResponse, numExercises, topicInput, complexitySlider, retryText):
        """Sends a request to the chatbot to generate an exam based on uploaded documents."""
        message = (
            f"Du bist 'Carl The Exam Creator', ein fortschrittlicher Assistent, der darauf spezialisiert ist, "
            f"Probeklausuren auf Basis hochgeladener PDF-Dateien zu erstellen. "
            f"Erstelle eine Klausur mit {numExercises} Aufgaben und einer Komplexität von {complexitySlider}/10."
        )
        if topicInput:
            message += f" Der Themenschwerpunkt ist: {topicInput}."
        if retryText:
            message += f" Außerdem sollen die folgenden Verbesserungswünsche umgesetzt werden: {retryText}"
        if oldResponse:
            message += f" Hier ist die vorherige Klausur: {oldResponse}"

        message += """\nDeine Antwort **muss ein valides JSON-Format haben**. Antworte **nur** mit JSON, ohne zusätzliche Erklärungen, Kommentare oder Markdown-Formatierung.
            Hier ist das **genaue JSON-Format**, das du zurückgeben sollst:\n\n```json\n[
            {"exercise": "## Probeklausur: [Thema]\\n\\n### Aufgabe 1: [Kategorie] ([Punkte] Punkte)\\n1. [Frage 1] ([Punkte] Punkt)\\n2. [Frage 2] ([Punkte] Punkt)\\n\\n### Aufgabe 2: [Kategorie] ([Punkte] Punkte)\\n1. [Frage 3] ([Punkte] Punkt)\\n2. [Frage 4] ([Punkte] Punkt)\\n\\n### Aufgabe 3: [Kategorie] ([Punkte] Punkte)\\n1. [Frage 5] ([Punkte] Punkt)\\n2. [Frage 6] ([Punkte] Punkt)",
            "answer": "## Lösungen zur Probeklausur: [Thema]\\n\\n### Aufgabe 1: [Kategorie]\\n1. [Lösung zu Frage 1]\\n2. [Lösung zu Frage 2]\\n\\n### Aufgabe 2: [Kategorie]\\n1. [Lösung zu Frage 3]\\n2. [Lösung zu Frage 4]\\n\\n### Aufgabe 3: [Kategorie]\\n1. [Lösung zu Frage 5]\\n2. [Lösung zu Frage 6]"}

        ]\n``` Und markiere deine JSON Antwort mit dem Tag ```json```."""

        payload = {
            "message": message,
            "model": "llama-3.1-8b-instant",  # Adjust model if needed
            "document_ids": self.doc_ids,
        }

        retry_count = 0
        while retry_count < MAX_PROMPT_TRYS:
            print(f"Try number: {retry_count + 1}")
            print(f"Attempt {retry_count + 1}: Sending request to chatbot...")

            payload = {"message": message, "model": "llama-3.1-8b-instant", "document_ids": self.doc_ids}
            response = requests.post(f"{BACKEND_URL}/api/chat", json=payload)

            if response.status_code == 200:
                chatbot_response = response.json().get("message", "")

                # Try parsing JSON
                examJSON, errorMessage = extract_and_parse_json(chatbot_response)

                if self.validate_json_structure(examJSON):
                    return examJSON  # Return valid JSON

            print("Invalid JSON received. Retrying...")
            retry_count += 1

        raise Exception("Chatbot response did not return valid JSON after multiple attempts.")

    def validate_json_structure(self, data):
        """Validates that the JSON response has the expected structure."""
        if not isinstance(data, list):
            return False

        for item in data:
            if not isinstance(item, dict) or "exercise" not in item or "answer" not in item:
                return False

        return True  # JSON is valid

    def retry_exam(self, old_response, numExercises, topicInput, complexitySlider, retryText):
        """Handles the full process of uploading PDFs and generating a summary."""
        try:
            # Generate a summary via the chatbot
            summary_text = self.ask_chatbot(old_response, numExercises, topicInput, complexitySlider, retryText)

            return None, summary_text
        except Exception as e:
            print("Exception:", e)
            return None, str(e)

    def create_exam(self, file_names, numExercises, topicInput, complexitySlider):
        """Uploads PDFs and generates an exam."""
        try:
            # Upload PDFs and get document IDs
            self.doc_ids = self.document_manager.upload_pdfs(file_names)

            # Generate exam via chatbot
            exam_text = self.ask_chatbot(None, numExercises, topicInput, complexitySlider, None)

            # Cleanup uploaded files
            for file_name in file_names:
                os.remove(file_name)

            print("Files deleted")
            return None, exam_text
        except Exception as e:
            print("Exception:", e)
            return str(e), None
