"""Tiles of any rectangle smaller than the grid (app 0.4.32, firmware 0.19.0): "3x2", "2x3" and the rest besides the
five names, set with a tile's handles in the editor and sent only to a screen that said its grid takes them."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'screen_manager/app'))
from core import Grid, apply_tile_event, event_size, span_of, span_offered, validate_layout  # noqa: E402
from page_layout import LayoutError, footprint_size  # noqa: E402


def layout(size, slot=0):
    return {'title': 'Home', 'tiles': [{'entity': 'light.kitchen', 'name': '', 'slot': slot, 'options': {'size': size}}]}


class Spans(unittest.TestCase):
    def test_a_span_is_every_rectangle_smaller_than_the_grid_that_no_name_says(self):
        self.assertEqual(span_of('3x2'), (3, 2))
        self.assertIsNone(span_of('square'))
        self.assertIsNone(span_of('10x2'))
        grid = Grid(3, 3)
        self.assertTrue(span_offered(3, 2, grid) and span_offered(1, 3, grid))
        self.assertFalse(span_offered(3, 3, grid))  # the whole grid is "full"
        self.assertFalse(span_offered(2, 2, grid))  # square
        self.assertFalse(span_offered(4, 1, grid))  # wider than the grid

    def test_the_layout_takes_a_span_where_it_fits_and_refuses_it_elsewhere(self):
        grid = Grid(3, 3)
        self.assertEqual(validate_layout(layout('3x2'), grid=grid)['tiles'][0]['options']['size'], '3x2')
        with self.assertRaises(ValueError):
            validate_layout(layout('3x2', slot=1), grid=grid)   # it would pass the right edge
        with self.assertRaises(ValueError):
            validate_layout(layout('2x2'), grid=grid)            # a name says that one
        with self.assertRaises(ValueError):
            validate_layout(layout('3x3'), grid=grid)            # the whole page is "full"
        with self.assertRaises(ValueError):
            validate_layout(layout('4x2'), grid=grid)            # wider than the grid

    def test_a_rectangle_reads_as_its_name_or_its_span(self):
        grid = Grid(4, 4)
        self.assertEqual(footprint_size(2, 2, grid), 'square')
        self.assertEqual(footprint_size(4, 4, grid), 'full')
        self.assertEqual(footprint_size(3, 2, grid), '3x2')
        self.assertEqual(footprint_size(2, 3, grid, '2x3'), '2x3')
        with self.assertRaises(LayoutError):
            footprint_size(3, 2, grid, '2x3')                     # the presentation says another rectangle
        with self.assertRaises(LayoutError):
            footprint_size(5, 1, grid)                            # wider than the grid

    def test_an_event_names_a_size_as_columns_x_rows(self):
        grid = Grid(2, 3)
        self.assertEqual(event_size('1x3', grid), '1x3')
        self.assertEqual(event_size('1 x 3', grid), '1x3')
        self.assertEqual(event_size('2x3', grid), 'full')      # the whole grid
        self.assertEqual(event_size('2x2', grid), 'square')
        self.assertEqual(event_size('wide', Grid(1, 4)), 'wide')  # a name stays a name; placing it checks where it goes
        for wrong in ('3x1', '9x9', 'huge'):
            with self.subTest(wrong), self.assertRaises(ValueError) as caught:
                event_size(wrong, grid)
            self.assertIn('1x3', str(caught.exception))          # it names what the screen does take

    def test_an_event_puts_a_span_on_the_screen_and_refuses_one_that_does_not_fit(self):
        grid = Grid(2, 3)
        layout = {'title': '', 'tiles': []}
        added = apply_tile_event(layout, 'add', {'entity': 'climate.hall', 'size': '1x3', 'page': 1, 'column': 'right'}, grid=grid)
        self.assertEqual(added['tiles'][0]['options']['size'], '1x3')
        self.assertEqual(added['tiles'][0]['slot'], 1)
        full = apply_tile_event(layout, 'add', {'entity': 'fan.hall', 'size': '2x3', 'page': 2}, grid=grid)
        self.assertEqual(full['tiles'][0]['options']['size'], 'full')
        with self.assertRaises(ValueError):
            apply_tile_event(layout, 'add', {'entity': 'switch.hall', 'size': '3x1', 'page': 1}, grid=grid)


if __name__ == '__main__':
    unittest.main()
