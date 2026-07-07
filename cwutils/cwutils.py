"""
Nathan wrote this code by hand. Claude made an improvement (adding a tie-breaker, the mean, to the words_freedom result).
It fetches the best words (answers) for a given slot (using the words_freedom method).
"""

from fnmatch import fnmatch


class Slot:
    """One across or down run in a Grid: its position, length, the flat
    cell indices it covers, and matching helpers against the grid's word
    list. Constructed by Grid.calc_slots(); not usually built directly."""

    def _len_across(self):
        """Counts cells rightward from self.start until the row wraps
        (i % cols == 0) or a block is hit. Runs of length 1 aren't
        filtered out here -- Grid.calc_slots() does that afterwards."""
        len = 1
        for i in range(self.start + 1, self.start + self.grid.cols):
            if i % self.grid.cols == 0 or self.grid.cells[i] == "#":
                break
            len += 1
        return len

    def _len_down(self):
        """Counts cells downward from self.start (stepping by a full row
        width) until the grid ends or a block is hit."""
        len = 1
        for i in range(
            self.start + self.grid.cols, self.grid.rows * self.grid.cols, self.grid.cols
        ):
            if self.grid.cells[i] == "#":
                break
            len += 1
        return len

    def _set_cells(self):
        """Populates self.cells with the flat indices of every cell in the
        slot, in reading order, stepping by 1 (across) or by the grid's
        column count (down)."""
        self.cells = []
        if self.dir == "A":
            step = 1
        else:
            step = self.grid.cols
        start = self.start
        end = self.start + step * len(self)
        for i in range(start, end, step):
            self.cells.append(i)

    def __init__(self, grid, dir, id, row, col):
        """Builds the slot starting at (row, col) in `grid`, running in
        direction `dir` ("A" or "D"); computes its length and cell indices
        immediately so every other method can assume they're ready."""
        self.grid = grid
        self.dir = dir
        self.id = id
        self.row = row
        self.col = col
        self.start = row * grid.cols + col
        if self.dir == "A":
            self._len = self._len_across()
        else:
            self._len = self._len_down()
        self._set_cells()
        self._intersections = []

    def __len__(self):
        return self._len

    def __str__(self):
        # Debug representation: id+direction, start cell, every subsequent
        # cell index in the run, then the length in brackets.
        s = f"{self.id}{self.dir}: [{self.row}, {self.col}] ({self.start}"
        step = 1
        if self.dir == "D":
            step = self.grid.cols
        for i in range(self.start + step, self.start + len(self) * step, step):
            s += " " + str(i)
        s += f") [{len(self)}]"
        return s

    def intersections(self):
        """The perpendicular slot crossing each of this slot's cells, in
        cell order (across slots return their crossing down slots, and
        vice versa). A cell with no real crossing slot -- e.g. it sits in
        an isolated single-cell run -- contributes nothing to the result,
        so the returned list can be shorter than this slot's length."""
        result = []
        dir = "A" if self.dir == "D" else "D"
        for cell in self.cells:
            slot = self.grid.slot_for_cell(dir, cell)
            if slot:
                result.append(slot)
        return result

    def intersecting_cell_index(self, intersection):
        """Finds the shared grid cell between this slot and `intersection`,
        returning (index within intersection.cells, index within
        self.cells), or (-1, -1) if they don't actually cross."""
        for i in range(len(intersection.cells)):
            for j in range(len(self.cells)):
                if intersection.cells[i] == self.cells[j]:
                    return (i, j)
        return (-1, -1)

    def glob(self):
        """The slot's current contents as an fnmatch pattern: filled cells
        become their letter, blank cells ("-") become the "?" wildcard."""
        glob = [" "] * len(self)
        j = 0
        for i in self.cells:
            letter = self.grid.cells[i]
            glob[j] = "?" if letter == "-" else letter
            j += 1
        return "".join(glob)

    def words(self):
        """Every word in the grid's word list matching this slot's current
        glob pattern (i.e. the right length and consistent with any
        letters already filled in)."""
        glob = self.glob()
        words = self.grid.words
        result = [w for w in words if fnmatch(w, glob)]
        return result

    def words_freedom(self):
        """Ranks this slot's candidate words (from words()) by how much
        freedom each leaves in its crossing slots, most promising first.

        For every candidate and every crossing slot that still has an
        unresolved (blank) intersecting cell, computes how many
        dictionary words of the right length could still fill that
        crossing if the candidate were placed -- already-filled crossings,
        and cells with no real crossing slot, are skipped entirely, so a
        candidate can end up with an empty score list. Results are
        cached per crossing pattern (glob_dict) since many candidates
        produce the same crossing pattern.

        Candidates are sorted by their worst (minimum) crossing score
        first, so a word that's fine everywhere except one badly
        constrained crossing loses to one that's evenly okay; the mean of
        all crossing scores breaks ties between candidates with the same
        worst score. A candidate with no scores at all (fully resolved
        slot, or no crossings exist) sorts by 0 for both, which just
        preserves words()' original order among such candidates.

        Returns a list of (word, scores) tuples. See fetch_algorirthm.md
        for the original pseudocode this replaced.
        """
        def min_no_error(lst):
            try:
                return min(lst)
            except ValueError:
                return 0

        glob_dict = {}
        self_words = self.words()
        self_glob = self.glob()
        intersections = self.intersections()
        result = {}
        for word in self_words:
            result[word] = []
        for word in self_words:
            for intersection in intersections:
                glob_list = list(intersection.glob())
                (i, j) = self.intersecting_cell_index(intersection)
                if self_glob[j] != "?":
                    continue
                glob_list[i] = word[j]
                glob = "".join(glob_list)
                if glob not in glob_dict:
                    words = [w for w in self.grid.words if len(w) == len(glob)]
                    matching_words = [w for w in words if fnmatch(w, glob)]
                    glob_dict[glob] = len(matching_words)
                result[word].append(glob_dict[glob])

        def mean(lst):
            return sum(lst) / len(lst) if lst else 0

        arr = list(result.items())
        arr = sorted(
            arr, key=lambda tpl: (min_no_error(tpl[1]), mean(tpl[1])), reverse=True
        )
        return arr


