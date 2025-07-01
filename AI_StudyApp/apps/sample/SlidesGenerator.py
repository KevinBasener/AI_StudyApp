import os
import uuid

import requests
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.shapes import PP_PLACEHOLDER

from .DocumentManager import DocumentManager
from .Utils import extract_and_parse_json

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")
RESOURCE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources"))
MAX_PROMPT_TRYS = 3
if not BACKEND_URL:
    raise ValueError("BACKEND_URL is not set in the .env file")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    print("Warning: PEXELS_API_KEY not found in .env file. Image search will fail.")

class SlidesGenerator:
    """Handles the creation of PowerPoint presentations based on user input."""

    def __init__(self):
        self.document_manager = DocumentManager()
        self.doc_ids = []
        self.template_path = os.path.join(RESOURCE_PATH, "presentation.pptx")
        self.output_path = os.path.join(RESOURCE_PATH, "result.pptx")

    def ask_chatbot(self, oldResponse, textInput, complexity, numSlides, topicInput, retryText):
        """Sends a request to the chatbot to generate slides, including image keywords."""
        message = (
            f"Erstelle eine Präsentation nach folgenden Kriterien. "
            f"Die Komplexität soll {complexity} von 10 betragen. "
            f"Es sollen {numSlides} Folien auf Deutsch erstellt werden."
        )
        # ... (rest of your existing message construction) ...
        if topicInput:
            message += f" Der Themenschwerpunkt ist: {topicInput}."
        if textInput:
            message += f" Die Präsentation wird wie folgt beschrieben: {textInput}"
        if oldResponse:
            message += f" Hier ist die vorherige Präsentation: {oldResponse}"
        if retryText:
            message += f" Außerdem sollen die folgenden Verbesserungswünsche umgesetzt werden: {retryText}"

        message += (
            # CHANGED instruction: Ask for keywords now
            "\n\nFür **jede Inhaltsfolie** (nicht die Titelfolie), gib bitte auch relevante **'ImageKeywords'** an. "
            "Dies sollte eine kurze Liste von 1-4 englischen Schlüsselwörtern sein (Komma-getrennt), die das Thema der Folie gut beschreiben und für die Suche in einer Stockfoto-Datenbank (wie Pexels) geeignet sind."

            "\n\nDeine Antwort **muss ein valides JSON-Format haben**. Antworte **nur** mit JSON, ohne zusätzliche Erklärungen, Kommentare oder Markdown-Formatierung."
            "Die JSON-Marker ```json``` dürfen auf keinen Fall fehlen."
            "Hier ist das **genaue JSON-Format**, das du zurückgeben sollst:\n\n"
            "```json{\"Presentation\": {\n"  # Make sure there's no newline after json marker
            "  \"Title\": \"[Haupttitel der Präsentation]\",\n"
            "  \"Subtitle\": \"[Kurzer beschreibender Untertitel]\",\n"
            "  \"Complexity\": [Komplexitätsgrad von 1.0 bis 5.0],\n"
            "  \"Slides\": [\n"
            # CHANGED ImagePrompt to ImageKeywords and updated example
            "    { \"Title\": \"[Titel der Folie]\", \"Content\": \"[Inhalt der Folie]\", \"ImageKeywords\": \"[Comma-separated English keywords, e.g., 'network, data, connection, abstract']\" },\n"
            "    { \"Title\": \"[Titel der nächsten Folie]\", \"Content\": \"[Inhalt der nächsten Folie]\", \"ImageKeywords\": \"[Another set of keywords...]\" }\n"
            "  ]\n"
            "}}\n```"
        )

        # --- The rest of the ask_chatbot method (retry loop, request sending, JSON parsing) remains largely the same ---
        # Make sure it calls the UPDATED validate_json_structure below
        retry_count = 0
        while retry_count < MAX_PROMPT_TRYS:
            print(f"Attempt {retry_count + 1}: Sending request to chatbot...")
            payload = {
                "message": message,
                "model": "llama3-8b-8192",  # Or a model better suited for structured output
                "document_ids": self.doc_ids,
            }
            try:
                # Use a reasonable timeout
                response = requests.post(f"{BACKEND_URL}/api/chat", json=payload, timeout=180)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                chatbot_response = response.json().get("message", "")
                slidesJSON, errorMessage = extract_and_parse_json(chatbot_response)

                if errorMessage:
                    print(f"Error parsing JSON: {errorMessage}")
                    # print(f"Raw response causing error:\n{chatbot_response}") # Debugging
                # Use the updated validation function
                elif self.validate_json_structure(slidesJSON):
                    print("Valid JSON structure received.")
                    return slidesJSON  # Return valid JSON

                print("Invalid or non-compliant JSON received. Retrying...")
                # print(f"Invalid JSON data received:\n{slidesJSON}") # Debugging

            except requests.exceptions.Timeout:
                print("Request to chatbot backend timed out.")
            except requests.exceptions.RequestException as e:
                print(f"Network error contacting chatbot backend: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during chatbot request: {e}")
                # import traceback # Add this import at the top
                # traceback.print_exc() # More detailed debug info

            retry_count += 1
            # Optional: Add a small delay before retrying
            # import time
            # time.sleep(2)

        raise Exception(
            "Chatbot response did not return valid JSON matching the required structure after multiple attempts.")


    def validate_json_structure(self, data):
        """Validates that the JSON response has the expected structure, including ImageKeywords."""
        if not isinstance(data, dict) or "Presentation" not in data:
            print("Validation Error: Missing 'Presentation' key.")
            return False

        presentation = data["Presentation"]
        required_presentation_keys = {"Title", "Subtitle", "Complexity", "Slides"}
        if not isinstance(presentation, dict) or not required_presentation_keys.issubset(presentation.keys()):
            print(
                f"Validation Error: Missing keys in 'Presentation' object. Found: {list(presentation.keys()) if isinstance(presentation, dict) else type(presentation)}")
            return False

        if not isinstance(presentation.get("Complexity"), (int, float)):
            print("Validation Error: 'Complexity' is not a number.")
            return False

        slides = presentation.get("Slides")
        if not isinstance(slides, list):
            print("Validation Error: 'Slides' is not a list.")
            return False

        for i, slide in enumerate(slides):
            if not isinstance(slide, dict) or "Title" not in slide or "Content" not in slide:
                print(f"Validation Error: Slide {i} missing 'Title' or 'Content'.")
                return False
            # Check for ImageKeywords: must be a string if present, but can be missing (optional)
            if "ImageKeywords" in slide and not isinstance(slide["ImageKeywords"], str):
                print(f"Validation Error: Slide {i} 'ImageKeywords' exists but is not a string.")
                return False
            # Add BulletPoints check if needed

        print("JSON structure validation passed.")
        return True  # JSON structure is valid


    def _search_and_download_pexels_image(self, keywords: str) -> str | None:
        """Searches Pexels for an image based on keywords and downloads it locally."""
        if not PEXELS_API_KEY:
            print("Pexels API key not available. Cannot search for image.")
            return None
        if not keywords or keywords.isspace():
            print("No image keywords provided. Skipping image search.")
            return None

        search_url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": keywords,
            "per_page": 1,  # We only need one image
            "orientation": "landscape"  # Better for slides usually
        }

        print(f"Searching Pexels for keywords: '{keywords}'")
        try:
            # Search Pexels API
            response = requests.get(search_url, headers=headers, params=params, timeout=15)  # Add timeout
            response.raise_for_status()  # Check for HTTP errors (4xx, 5xx)

            results = response.json()

            # Check if any photos were found
            if results and results.get("photos") and len(results["photos"]) > 0:
                # Get the URL of a suitable image size (e.g., 'large')
                image_url = results["photos"][0]["src"].get("large")  # Or 'medium', 'large2x'
                if not image_url:
                    image_url = results["photos"][0]["src"].get("original")  # Fallback

                if image_url:
                    print(f"Image found on Pexels. URL: {image_url}")

                    # Download the image
                    image_response = requests.get(image_url, stream=True, timeout=30)  # Timeout for download
                    image_response.raise_for_status()

                    # Save to a temporary file
                    temp_dir = os.path.join(RESOURCE_PATH, "temp_images")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_filename = os.path.join(temp_dir,
                                                 f"slide_image_{uuid.uuid4()}.png")  # Assume PNG, adjust if needed

                    with open(temp_filename, 'wb') as f:
                        for chunk in image_response.iter_content(8192):
                            f.write(chunk)

                    print(f"Image downloaded and saved to: {temp_filename}")
                    return temp_filename
                else:
                    print("Image found, but suitable image URL ('large' or 'original') is missing.")
                    return None
            else:
                # === Handle "Image Not Found" ===
                print(f"No image found on Pexels for keywords: '{keywords}'")
                return None  # Explicitly return None when no image is found

        except requests.exceptions.Timeout:
            print(f"Timeout during Pexels API request or image download for keywords: {keywords}")
        except requests.exceptions.RequestException as e:
            print(f"Error during Pexels API request or image download for '{keywords}': {e}")
            # Check for specific status codes if needed (e.g., 401 Unauthorized, 429 Rate Limit)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status Code: {e.response.status_code}")
                # print(f"Response Body: {e.response.text}") # Debugging
        except Exception as e:
            print(f"Unexpected error during Pexels image search/download for '{keywords}': {e}")

        return None  # Return None if any error occurred


    def retry_slides(self, old_response, textInput,  numExercises, topicInput, complexitySlider, retryText):
        """Handles the full process of uploading PDFs and generating a summary."""
        try:
            # Generate a summary via the chatbot
            slides_text = self.ask_chatbot(old_response,  textInput, complexitySlider, numExercises, topicInput, retryText)

            slidesJSON = extract_and_parse_json(slides_text)

            self.create_powerpoint(slidesJSON)

            return slidesJSON, None
        except Exception as e:
            print("Exception:", e)
            return None, str(e)

    def create_powerpoint(self, ai_response):
        """Creates a PowerPoint presentation using layout 9 for slides with images."""

        # --- Optional: Add validation check at the start ---
        if not self.validate_json_structure(ai_response):
            print("Cannot create PowerPoint. Invalid JSON structure provided.")
            raise ValueError("Invalid JSON structure for PowerPoint creation.")

        generated_image_paths = [] # Keep track of downloaded images for cleanup
        try:
            presentation = Presentation(self.template_path)
            pres_data = ai_response['Presentation']
            pres_title = pres_data.get('Title', 'Presentation Title')
            pres_subtitle = pres_data.get('Subtitle', '')

            # --- Define Layout Indices ---
            # Use the 10th layout (index 9) for slides with pictures, as specified
            picture_layout_index = 8
            # Use a standard layout for text-only slides (e.g., Title and Content, often index 1)
            # *** VERIFY THIS INDEX FOR YOUR TEMPLATE ***
            text_only_layout_index = 1

            # --- Title Slide ---
            # (Keep your existing title slide creation logic)
            try:
                title_slide_layout = presentation.slide_layouts[0]
                title_slide = presentation.slides.add_slide(title_slide_layout)
                if title_slide.shapes.title: # Check if title shape exists
                    title_slide.shapes.title.text = pres_title
                # Check for subtitle placeholder by index (common) or type if needed
                if len(title_slide.placeholders) > 1 and hasattr(title_slide.placeholders[1], 'has_text_frame') and title_slide.placeholders[1].has_text_frame:
                     title_slide.placeholders[1].text = pres_subtitle
                elif title_slide.has_notes_slide: # Example fallback: put subtitle in notes?
                     title_slide.notes_slide.notes_text_frame.text = pres_subtitle
            except IndexError:
                print("Error: Could not find slide layout index 0 for the title slide.")
                raise # Or handle differently


            # --- Create Content Slides ---
            for slide_info in pres_data.get('Slides', []):
                slide_title = slide_info.get('Title', 'Slide Title')
                slide_content = slide_info.get('Content', '')
                image_keywords = slide_info.get('ImageKeywords')

                # --- Choose Layout Based on ImageKeywords ---
                if image_keywords:
                    print(f"Using layout {picture_layout_index} for slide '{slide_title}' (with image).")
                    try:
                        layout = presentation.slide_layouts[picture_layout_index]
                    except IndexError:
                        print(f"Error: Layout index {picture_layout_index} not found! Falling back to layout 1.")
                        layout = presentation.slide_layouts[text_only_layout_index] # Fallback
                        image_keywords = None # Treat as text-only if intended layout is missing
                else:
                    print(f"Using layout {text_only_layout_index} for slide '{slide_title}' (text only).")
                    try:
                        layout = presentation.slide_layouts[text_only_layout_index]
                    except IndexError:
                        print(f"Error: Layout index {text_only_layout_index} not found! Skipping slide.")
                        continue # Skip this slide if text layout is missing

                content_slide = presentation.slides.add_slide(layout)

                # --- Assign Title ---
                if content_slide.shapes.title:
                    content_slide.shapes.title.text = slide_title
                elif len(content_slide.placeholders) > 0: # Fallback
                     try:
                          content_slide.placeholders[0].text = slide_title
                     except Exception as e_title:
                          print(f"Could not set title placeholder text for '{slide_title}': {e_title}")

                # --- Find Placeholders (Adapt based on expected placeholders in *both* layouts) ---
                text_placeholder = None
                picture_placeholder = None # Only relevant for picture layout

                # Iterate through the placeholders defined in the layout for this slide
                for shape in content_slide.placeholders:
                    ph_format = shape.placeholder_format
                    # Use PP_PLACEHOLDER members to check the type
                    print(
                        f"DEBUG: Found placeholder: Name='{shape.name}', Type={ph_format.type}, Idx={ph_format.idx}")  # Helpful for debugging

                    # Check for Picture placeholder type
                    if ph_format.type == PP_PLACEHOLDER.PICTURE:  # Correct enum member
                        picture_placeholder = shape
                        print(f"DEBUG: Identified as Picture Placeholder: {shape.name}")

                    # Check for Body or Object placeholder types (common for main text)
                    # PP_PLACEHOLDER.BODY is standard for main content.
                    # PP_PLACEHOLDER.OBJECT can also sometimes hold text content.
                    elif ph_format.type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
                        # Take the first Body/Object placeholder found as the text placeholder
                        if text_placeholder is None:
                            text_placeholder = shape
                            print(f"DEBUG: Identified as Text Placeholder: {shape.name} (Type: {ph_format.type})")
                    # Add checks for other types if necessary based on your template

                # --- Add Text Content ---
                if text_placeholder:
                    text_frame = text_placeholder.text_frame
                    text_frame.clear()
                    text_frame.word_wrap = True
                    p = text_frame.add_paragraph()
                    p.text = slide_content
                    # ... (bullet point logic) ...
                else:
                    # Log a more specific warning if text placeholder wasn't found
                    print(
                        f"Warning: Could not find BODY or OBJECT placeholder for text on slide '{slide_title}'. Layout index used: {layout.name if hasattr(layout, 'name') else picture_layout_index if image_keywords else text_only_layout_index}")

                # --- Add Image ---
                if image_keywords and picture_placeholder:  # Check if we found the picture placeholder
                    image_path = self._search_and_download_pexels_image(image_keywords)
                    if image_path:
                        generated_image_paths.append(image_path)
                        try:
                            print(f"Inserting picture into placeholder: {picture_placeholder.name} ({image_path})")
                            picture_placeholder.insert_picture(image_path)
                        except Exception as e:
                            print(f"Error inserting picture {image_path} into placeholder: {e}")
                elif image_keywords and not picture_placeholder:
                    print(
                        f"Warning: Image keywords provided for slide '{slide_title}', but no PICTURE placeholder found on layout. Image skipped.")

            # --- Save and Cleanup ---
            presentation.save(self.output_path)
            print(f"Presentation saved to {self.output_path}")

        except Exception as e:
             print(f"Error during PowerPoint creation: {e}")
             # import traceback
             # traceback.print_exc() # Uncomment for detailed debugging
             raise e # Propagate error after logging
        finally:
             # Cleanup temporary image files
             self._cleanup_temp_images(generated_image_paths) # Pass the list to cleanup

    # --- Update cleanup function to accept list ---
    def _cleanup_temp_images(self, image_paths_to_delete: list):
        """Deletes specified temporary image files."""
        if not image_paths_to_delete:
            return

        removed_count = 0
        print(f"Cleaning up {len(image_paths_to_delete)} downloaded image(s)...")
        for img_path in image_paths_to_delete:
            try:
                if os.path.exists(img_path): # Check if file exists before removing
                    os.remove(img_path)
                    removed_count += 1
                else:
                    print(f"Warning: Temp image file not found for deletion: {img_path}")
            except OSError as e_rm:
                print(f"Error removing temporary file {img_path}: {e_rm}")

        if removed_count > 0:
            print(f"Cleaned up {removed_count} temporary images.")
        # Optional: Cleanup directory if empty logic can remain

    def create_presentation(self, textInput, file_names, complexity, numSlides, topicInput):
        """Uploads PDFs (if provided) and generates a presentation."""
        try:
            if(file_names != None):
                self.doc_ids = self.document_manager.upload_pdfs(file_names)

            slidesJSON = self.ask_chatbot(None, textInput, complexity, numSlides, topicInput, None)

            self.create_powerpoint(slidesJSON)

            # Cleanup uploaded files
            if file_names != None:
                for file_name in file_names:
                    os.remove(file_name)
                    print("Files deleted")

            return slidesJSON, None
        except Exception as e:
            print("Exception:", str(e))
            return str(e), str(e)
