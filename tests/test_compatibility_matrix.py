# -*- coding: utf-8 -*-
"""Validate compatibility_matrix.yaml structure and release-gate requirements."""

import os
import unittest

from tests.matrix_loader import (
    get_android_entries,
    get_ios_entries,
    load_matrix,
    validate_matrix,
    validate_release_readiness,
    validate_docs_consistency,
)

_DOCS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'compatibility-matrix.md'
)


class TestCompatibilityMatrixSchema(unittest.TestCase):
    """Matrix YAML must be structurally valid for release gate."""

    @classmethod
    def setUpClass(cls):
        cls.matrix = load_matrix()

    def test_matrix_loads_without_errors(self):
        errors = validate_matrix(self.matrix)
        self.assertEqual(errors, [], f'Matrix validation errors: {errors}')

    def test_release_readiness_full_gate(self):
        errors = validate_release_readiness(self.matrix)
        self.assertEqual(errors, [], f'Release readiness errors: {errors}')

    def test_docs_consistency_with_matrix(self):
        errors = validate_docs_consistency(self.matrix)
        self.assertEqual(errors, [], f'Docs consistency errors: {errors}')

    def test_p0_android_covers_play_2026_baseline(self):
        apis = {e['api'] for e in get_android_entries('P0', self.matrix)}
        self.assertIn(35, apis, 'P0 must include API 35 (Google Play 2026 target)')
        self.assertIn(36, apis, 'P0 must include API 36 (Android 16)')

    def test_p0_ios_covers_2026_mainline(self):
        versions = {str(e['version']) for e in get_ios_entries('P0', self.matrix)}
        self.assertIn('18', versions)
        self.assertIn('26', versions)

    def test_p3_android_page_flip_only(self):
        for entry in get_android_entries('P3', self.matrix):
            self.assertEqual(
                entry.get('fps_strategy'),
                'page_flip_only',
                f"API {entry['api']} P3 must use page_flip_only",
            )

    def test_surface_fixtures_match_package(self):
        pkg = 'com.test.game'
        for group in self.matrix['surface_fixtures'].values():
            for surface in group['surfaces']:
                self.assertIn(pkg, surface)

    def test_docs_file_exists_and_references_p0_apis(self):
        self.assertTrue(os.path.isfile(_DOCS_PATH), 'docs/compatibility-matrix.md missing')
        with open(_DOCS_PATH, encoding='utf-8') as fh:
            content = fh.read()
        for api in (33, 34, 35, 36):
            self.assertRegex(
                content,
                rf'\b{api}\b',
                f'docs must mention Android API {api}',
            )
        self.assertIn('P0', content)
        self.assertIn('iOS 26', content)

    def test_docs_release_gate_matches_matrix(self):
        with open(_DOCS_PATH, encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn(self.matrix['release_gate'], content)


class TestMatrixTierConsistency(unittest.TestCase):
    """Tier definitions must not overlap or contradict."""

    def test_android_api_ranges_monotonic_by_priority(self):
        matrix = load_matrix()
        p0_min = min(e['api'] for e in matrix['android']['P0']['entries'])
        p3_max = max(e['api'] for e in matrix['android']['P3']['entries'])
        self.assertGreater(p0_min, p3_max)

    def test_no_duplicate_android_p0_api(self):
        entries = get_android_entries('P0')
        apis = [e['api'] for e in entries]
        self.assertEqual(len(apis), len(set(apis)))


if __name__ == '__main__':
    unittest.main()
