from django import forms

from .models import Crossword


class CrosswordCreateForm(forms.ModelForm):
    SIZE_CHOICES = [(5, "5 x 5"), (7, "7 x 7"), (15, "15 x 15"), (19, "19 x 19")]

    size = forms.TypedChoiceField(
        choices=SIZE_CHOICES, coerce=int, label="Grid size"
    )

    class Meta:
        model = Crossword
        fields = ["requires_rotational_symmetry"]

    def save(self, commit=True):
        crossword = super().save(commit=False)
        size = self.cleaned_data["size"]
        crossword.num_rows = size
        crossword.num_cols = size
        crossword.cells = [""] * (size * size)
        crossword.blocked_out_squares = []
        if commit:
            crossword.save()
        return crossword
