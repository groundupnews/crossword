import json
import random
from datetime import datetime

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView

from . import grid
from .forms import CrosswordCreateForm
from .models import Clue, Crossword, Entry, Word
from .xd import parse_xd, render_xd, save_crossword_from_xd

# Nathan not to self: I've reviewed this but not closely.

PERM = "crossword.can_generate_crosswords"


class CrosswordCreateView(PermissionRequiredMixin, CreateView):
    permission_required = PERM
    """Add a new crossword.

    Presents a two-field form (grid size, NYT rules); the form creates a
    blank crossword with empty `cells` and `blocked_out_squares`. Redirects
    to the edit screen for the newly created crossword.
    """

    model = Crossword
    form_class = CrosswordCreateForm
    template_name = "crossword/add.html"

    def form_valid(self, form):
        self.object = form.save()
        return redirect("crossword_edit", pk=self.object.pk)


class CrosswordSelectView(ListView):
    """List crosswords.

    Generators see all crosswords. Everyone else sees only published ones.
    """

    model = Crossword
    template_name = "crossword/select.html"
    context_object_name = "crosswords"
    ordering = ["-date_modified"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.has_perm(PERM):
            qs = qs.published()
        return qs


@permission_required(PERM)
def crossword_edit(request, pk):
    """Render the editable crossword grid for the given crossword."""
    crossword = get_object_or_404(Crossword, pk=pk)
    clues = {
        f"{e.number}{e.direction}": e.clue.clue
        for e in crossword.entries.select_related("clue")
        if e.clue
    }
    return render(
        request,
        "crossword/edit.html",
        {"crossword": crossword, "clues": clues},
    )


@require_POST
def crossword_check(request, pk):
    """Check the solver's answers against the stored grid.

    Accepts JSON: mode ('letter'|'word'|'crossword'), cells (flat list),
    cursor (cell index), direction ('A'|'D').  Returns per-cell results
    without revealing the correct letters.
    """
    crossword = get_object_or_404(Crossword, pk=pk)
    if not crossword.is_published() and not request.user.has_perm(PERM):
        raise Http404

    payload = json.loads(request.body)
    mode = payload.get("mode")
    user_cells = payload.get("cells", [])
    cursor = payload.get("cursor", 0)
    direction = payload.get("direction", Entry.ACROSS)

    answer = crossword.cells
    if len(user_cells) != len(answer):
        return JsonResponse({"error": "cell count mismatch"}, status=400)

    blocked = set(crossword.blocked_out_squares)

    def check_cell(i):
        return {"index": i, "correct": bool(user_cells[i] and user_cells[i] == answer[i])}

    if mode == "letter":
        results = [] if cursor in blocked else [check_cell(cursor)]
    elif mode == "word":
        all_slots = grid.slots(
            crossword.num_rows, crossword.num_cols,
            crossword.blocked_out_squares, answer,
        )
        slot = next(
            (s for s in all_slots if s.direction == direction and cursor in s.indices),
            None,
        )
        results = [check_cell(i) for i in slot.indices] if slot else []
    elif mode == "crossword":
        results = [check_cell(i) for i in range(len(answer)) if i not in blocked]
    else:
        return JsonResponse({"error": "invalid mode"}, status=400)

    return JsonResponse({"results": results})


def crossword_solve(request, pk):
    """Detail/solver view.

    Available to everyone for published crosswords; generators can preview
    unpublished ones. Non-generators get a 404 for unpublished crosswords.
    """
    crossword = get_object_or_404(Crossword, pk=pk)
    if not crossword.is_published() and not request.user.has_perm(PERM):
        raise Http404
    clues = {
        f"{e.number}{e.direction}": e.clue.clue
        for e in crossword.entries.select_related("clue")
        if e.clue
    }
    return render(request, "crossword/detail.html", {"crossword": crossword, "clues": clues})


@permission_required(PERM)
@require_POST
def crossword_save(request, pk):
    """Save the grid for the given crossword.

    Accepts a JSON body: cells, blocked_out_squares, name, description,
    clues ({"1A": "clue text", ...}). cells is the source of truth and is
    always saved. Entry rows are derived from the complete slots; partial
    slots touch nothing but cells.
    """
    crossword = get_object_or_404(Crossword, pk=pk)
    payload = json.loads(request.body)

    with transaction.atomic():
        crossword.cells = payload["cells"]
        crossword.blocked_out_squares = payload["blocked_out_squares"]
        crossword.name = payload.get("name", "")
        crossword.description = payload.get("description", "")
        crossword.authors = payload.get("authors", "")
        crossword.editors = payload.get("editors", "")
        crossword.copyright = payload.get("copyright", "")
        published_str = payload.get("published") or ""
        if published_str:
            dt = datetime.fromisoformat(published_str)
            crossword.published = dt if timezone.is_aware(dt) else timezone.make_aware(dt)
        else:
            crossword.published = None
        crossword.save()

        clues = payload.get("clues", {})
        cells = crossword.cells
        complete = [
            s
            for s in grid.slots(
                crossword.num_rows,
                crossword.num_cols,
                crossword.blocked_out_squares,
                cells,
            )
            if s.is_complete(cells)
        ]

        # Reconcile: drop entries no longer backed by a complete slot.
        keep = {(s.number, s.direction) for s in complete}
        keep_across = {n for n, d in keep if d == Entry.ACROSS}
        keep_down = {n for n, d in keep if d == Entry.DOWN}
        crossword.entries.exclude(
            Q(direction=Entry.ACROSS, number__in=keep_across)
            | Q(direction=Entry.DOWN, number__in=keep_down)
        ).delete()

        for slot in complete:
            word, _ = Word.objects.get_or_create(text=slot.letters(cells))

            clue_obj = None
            clue_text = clues.get(f"{slot.number}{slot.direction}")
            if clue_text:
                clue_obj, _ = Clue.objects.get_or_create(text=word, clue=clue_text)

            Entry.objects.update_or_create(
                crossword=crossword,
                number=slot.number,
                direction=slot.direction,
                defaults={"word": word, "clue": clue_obj},
            )

    return JsonResponse({"status": "ok"})


@permission_required(PERM)
def fetch_answers(request, pk):
    """Return up to 10 Word matches for the current slot pattern.

    The client sends `pattern`: filled positions as their letter, blanks as
    "?". Matching uses SQLite GLOB, which enforces length and fixed letters.
    Returns up to 20 matches.
    """
    pattern = request.GET.get("pattern", "")
    texts = []
    if pattern:
        table = Word._meta.db_table
        rows = Word.objects.raw(
            f"SELECT id, text FROM {table} WHERE text GLOB %s", [pattern]
        )
        texts = [w.text for w in rows]
    if len(texts) > 20:
        texts = random.sample(texts, 20)
    return JsonResponse({"answers": sorted(texts)})


@permission_required(PERM)
def fetch_clues(request, pk):
    """Return up to 10 clue texts for the current complete word.

    The client sends `word`. If empty (slot incomplete), the result is empty.
    """
    word_text = request.GET.get("word", "")
    clues = []
    if word_text:
        clues = list(
            Clue.objects.filter(text__text=word_text).values_list("clue", flat=True)
        )
    if len(clues) > 10:
        clues = random.sample(clues, 10)
    return JsonResponse({"clues": sorted(clues)})


@permission_required(PERM)
@require_POST
def crossword_delete(request, pk):
    crossword = get_object_or_404(Crossword, pk=pk)
    crossword.delete()
    return redirect("crossword_select")


def crossword_xd(request, pk):
    """Return the crossword as a downloadable .xd file."""
    crossword = get_object_or_404(Crossword, pk=pk)
    filename = (crossword.name or "crossword").replace('"', "")
    response = HttpResponse(render_xd(crossword), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xd"'
    return response


@permission_required(PERM)
@require_POST
def crossword_import(request):
    """Create or replace a crossword from an uploaded .xd file.

    Accepts a plain-text .xd body. Returns JSON with a redirect URL on
    success, or an error message on failure.
    """
    try:
        data = parse_xd(request.body.decode("utf-8"))
        if not data["size"]["rows"]:
            raise ValueError("empty grid")
    except Exception:
        return JsonResponse({"error": "Invalid .xd file"}, status=400)

    crossword = save_crossword_from_xd(data, replace=True)
    return JsonResponse({"redirect": reverse("crossword_edit", args=[crossword.pk])})