class Grid:
    """A crossword grid parsed from a plain-text layout, with its numbered
    Slots and (optionally) a word list to match candidates against."""

    words = []  # fallback when __init__ isn't given a word list

    def __init__(self, string: str, words=None):
        """Parses `string` (one grid row per line; "#" for a block, "-" for
        a blank white cell, A-Z for a filled cell) into a flat cell list,
        infers rows/cols from the line breaks and longest line, and
        computes the grid's numbered slots. `words` is the dictionary
        words() and words_freedom() will match candidates against."""
        if words:
            self.words = words
        self.cells = []
        rows = 0
        cols = 0
        max_cols = 0
        for c in string:
            if c == "#" or c == "-" or (c >= "A" and c <= "Z"):
                self.cells.append(c)
                cols += 1
            if c == "\n" and cols > 0:
                rows += 1
                if cols > max_cols:
                    max_cols = cols
                cols = 0
        self.rows = rows
        self.cols = max_cols
        self.slots = sorted(
            self.calc_slots(), key=lambda slot: f"{slot.dir}{slot.id:03}"
        )

    def _I(self, r: int, c: int):
        """Flat cell index for (row, col), asserting both are in bounds."""
        assert r >= 0 and r < self.rows and c >= 0 and c < self.cols
        return r * self.cols + c

    def __str__(self):
        # Renders the grid back out as one line of cell characters per row.
        result = ""
        for r in range(self.rows):
            for c in range(self.cols):
                result += self.cells[self._I(r, c)]
            result += "\n"
        return result[:-1]

    def calc_slots(self):
        """Builds every Slot in the grid, numbered and ordered the way
        Grid.__init__ expects (see the sort key there: across slots first,
        then down, each ordered by id).

        Scans cells in row-major order. A slot is started at a cell
        whenever there's no white cell immediately to its left (across) or
        above it (down) -- edges of the grid count as "no white cell"
        there, same as a block would. Unlike grid.py's slots(), this does
        not check whether the run is actually longer than one cell before
        creating the Slot; instead every candidate start gets a Slot
        object, and the final list comprehension drops any whose computed
        length (via Slot.__len__) turns out to be 1. A cell that starts
        both an across and a down slot shares one id between them, exactly
        as standard crossword numbering requires.
        """

        # Records that cell (r, c) starts a slot in direction `dir`, using
        # the number not yet incremented for this cell. inc_slot_num flags
        # that at least one slot started here, so the outer loop bumps
        # slot_num once per cell rather than once per direction.
        def push_slot(dir, r, c):
            nonlocal inc_slot_num
            nonlocal slots
            inc_slot_num = True
            slots.append(Slot(grid=self, dir=dir, id=slot_num, row=r, col=c))

        inc_slot_num = False
        slots = []
        slot_num = 1
        for r in range(self.rows):
            for c in range(self.cols):
                inc_slot_num = False
                cell = self.cells[self._I(r, c)]
                if cell == "#":
                    continue
                if c == 0:
                    push_slot("A", r, c)
                if r == 0:
                    push_slot("D", r, c)
                if c > 0 and self.cells[self._I(r, c - 1)] == "#":
                    push_slot("A", r, c)
                if r > 0 and self.cells[self._I(r - 1, c)] == "#":
                    push_slot("D", r, c)
                if inc_slot_num:
                    slot_num += 1
        return [slot for slot in slots if len(slot) > 1]

    def slot_for_cell(self, dir, cell):
        """The slot running in `dir` that covers flat cell index `cell`,
        or None if there isn't one (e.g. `cell` is blocked, or its run in
        that direction is only one cell long and so isn't a real slot)."""
        for slot in self.slots:
            if slot.dir == dir and cell in slot.cells:
                return slot
        return None
