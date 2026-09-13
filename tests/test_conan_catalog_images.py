import unittest

from database import SessionLocal
from seed_data import ATTACHED_MANGA_CATALOG, CONAN_COVER_IMAGES


class ConanCatalogImageTests(unittest.TestCase):
    def test_conan_titles_have_unique_cover_urls(self):
        urls = [item["cover_image"] for item in ATTACHED_MANGA_CATALOG]
        self.assertEqual(len(urls), len(set(urls)))

    def test_every_conan_volume_has_a_defined_cover(self):
        titles = {item["title"] for item in ATTACHED_MANGA_CATALOG}
        for title in titles:
            self.assertIn(title, CONAN_COVER_IMAGES)
            self.assertTrue(CONAN_COVER_IMAGES[title].startswith("/static/"))


if __name__ == "__main__":
    unittest.main()
