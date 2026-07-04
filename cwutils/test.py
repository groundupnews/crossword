import unittest
from cwutils import Grid, Slot


class TestGrid(unittest.TestCase):
    cw1 = """
#BIB#
BIERS
ON#IS
OGLED
#OOF#
"""

    cw2 = """
#---#
-----
--#--
-----
#---#
"""

    def setUp(self):
        self.grid1 = Grid(self.cw1)
        self.grid2 = Grid(self.cw2)

    def test_grid(self):
        self.assertEqual(self.grid1.rows, 5)
        self.assertEqual(self.grid1.cols, 5)
        self.assertGreater(len(self.grid1.dictionary.words), 1000)
        self.assertEqual(self.grid2.rows, 5)
        self.assertEqual(self.grid2.cols, 5)
        self.assertEqual(self.grid1.dictionary.words, self.grid2.dictionary.words)
        self.assertNotEqual(self.grid1.slots, self.grid2.slots)

    def test_slots(self):
        self.assertEqual(self.grid1.slots[0].id, 1)
        self.assertEqual(self.grid1.slots[0].dir, "A")
        self.assertEqual(self.grid1.slots[0].row, 0)
        self.assertEqual(self.grid1.slots[0].col, 1)
        self.assertEqual(self.grid1.slots[0].start, 1)
        self.assertEqual(len(self.grid1.slots[0]), 3)

        self.assertEqual(self.grid1.slots[1].id, 4)
        self.assertEqual(self.grid1.slots[1].dir, "A")
        self.assertEqual(self.grid1.slots[1].row, 1)
        self.assertEqual(self.grid1.slots[1].col, 0)
        self.assertEqual(self.grid1.slots[1].start, 5)
        self.assertEqual(len(self.grid1.slots[1]), 5)

        self.assertEqual(self.grid1.slots[2].id, 6)
        self.assertEqual(self.grid1.slots[2].dir, "A")
        self.assertEqual(self.grid1.slots[2].row, 2)
        self.assertEqual(self.grid1.slots[2].col, 0)
        self.assertEqual(self.grid1.slots[2].start, 10)
        self.assertEqual(len(self.grid1.slots[2]), 2)

        self.assertEqual(self.grid1.slots[3].id, 7)
        self.assertEqual(self.grid1.slots[3].dir, "A")
        self.assertEqual(self.grid1.slots[3].row, 2)
        self.assertEqual(self.grid1.slots[3].col, 3)
        self.assertEqual(self.grid1.slots[3].start, 13)
        self.assertEqual(len(self.grid1.slots[3]), 2)

        self.assertEqual(self.grid1.slots[4].id, 8)
        self.assertEqual(self.grid1.slots[4].dir, "A")
        self.assertEqual(self.grid1.slots[4].row, 3)
        self.assertEqual(self.grid1.slots[4].col, 0)
        self.assertEqual(self.grid1.slots[4].start, 15)
        self.assertEqual(len(self.grid1.slots[4]), 5)

        self.assertEqual(self.grid1.slots[5].id, 10)
        self.assertEqual(self.grid1.slots[5].dir, "A")
        self.assertEqual(self.grid1.slots[5].row, 4)
        self.assertEqual(self.grid1.slots[5].col, 1)
        self.assertEqual(self.grid1.slots[5].start, 21)
        self.assertEqual(len(self.grid1.slots[5]), 3)

        self.assertEqual(self.grid1.slots[6].id, 1)
        self.assertEqual(self.grid1.slots[6].dir, "D")
        self.assertEqual(self.grid1.slots[6].row, 0)
        self.assertEqual(self.grid1.slots[6].col, 1)
        self.assertEqual(self.grid1.slots[6].start, 1)
        self.assertEqual(len(self.grid1.slots[6]), 5)

        self.assertEqual(self.grid1.slots[7].id, 2)
        self.assertEqual(self.grid1.slots[7].dir, "D")
        self.assertEqual(self.grid1.slots[7].row, 0)
        self.assertEqual(self.grid1.slots[7].col, 2)
        self.assertEqual(self.grid1.slots[7].start, 2)
        self.assertEqual(len(self.grid1.slots[7]), 2)

        self.assertEqual(self.grid1.slots[8].id, 3)
        self.assertEqual(self.grid1.slots[8].dir, "D")
        self.assertEqual(self.grid1.slots[8].row, 0)
        self.assertEqual(self.grid1.slots[8].col, 3)
        self.assertEqual(self.grid1.slots[8].start, 3)
        self.assertEqual(len(self.grid1.slots[8]), 5)

        self.assertEqual(self.grid1.slots[9].id, 4)
        self.assertEqual(self.grid1.slots[9].dir, "D")
        self.assertEqual(self.grid1.slots[9].row, 1)
        self.assertEqual(self.grid1.slots[9].col, 0)
        self.assertEqual(self.grid1.slots[9].start, 5)
        self.assertEqual(len(self.grid1.slots[9]), 3)

        self.assertEqual(self.grid1.slots[10].id, 5)
        self.assertEqual(self.grid1.slots[10].dir, "D")
        self.assertEqual(self.grid1.slots[10].row, 1)
        self.assertEqual(self.grid1.slots[10].col, 4)
        self.assertEqual(self.grid1.slots[10].start, 9)
        self.assertEqual(len(self.grid1.slots[10]), 3)

        self.assertEqual(self.grid1.slots[11].id, 9)
        self.assertEqual(self.grid1.slots[11].dir, "D")
        self.assertEqual(self.grid1.slots[11].row, 3)
        self.assertEqual(self.grid1.slots[11].col, 2)
        self.assertEqual(self.grid1.slots[11].start, 17)
        self.assertEqual(len(self.grid1.slots[11]), 2)

        self.assertEqual(len(self.grid1.slots), len(self.grid2.slots))

        tuples = zip(self.grid1.slots, self.grid2.slots)
        for t in tuples:
            self.assertEqual(t[0].dir, t[1].dir)
            self.assertEqual(t[0].id, t[1].id)
            self.assertEqual(len(t[0]), len(t[1]))
            self.assertEqual(t[0].cells, t[1].cells)

    def test_intersection_slots(self):
        intersections = self.grid1.slots[0].intersections()
        self.assertEqual(len(intersections), 3)
        self.assertEqual(intersections[0].dir, "D")
        self.assertEqual(intersections[1].dir, "D")
        self.assertEqual(intersections[2].dir, "D")
        self.assertEqual(intersections[0].id, 1)
        self.assertEqual(intersections[1].id, 2)
        self.assertEqual(intersections[2].id, 3)
        intersections = self.grid1.slots[3].intersections()
        self.assertEqual(len(intersections), 2)
        i = self.grid1.slots[3].intersecting_cell_index(intersections[0])
        self.assertEqual(i, (2, 0))

        i = self.grid1.slots[3].intersecting_cell_index(intersections[1])
        self.assertEqual(i, (1, 1))


class TestMatching(unittest.TestCase):
    cw1 = """
#---#
--A-Y
--#--
-----
#---#
"""

    def setUp(self):
        self.grid1 = Grid(self.cw1)

    def test_glob(self):
        slot = self.grid1.slot_for_cell("A", 5)
        self.assertEqual(type(slot), Slot)
        if slot:
            glob = slot.glob()
            self.assertEqual(glob, "??A?Y")
        slot = self.grid1.slot_for_cell("D", 2)
        self.assertEqual(type(slot), Slot)
        if slot:
            glob = slot.glob()
            self.assertEqual(glob, "?A")

    def test_match(self):
        slot = self.grid1.slot_for_cell("A", 5)
        if slot:
            words = slot.words()
            self.assertGreater(len(words), 30)
        slot = self.grid1.slot_for_cell("D", 2)
        if slot:
            words = slot.words()
            self.assertGreater(len(words), 15)

    def test_words_freedom(self):
        print(self.grid1.slots[1].words_freedom())


if __name__ == "__main__":
    unittest.main()
