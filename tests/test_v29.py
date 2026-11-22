"""v2.9: the chunked render §11.5 claims, a transcriber adapter, and VFR maps."""
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

import analysis as An
import ingest as In
import render_engine as RE
import renderer as R
import store as St

TMP = Path(tempfile.mkdtemp())

CHUNK_A = "[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_out]"
CHUNK_B = "[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_out]"
WHOLE = ("[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_a];\n"
         "[1:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_b];\n"
         "[v_a][v_b]concat=n=2:v=1:a=0[v_out]")


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NOTHING WAS RENDERED")
class TestChunkedRender(unittest.TestCase):
    """§11.5 — a chunked render must be frame-identical to a single pass."""

    @classmethod
    def setUpClass(cls):
        cls.a = R.make_source(TMP / "a.mp4", pattern="testsrc2")
        cls.b = R.make_source(TMP / "b.mp4", pattern="smptebars")

    def test_two_chunks_equal_one_pass(self):
        whole = R.render_bytes(WHOLE, [self.a, self.b])
        chunked = RE.concat([RE.render_segment(CHUNK_A, [self.a]),
                             RE.render_segment(CHUNK_B, [self.b])])
        self.assertEqual(chunked, whole)

    def test_the_hash_is_the_same_either_way(self):
        import hashlib
        whole = hashlib.sha256(R.render_bytes(WHOLE, [self.a, self.b])).hexdigest()
        chunked = hashlib.sha256(RE.concat([
            RE.render_segment(CHUNK_A, [self.a]),
            RE.render_segment(CHUNK_B, [self.b])])).hexdigest()
        self.assertEqual(chunked, whole)

    def test_a_resume_renders_only_the_missing_segments(self):
        store = St.Store(":memory:")
        store.register_asset("tnt_a", "prj_1", "x" * 64, 100, (24, 1), 48, 320, 180)
        asset = store.db.execute("SELECT id FROM assets").fetchone()["id"]
        publisher = RE.Publisher(store)
        segments = [(CHUNK_A, [self.a]), (CHUNK_B, [self.b])]

        frames, rendered, reused = RE.render_chunked(asset, segments, publisher)
        self.assertEqual((rendered, reused), (2, 0))

        # the second run is a resume: everything is already published
        again, rendered2, reused2 = RE.render_chunked(asset, segments, publisher)
        self.assertEqual((rendered2, reused2), (0, 2))
        self.assertEqual(again, frames)

    def test_a_partial_resume_renders_the_rest(self):
        store = St.Store(":memory:")
        store.register_asset("tnt_a", "prj_1", "y" * 64, 100, (24, 1), 48, 320, 180)
        asset = store.db.execute("SELECT id FROM assets").fetchone()["id"]
        publisher = RE.Publisher(store)
        publisher.publish(asset, 0, "seg", RE.render_segment(CHUNK_A, [self.a]))
        _, rendered, reused = RE.render_chunked(
            asset, [(CHUNK_A, [self.a]), (CHUNK_B, [self.b])], publisher)
        self.assertEqual((rendered, reused), (1, 1))


class TestSplitAtCuts(unittest.TestCase):
    """§11.5 — a boundary no transition spans is the only safe split."""

    def test_every_cut_is_a_split_point(self):
        self.assertEqual(RE.split_at_cuts(3), [(0, 1), (1, 2), (2, 3)])

    def test_a_transition_is_never_split(self):
        # the transition joins clips 1 and 2, so position 2 is not a boundary;
        # 1 and 3 still are, and clips 1-2 stay together
        self.assertEqual(RE.split_at_cuts(4, transitions=[(1, 2)]),
                         [(0, 1), (1, 3), (3, 4)])

    def test_a_fully_spanned_timeline_is_one_segment(self):
        self.assertEqual(RE.split_at_cuts(2, transitions=[(0, 1)]), [(0, 2)])


class TestTranscriberAdapter(unittest.TestCase):
    """§10.4 — a contract any ASR can satisfy, and one recorded instance."""

    def test_a_recorded_transcript_satisfies_the_contract(self):
        t = An.RecordedTranscriber(Path(__file__).parent / "golden" / "transcript.json").run()
        self.assertEqual(len(t.words), 6)
        self.assertEqual(t.words[0]["text"], "this")

    def test_the_adapter_is_the_interface_the_pipeline_uses(self):
        # the planner only needs .words in source frames
        t = An.RecordedTranscriber(Path(__file__).parent / "golden" / "transcript.json").run()
        self.assertTrue(all({"text", "start", "end"} <= set(w) for w in t.words))

    def test_a_transcript_without_timings_is_rejected(self):
        with self.assertRaises(ValueError):
            An.Transcript.validate([{"text": "hello"}])


class TestVfrConformMap(unittest.TestCase):
    """§5.9.4 — a variable-rate source must not get an affine map."""

    def test_a_cfr_source_gets_an_affine_map(self):
        m = In.build_conform_map(250, F(25), F(30000, 1001))
        self.assertEqual(m["kind"], "affine")
        self.assertEqual(m["conformed_frames"], 300)

    def test_a_vfr_source_gets_a_table(self):
        pts = [0, 33333, 66667, 133333, 166667, 200000]
        m = In.build_conform_map(6, F(30), F(30000, 1001), vfr=True, pts_us=pts)
        self.assertEqual(m["kind"], "table")
        self.assertEqual(m["table"], [0, 1, 2, 4, 5, 6])

    def test_the_table_is_non_decreasing_and_injective(self):
        pts = [0, 33333, 66667, 133333, 166667, 200000]
        table = In.build_conform_map(6, F(30), F(30000, 1001), vfr=True, pts_us=pts)["table"]
        self.assertEqual(table, sorted(table))
        self.assertEqual(len(set(table)), len(table))

    def test_a_vfr_source_without_timestamps_is_refused(self):
        # an affine map over VFR media is silently wrong; refuse instead
        with self.assertRaises(ValueError):
            In.build_conform_map(6, F(30), F(30000, 1001), vfr=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
