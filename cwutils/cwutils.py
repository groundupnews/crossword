import sqlite3
from fnmatch import fnmatch


class Dictionary:
    words = []

    def __init__(self):
        if len(self.words) == 0:
            conn = sqlite3.connect("db.sqlite3")
            cur = conn.cursor()
            cur.execute("SELECT text FROM crossword_word")
            self.words = [row[0] for row in cur.fetchall()]
            conn.close()


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
        words = self.grid.dictionary.words
        result = [w for w in words if fnmatch(w, glob)]
        return result

    def words_freedom(self):
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
                    words = [
                        w for w in self.grid.dictionary.words if len(w) == len(glob)
                    ]
                    matching_words = [w for w in words if fnmatch(w, glob)]
                    glob_dict[glob] = len(matching_words)
                result[word].append(glob_dict[glob])
        arr = list(result.items())
        arr = sorted(arr, key=lambda tpl: min(tpl[1]), reverse=True)
        return arr


class Grid:
    dictionary = Dictionary()

    def __init__(self, string: str):
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
            nonlocal result
            inc_slot_num = True
            result.append(Slot(grid=self, dir=dir, id=slot_num, row=r, col=c))

        inc_slot_num = False
        result = []
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
        return result

    def slot_for_cell(self, dir, cell):
        for slot in self.slots:
            if slot.dir == dir and cell in slot.cells:
                return slot
        return None
