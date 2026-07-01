from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Claude: Why use a regex validator instead of Python's isupper?
# Claude response: Two reasons. (1) isupper() allows digits — "AB3".isupper() is True
# because all *cased* characters are uppercase. The regex ^[A-Z]+$ strictly permits
# only A-Z letters. (2) Django validators must be callable objects that raise
# ValidationError — you can't pass isupper directly to a field's validators list.
uppercase_az = RegexValidator(r"^[A-Z]+$", "Text must be uppercase A-Z only.")


class Word(models.Model):
    # Claude: Why is the max_length set to 64?
    # Claude response: It's a safe ceiling for crossword answers. The largest standard
    # grids are 21x21 (NYT Sunday), so the longest possible answer is 21 letters. 64
    # gives ample headroom without being unlimited. 32 would also work — 64 is somewhat
    # arbitrary but a common power-of-two choice.
    text = models.CharField(max_length=64, unique=True, validators=[uppercase_az])
    source_crossword = models.ForeignKey(
        "Crossword",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sourced_words",
    )
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class Clue(models.Model):
    text = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="clues")
    clue = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["text", "clue"], name="unique_text_clue"),
        ]

    def __str__(self):
        return self.clue


def default_copyright():
    return f"(C) {timezone.now().year} GroundUp News"


class CrosswordQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published__isnull=False, published__lte=timezone.now())


class Crossword(models.Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    authors = models.CharField(max_length=200, blank=True)
    editors = models.CharField(max_length=200, blank=True)
    copyright = models.CharField(max_length=200, default=default_copyright)
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    published = models.DateTimeField(null=True, blank=True)
    num_rows = models.PositiveIntegerField()
    num_cols = models.PositiveIntegerField()
    blocked_out_squares = models.JSONField(default=list)
    cells = models.JSONField(default=list)
    requires_rotational_symmetry = models.BooleanField(default=True)

    objects = CrosswordQuerySet.as_manager()

    class Meta:
        permissions = [("can_generate_crosswords", "Can generate crosswords")]

    def get_absolute_url(self):
        return reverse("crossword_solve", args=[self.pk])

    def is_published(self):
        return self.published is not None and self.published <= timezone.now()

    def __str__(self):
        return self.name or f"Crossword {self.pk}"


# Claude: We are tring to achieve two things: (a) store the, perhaps
# unfinished, crossword clues and answers and (b) have a database of clues and
# answers to show the crossword setter. But it seems there is something less
# than ideal in the design because we're duplicating information in the
# Crossword.cells field and the Entry table below. Having said that it's not clear to me
# that a more normalised design would come with fewer problems.
#
# Claude response: The duplication is real but intentional and defensible.
# Crossword.cells is the canonical grid state — a flat list of letters needed to render
# the grid efficiently without joins. Entry is the semantic layer — it names which word
# occupies which slot and links to clues and the word database.
# A fully normalised design (deriving cell contents from Entry rows) would require
# reconstructing the grid from slot positions on every render, and makes partial/in-progress
# grids awkward (cells with letters but no committed Entry yet). The main risk with the
# current design is that cells and Entry rows drift out of sync — worth adding a
# validation method on Crossword that checks consistency, but not a reason to redesign.

class Entry(models.Model):
    ACROSS = "A"
    DOWN = "D"
    DIRECTION_CHOICES = [(ACROSS, "Across"), (DOWN, "Down")]

    crossword = models.ForeignKey(
        Crossword, on_delete=models.CASCADE, related_name="entries"
    )
    word = models.ForeignKey(Word, on_delete=models.PROTECT, related_name="entries")
    clue = models.ForeignKey(
        Clue, on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )
    number = models.PositiveIntegerField()
    direction = models.CharField(max_length=1, choices=DIRECTION_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["crossword", "number", "direction"],
                name="unique_crossword_number_direction",
            ),
        ]

    def __str__(self):
        return f"{self.number}{self.direction}: {self.word.text}"
