import os
import requests

from dotenv import load_dotenv

from .DocumentManager import DocumentManager

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    raise ValueError("BACKEND_URL is not set in the .env file")

class SummaryGenerator:
    """Handles the generation of summaries from uploaded documents."""

    def __init__(self):
        self.document_manager = DocumentManager()
        self.doc_ids = []

    def ask_chatbot(self, doc_ids, old_response, detailDegree, topicInput, complexitySlider, retryText):
        """Sends a request to the chatbot to generate a summary based on uploaded documents."""
        message = (
            f"Erstelle eine Zusammenfassung mit einer Detailtiefe von {detailDegree}/10 "
            f"und einer Komplexität von {complexitySlider}/10."
        )
        if old_response:
            message += f" Hier ist die vorherige Zusammenfassung: {old_response}"
        if topicInput:
            message += f" Der Themenschwerpunkt ist: {topicInput}."
        if retryText:
            message += f". Außerdem sollen die folgenden Verbesserungswünsche umgesetzt werden: {retryText}"

        message += f" Die relevanten Dokumente haben die IDs: {', '.join(map(str, doc_ids))}."

        payload = {"message": message, "model": "llama-3.1-8b-instant", "document_ids": doc_ids}  # Adjust model if necessary
        response = requests.post(f"{BACKEND_URL}/api/chat", json=payload)

        if response.status_code == 200:
            return response.json()["message"]  # Assuming the bot's response is in `message`
        else:
            raise Exception(f"Chatbot request failed: {response.text}")


    def retry_summary(self, old_response, detailDegree, topicInput, complexitySlider, retryText):
        """Handles the full process of uploading PDFs and generating a summary."""
        try:
            # Generate a summary via the chatbot
            summary_text = self.ask_chatbot(self.doc_ids, old_response, detailDegree, topicInput, complexitySlider, retryText)

            return None, summary_text
        except Exception as e:
            print("Exception:", e)
            return None, str(e)


    def create_summary(self, file_names, detailDegree, topicInput, complexitySlider):
        """Handles the full process of uploading PDFs and generating a summary."""
        try:
            # Upload PDFs
            self.doc_ids = self.document_manager.upload_pdfs(file_names)

            # Generate a summary via the chatbot
            summary_text = self.ask_chatbot(self.doc_ids, None, detailDegree, topicInput, complexitySlider, None)

            # Cleanup uploaded files
            for file_name in file_names:
                os.remove(file_name)

            print("Files deleted")
            return summary_text
        except Exception as e:
            print("Exception:", e)
            return str(e)
