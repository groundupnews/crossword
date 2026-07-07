"""
Nathan wrote this code by hand. Claude made an improvement (adding a tie-breaker, the mean, to the words_freedom result).
It fetches the best words (answers) for a given slot (using the words_freedom method).
"""

from fnmatch import fnmatch


class Slot:
    def _len_across(self):
        len = 1
        for i in range(self.start + 1, self.start + self.grid.cols):
            if i % self.grid.cols == 0 or self.grid.cells[i] == "#":
                break
            len += 1
        return len

    def _len_down(self):
        len = 1
        for i in range(
            self.start + self.grid.cols, self.grid.rows * self.grid.cols, self.grid.cols
        ):
            if self.grid.cells[i] == "#":
                break
            len += 1
        return len

    def _set_cells(self):
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
        s = f"{self.id}{self.dir}: [{self.row}, {self.col}] ({self.start}"
        step = 1
        if self.dir == "D":
            step = self.grid.cols
        for i in range(self.start + step, self.start + len(self) * step, step):
            s += " " + str(i)
        s += f") [{len(self)}]"
        return s

    def intersections(self):
        result = []
        dir = "A" if self.dir == "D" else "D"
        for cell in self.cells:
            slot = self.grid.slot_for_cell(dir, cell)
            if slot:
                result.append(slot)
        return result

    def intersecting_cell_index(self, intersection):
        for i in range(len(intersection.cells)):
            for j in range(len(self.cells)):
                if intersection.cells[i] == self.cells[j]:
                    return (i, j)
        return (-1, -1)

    def glob(self):
        glob = [" "] * len(self)
        j = 0
        for i in self.cells:
            letter = self.grid.cells[i]
            glob[j] = "?" if letter == "-" else letter
            j += 1
        return "".join(glob)

    def words(self):
        glob = self.glob()
        words = self.grid.words
        result = [w for w in words if fnmatch(w, glob)]
        return result

    def words_freedom(self):
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
    words = []

    def __init__(self, string: str, words=None):
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
        assert r >= 0 and r < self.rows and c >= 0 and c < self.cols
        return r * self.cols + c

    def __str__(self):
        result = ""
        for r in range(self.rows):
            for c in range(self.cols):
                result += self.cells[self._I(r, c)]
            result += "\n"
        return result[:-1]

    def calc_slots(self):

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
        for slot in self.slots:
            if slot.dir == dir and cell in slot.cells:
                return slot
        return None
