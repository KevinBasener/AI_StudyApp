import random
import uuid

from django.views.generic import TemplateView
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse, FileResponse
from pptx import Presentation

from web_project import TemplateLayout
from rest_framework.views import APIView
from requests import Request, post

from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view

from openai import OpenAI
import time, os

from .ExamGenerator import ExamGenerator
from .SlidesGenerator import SlidesGenerator
from .models import UploadedFile
from .serializers import UploadedFileSerializer
import json, requests

from .summaryGenerator import SummaryGenerator
from .LearncardsGenerator import LearnCardsGenerator
from .Utils import extract_and_parse_json

"""
This file is a view controller for multiple pages as a module.
Here you can override the page view layout.
Refer to sample/urls.py file for more pages.
"""

RESOURCE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources"))
summary_generator = SummaryGenerator()
exam_generator = ExamGenerator()
learncards_generator = LearnCardsGenerator()
slides_generator = SlidesGenerator()


class FileUploadView(APIView):
    print("FileUploadView")
    parser_classes = (MultiPartParser, FormParser)


@api_view(["POST"])
def postPDF(request):
    filenames = []
    print("Request: ", request.FILES.items())

    if request.method == "POST":
        # Iterieren über alle hochgeladenen Dateien
        for field_name, uploaded_files in request.FILES.lists():
            # 'uploaded_files' kann eine Liste von Dateien sein
            for uploaded_file in uploaded_files:
                print("Datei: ", uploaded_file.name)
                fs = FileSystemStorage()
                filename = fs.save(uploaded_file.name, uploaded_file)
                filenames.append(filename)

    if filenames:
        # Konvertieren der Liste von Dateinamen in einen String, um ihn auszugeben
        filenames_str = ", ".join(filenames)
        print("Dateinamen: " + filenames_str)
        result_dict = {
            "data": filenames,
            "message": "Files uploaded and processed successfully",
        }
        return Response(result_dict, status=status.HTTP_201_CREATED)
    else:
        return Response(
            {"error": "Failed to process the uploaded files"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
def getExam(request):
    """API endpoint to generate an exam from uploaded PDFs."""
    try:
        data = request.data
        file_names = data.get("filename")  # Expecting a list of file paths
        numExercises = data.get("numExercises")
        topicInput = data.get("topic")
        complexitySlider = data.get("complexity")

        if not file_names:
            return Response({"error": "Missing file names"}, status=status.HTTP_400_BAD_REQUEST)

        errorMessage, exam_text = exam_generator.create_exam(file_names, numExercises, topicInput, complexitySlider)

        result_dict = {
            "data": exam_text,
            "errorMessage": errorMessage,
            "message": "Exam created successfully",
        }
        return Response(result_dict, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Exception in getExam:", str(e))
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def retryExam(request):
    print(request)
    data = request.data
    assistant_id = "asst_7jrCIkWKfn3M4lllefB3f6Nd"
    numExercises = request.data.get("numExercises")
    topicInput = request.data.get("topic")
    retryText = request.data.get("retryText")
    oldResponse = request.data.get("old_response")
    complexitySlider = request.data.get("complexity")

    errorMessage, exam_text = exam_generator.retry_exam(oldResponse, numExercises, topicInput, complexitySlider,
                                                           retryText)
    print("Result retry exam Text: ", exam_text)

    result_dict = {
        "data": exam_text,
        "thread_id": None,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }
    return Response(result_dict, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def retrySummary(request):
    print(request)
    data = request.data
    assistant_id = "asst_as7nuJcgHK52ciw9TGKWVqTZ"
    detailDegree = request.data.get("detailDegree")
    topicInput = request.data.get("topic")
    oldResponse = request.data.get("old_response")
    complexitySlider = request.data.get("complexity")
    retryText = request.data.get("retryText")

    thread_id, exam_text = summary_generator.retry_summary(oldResponse, detailDegree, topicInput, complexitySlider, retryText)
    print("Result retry exam Text: ", exam_text)

    errorMessage = None

    result_dict = {
        "data": exam_text,
        "thread_id": thread_id,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }
    return Response(result_dict, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def retrySlides(request):
    print(request)
    data = request.data
    assistant_id = "asst_Rq7xXvGyh8NfT9b4n4bkmDqx"
    numSlides = request.data.get("numSlides")
    topicInput = request.data.get("topic")
    complexitySlider = request.data.get("complexity")
    textInput = request.data.get("textInput")
    retryText = request.data.get("retryText")
    oldResponse = request.data.get("old_response")
    thread_id = request.data.get("thread_id")

    slidesJSON, errorMessage = slides_generator.retry_slides(oldResponse, textInput, numSlides, topicInput, complexitySlider, retryText)

    result_dict = {
        "data": slidesJSON,
        "thread_id": thread_id,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }
    return Response(result_dict, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def retryLeanCards(request):
    print(request)
    data = request.data
    assistant_id = "asst_N4e78jd5WMA0Gt9e26G2z9id"
    numSlides = request.data.get("numSlides")
    topicInput = request.data.get("topic")
    complexitySlider = request.data.get("complexity")
    retryText = request.data.get("retryText")
    oldResponse = request.data.get("old_response")
    thread_id = request.data.get("thread_id")

    slidesJSON, errorMessage = learncards_generator.retry_learncards(oldResponse, numSlides, complexitySlider, topicInput, retryText)
    print("Result retry exam Text: ", slidesJSON)

    result_dict = {
        "data": slidesJSON,
        "thread_id": thread_id,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }
    return Response(result_dict, status=status.HTTP_201_CREATED)

@api_view(["POST"])
def getSummary(request):
    print(request)
    data = request.data
    filename = data.get("filename")
    print("Processing Uploaded PDF to create exam...")
    print("filename: ", filename)
    assistant_id = "asst_as7nuJcgHK52ciw9TGKWVqTZ"

    detailDegree = request.data.get("detailDegree")
    topicInput = request.data.get("topic")
    complexitySlider = request.data.get("complexity")
    print("Debugging: before create_exam")
    thread_id, exam_text = create_summary(
        filename, assistant_id, detailDegree, topicInput, complexitySlider
    )

    errorMessage = None

    if exam_text != "error":
        response_data = {
            "data": [
                ["annotations", []],  # Placeholder for annotations if any
                [
                    "value",
                    exam_text  # Assuming exam_text contains the desired summary
                ]
            ],
            "thread_id": thread_id,
            "errorMessage":  errorMessage,
            "message": "File uploaded and processed successfully"
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    else:
        return Response(
            {"error": "Failed to process the uploaded file"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
def getLearnCards(request):
    print(request)
    data = request.data
    numSlides = request.data.get("numSlides")
    topicInput = request.data.get("topic")
    complexity = request.data.get("complexity")
    filename = data.get("filename")
    print("Processing Uploaded PDF to create exam...")
    print("filename: ", filename)
    assistant_id = "asst_N4e78jd5WMA0Gt9e26G2z9id"

    slidesJSON, errorMessage = learncards_generator.create_learncards(filename, numSlides, complexity, topicInput)

    result_dict = {
        "data": slidesJSON,
        "thread_id": None,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }

    return Response(result_dict, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def getSlides(request):
    data = request.data
    numSlides = data.get("numSlides")
    topicInput = data.get("topic")
    text = data.get("text")
    filename = data.get("filename")
    complexity = data.get("complexity")
    slidesJSON, errorMessage=slides_generator.create_presentation(
        text, filename, complexity, numSlides, topicInput
    )

    result_dict = {
        "data": slidesJSON,
        "response_id": None,
        "errorMessage": errorMessage,
        "message": "File uploaded and processed successfully",
    }

    return Response(result_dict, status=status.HTTP_201_CREATED)


# pdf that will be used for the test
# pdf_file_path = "Skript_fuer_testklausur.pdf"
# pdf_file_path = "RAarith2.pdf"

def download_presentation(request):
    file_path = os.path.join(RESOURCE_PATH, "result.pptx")
    if os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename="result.pptx")
    else:
        return HttpResponse("File not found", status=404)


def create_presentation_with_headlines(template_path, output_path, ai_response):
    # Load the PowerPoint template
    presentation = Presentation(template_path)

    # Extract presentation metadata
    pres_data = ai_response['Presentation']
    pres_title = pres_data['Title']
    pres_subtitle = pres_data['Subtitle']

    # Create the title slide
    title_slide_layout = presentation.slide_layouts[0]  # Title slide layout
    title_slide = presentation.slides.add_slide(title_slide_layout)
    title_slide.shapes.title.text = pres_title

    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = pres_subtitle

    # Create content slides
    for slide_info in pres_data['Slides']:
        slide_title = slide_info['Title']
        slide_content = slide_info['Content']

        # Create a section header slide
        section_slide_layout = presentation.slide_layouts[0]  # Title slide layout
        section_slide = presentation.slides.add_slide(section_slide_layout)
        section_slide.shapes.title.text = slide_title

        # Add content slide
        content_slide_layout = presentation.slide_layouts[1]  # Title and Content layout
        content_slide = presentation.slides.add_slide(content_slide_layout)
        content_slide.shapes.title.text = slide_title

        # Add content to the slide's placeholder
        if len(content_slide.placeholders) > 1:
            content_placeholder = content_slide.placeholders[1]
            content_placeholder.text = slide_content

            # Add bullet points if available
            if 'BulletPoints' in slide_info and slide_info['BulletPoints']:
                for bullet in slide_info['BulletPoints']:
                    p = content_placeholder.text_frame.add_paragraph()
                    p.text = "\n-" + bullet

    # Remove the first empty slide if present
    if len(presentation.slides) > 1 and not presentation.slides[0].shapes.title.text:
        slide_ids = presentation.slides._sldIdLst
        slide_id_list = list(slide_ids)
        slide_ids.remove(slide_id_list[0])

    # Save the final presentation
    presentation.save(output_path)
    print(f"Presentation saved to {output_path}")

def create_summary(file_names, assistant_id, detailDegree, topicInput, complexitySlider):
    try:
        summary_text = summary_generator.create_summary(file_names, detailDegree, topicInput, complexitySlider)
        return 1, summary_text
    except Exception as e:
        print("Exception:", e)
        return None, str(e)

class SampleView(TemplateView):
    # Predefined function
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        return context
