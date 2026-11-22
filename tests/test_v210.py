"""v2.10: the encoded path, a provider adapter, and segment retention."""
import json
import tempfile
import unittest
from pathlib import Path

import analysis as An
import render_engine as RE
import renderer as R
import store as St

TMP = Path(tempfile.mkdtemp())
CHUNK_A = "[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_out]"
CHUNK_B = "[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_out]"


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NOTHING WAS ENCODED")
class TestEncodedChunks(unittest.TestCase):
    """§11.5 — a customer receives a file, not raw frames."""

    @classmethod
    def setUpClass(cls):
        cls.a = R.make_source(TMP / "a.mp4", pattern="testsrc2")
        cls.b = R.make_source(TMP / "b.mp4", pattern="smptebars")

    def test_a_segment_encodes_to_a_playable_file(self):
        out = RE.encode_segment(CHUNK_A, [self.a], TMP / "seg0.mp4")
        self.assertTrue(Path(out).exists())
        self.assertEqual(RE.frame_count(out), 24)

    def test_segments_join_without_dropping_a_frame(self):
        s0 = RE.encode_segment(CHUNK_A, [self.a], TMP / "s0.mp4")
        s1 = RE.encode_segment(CHUNK_B, [self.b], TMP / "s1.mp4")
        joined = RE.concat_encoded([s0, s1], TMP / "joined.mp4")
        self.assertEqual(RE.frame_count(joined), 48)

    def test_the_join_decodes_to_the_same_frame_count_as_the_parts(self):
        s0 = RE.encode_segment(CHUNK_A, [self.a], TMP / "j0.mp4")
        s1 = RE.encode_segment(CHUNK_B, [self.b], TMP / "j1.mp4")
        joined = RE.concat_encoded([s0, s1], TMP / "j.mp4")
        total = len(RE.decoded(joined))
        self.assertEqual(total, len(RE.decoded(s0)) + len(RE.decoded(s1)))

    def test_the_same_segment_encodes_identically_twice(self):
        # segment-level determinism is what a resume depends on
        one = RE.decoded(RE.encode_segment(CHUNK_A, [self.a], TMP / "d1.mp4"))
        two = RE.decoded(RE.encode_segment(CHUNK_A, [self.a], TMP / "d2.mp4"))
        self.assertEqual(one, two)

    def test_a_closed_gop_keeps_a_segment_independently_decodable(self):
        out = RE.encode_segment(CHUNK_B, [self.b], TMP / "gop.mp4")
        self.assertGreater(len(RE.decoded(out)), 0)


class TestProviderAdapter(unittest.TestCase):
    """§10.4 — seconds in, source frames out, nothing else."""

    def setUp(self):
        self.response = TMP / "provider.json"
        self.response.write_text(json.dumps({"words": [
            {"word": "hello", "start": 0.0, "end": 0.24},
            {"word": "world", "start": 0.24, "end": 0.60}]}))

    def test_seconds_become_source_frames(self):
        t = An.ProviderJSON(self.response, "25/1").run()
        self.assertEqual([w["start"] for w in t.words], [0, 6])
        self.assertEqual(t.words[1]["end"], 15)

    def test_the_rate_is_respected(self):
        t = An.ProviderJSON(self.response, "50/1").run()
        self.assertEqual(t.words[1]["start"], 12)

    def test_a_response_without_timings_is_rejected(self):
        bad = TMP / "bad.json"
        bad.write_text(json.dumps({"words": [{"word": "hello"}]}))
        with self.assertRaises(ValueError):
            An.ProviderJSON(bad, "25/1").run()

    def test_the_adapter_satisfies_the_transcriber_interface(self):
        self.assertIsInstance(An.ProviderJSON(self.response, "25/1"), An.Transcriber)


class TestSegmentRetention(unittest.TestCase):
    """§11.5 — segments are a cache, and a cache that never expires is a cost bug."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.store.register_asset("tnt_a", "prj_1", "z" * 64, 100, (24, 1), 48, 320, 180)
        self.asset = self.store.db.execute("SELECT id FROM assets").fetchone()["id"]
        for i in range(3):
            self.store.add_derivative("tnt_a", self.asset, "segment", 1000,
                                      f"seg:{i}", f"mem://{i}")

    def test_segments_count_against_storage(self):
        self.assertGreater(self.store.stored_bytes("tnt_a"), 3000)

    def test_expiry_removes_them_and_nothing_else(self):
        self.store.add_derivative("tnt_a", self.asset, "proxy", 500, "proxy:180", "mem://p")
        before = self.store.stored_bytes("tnt_a")
        removed = self.store.expire_segments(0)
        self.assertEqual(removed, 3)
        self.assertLess(self.store.stored_bytes("tnt_a"), before)
        self.assertIsNotNone(
            self.store.derivative("tnt_a", self.asset, "proxy", "proxy:180"))

    def test_a_recent_segment_survives_a_short_retention(self):
        removed = self.store.expire_segments(older_than_seconds=3600)
        self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
