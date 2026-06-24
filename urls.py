from django.urls import path

from . import views

urlpatterns = [
    path("new/", views.CrosswordCreateView.as_view(), name="crossword_add"),
    path("", views.CrosswordSelectView.as_view(), name="crossword_select"),
    path("<int:pk>/solve/", views.crossword_solve, name="crossword_solve"),
    path("<int:pk>/check/", views.crossword_check, name="crossword_check"),
    path("<int:pk>/edit/", views.crossword_edit, name="crossword_edit"),
    path("<int:pk>/save/", views.crossword_save, name="crossword_save"),
    path("<int:pk>/fetch-answers/", views.fetch_answers, name="fetch_answers"),
    path("<int:pk>/fetch-clues/", views.fetch_clues, name="fetch_clues"),
    path("<int:pk>/xd/", views.crossword_xd, name="crossword_xd"),
    path("<int:pk>/delete/", views.crossword_delete, name="crossword_delete"),
    path("import/", views.crossword_import, name="crossword_import"),
]
