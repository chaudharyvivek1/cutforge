"""§11.7, FR-10 — the export is a translation, and a round trip proves it."""
import unittest

import compiler as C
import otio_export as O


class TestExport(unittest.TestCase):
    def setUp(self):
        self.ir = C.appendix_a_ir()
        self.doc = O.export(self.ir)

    def test_it_is_an_otio_timeline(self):
        self.assertEqual(self.doc["OTIO_SCHEMA"], "Timeline.1")
        self.assertEqual(self.doc["tracks"]["OTIO_SCHEMA"], "Stack.1")

    def test_every_track_survives(self):
        back = O.read_back(self.doc)
        self.assertEqual(set(back), {"V1"})

    def test_every_clip_survives_with_its_duration(self):
        back = O.read_back(self.doc)
        clips = [c for c in back["V1"] if c["kind"] == "clip"]
        self.assertEqual(len(clips), 5)
        self.assertEqual([c["frames"] for c in clips], [311, 265, 194, 331, 296])

    def test_assets_survive(self):
        back = O.read_back(self.doc)
        self.assertEqual([c["asset"] for c in back["V1"]],
                         ["ast_a91", "ast_b07", "ast_c13", "ast_d22", "ast_a91"])

    def test_a_gap_survives_as_a_gap(self):
        self.ir["sequence"]["tracks"][0]["items"].append(
            {"kind": "gap", "id": "g1", "record": {"in": 1349, "out": 1373}})
        back = O.read_back(O.export(self.ir))
        self.assertEqual(back["V1"][-1]["kind"], "gap")
        self.assertEqual(back["V1"][-1]["frames"], 24)

    def test_the_ir_schema_is_recorded(self):
        self.assertEqual(self.doc["metadata"]["ir_schema"], self.ir["schema"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
