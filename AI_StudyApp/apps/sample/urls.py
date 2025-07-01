from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
    SampleView,
    FileUploadView,
    postPDF,
    getExam,
    getSummary,
    getLearnCards,
    getSlides,
    retryExam,
    retrySummary,
    retrySlides,
    retryLeanCards,
    download_presentation
)  # ,UploadPDF


urlpatterns = [
    path(
        "",
        login_required(SampleView.as_view(template_name="index.html")),
        name="index",
    ),
    path(
        "summaryCreator/",
        login_required(SampleView.as_view(template_name="summaryCreator.html")),
        name="summaryCreator",
    ),
    path(
        "learnCards/",
        login_required(SampleView.as_view(template_name="learnCards.html")),
        name="learnCards",
    ),
    path(
        "slides/",
        login_required(SampleView.as_view(template_name="slidesCreator.html")),
        name="slides",
    ),
    # path(
    #     "upload_pdf/",
    #     UploadPDF.as_view(),
    #     name="upload_pdf",
    # ),
    path("upload", postPDF, name="file-upload"),
    path("endpoint", getExam, name="get-exam"),
    path("summaryEndpoint", getSummary, name="get-summary"),
    path("learnCardsEndpoint", getLearnCards, name="get-cards"),
    path("slidesEndpoint", getSlides, name="get-slides"),
    path("retryExam", retryExam, name="retry-exam"),
    # path(
    #     "learningSuggestionsEndpoint", learningSuggestions, name="learning-suggestions"
    # ),
    path("retrySummary", retrySummary, name="retry-summary"),
    path("retrySlides", retrySlides, name="retry-slides"),
    path("retryLeanCards", retryLeanCards, name="retry-learn-cards"),
    path("downloadPresentation", download_presentation, name="download_presentation"),
]
