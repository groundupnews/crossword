from django.contrib import admin

from .models import Clue, Crossword, Entry, Word


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("text", "date_added", "date_modified")
    search_fields = ("text",)
    ordering = ("text",)


@admin.register(Clue)
class ClueAdmin(admin.ModelAdmin):
    list_display = ("text", "clue", "date_added", "date_modified")
    search_fields = ("text__text", "clue")
    list_select_related = ("text",)


@admin.register(Crossword)
class CrosswordAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "num_rows",
        "num_cols",
        "published",
        "date_modified",
    )
    search_fields = ("name", "description")
    readonly_fields = ("date_added", "date_modified")
    view_on_site = True


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("crossword", "number", "direction", "word", "clue")
    list_filter = ("direction",)
    search_fields = ("word__text",)
    list_select_related = ("crossword", "word", "clue")
