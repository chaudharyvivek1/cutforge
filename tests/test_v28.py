"""v2.8: assets exist, ingest produces what the compiler assumes, analysis runs."""
import subprocess
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

import analysis as An
import assets as As
import ingest as In
import renderer as R
import store as St

TMP = Path(tempfile.mkdtemp())


def clip(name, frames, fps, pattern="testsrc2", vf=None):
    return As.video(TMP / name, frames, fps, pattern=pattern, vf=vf)


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO MEDIA WAS PROBED")
class TestProbe(unittest.TestCase):
    """§10.1 — the five fields ingest needs, read from the file itself."""

    def test_it_reads_rate_frames_and_size(self):
        path = clip("p25.mp4", 250, F(25))
        info = In.probe(path)
        self.assertEqual(info["fps"], (25, 1))
        self.assertEqual(info["frames"], 250)
        self.assertEqual((info["width"], info["height"]), (320, 180))

    def test_a_fractional_rate_comes_back_as_a_rational(self):
        # 29.97 must not be stored as 29.97; §5.1 forbids it
        path = clip("p2997.mp4", 120, F(30000, 1001))
        info = In.probe(path)
        self.assertEqual(F(*info["fps"]), F(30000, 1001))

    def test_the_byte_count_is_the_file_size(self):
        path = clip("bytes.mp4", 48, F(24))
        self.assertEqual(In.probe(path)["bytes"], path.stat().st_size)


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO MEDIA WAS PROBED")
class TestIngest(unittest.TestCase):
    """§5.3 and §5.9.2 — the derivative the compiler assumes now exists."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.ingest = In.Ingest(self.store, TMP)
        self.path = clip("ing.mp4", 250, F(25))
        self.asset, _ = self.ingest.register(self.path)

    def test_an_asset_is_registered_with_its_probe(self):
        self.assertEqual(self.asset["frames"], 250)
        self.assertEqual(self.asset["fps_num"], 25)

    def test_the_same_content_is_not_registered_twice(self):
        again, created = self.ingest.register(self.path)
        self.assertFalse(created)
        self.assertEqual(again["id"], self.asset["id"])

    def test_a_proxy_is_recorded_as_a_derivative(self):
        out = self.ingest.proxy(self.asset, self.path, height=90)
        self.assertTrue(out.exists())
        derivative = self.store.derivative("tnt_a", self.asset["id"], "proxy", "proxy:90")
        self.assertIsNotNone(derivative)

    def test_the_conform_map_is_the_section_5_9_arithmetic(self):
        _, conform_map = self.ingest.conform(self.asset, self.path, F(30000, 1001))
        self.assertEqual(conform_map["native_frames"], 250)
        self.assertEqual(conform_map["conformed_frames"], 300)
        self.assertEqual(conform_map["delta_frames"], 50)

    def test_a_same_rate_conform_has_no_delta(self):
        _, conform_map = self.ingest.conform(self.asset, self.path, F(25))
        self.assertEqual(conform_map["delta_frames"], 0)

    def test_the_conform_file_has_the_frames_the_map_promises(self):
        out, conform_map = self.ingest.conform(self.asset, self.path, F(30000, 1001))
        self.assertEqual(In.probe(out)["frames"], conform_map["conformed_frames"])


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO MEDIA WAS PROBED")
class TestStorageQuota(unittest.TestCase):
    """§16.1's other half, now that there is a table to sum."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.ingest = In.Ingest(self.store, TMP)
        self.path = clip("quota.mp4", 48, F(24))
        self.asset, _ = self.ingest.register(self.path)

    def test_originals_count(self):
        self.assertEqual(self.store.stored_bytes("tnt_a"), self.path.stat().st_size)

    def test_derivatives_count_too(self):
        before = self.store.stored_bytes("tnt_a")
        self.ingest.proxy(self.asset, self.path, height=90)
        self.assertGreater(self.store.stored_bytes("tnt_a"), before)

    def test_a_quota_refuses_rather_than_truncating(self):
        used = self.store.stored_bytes("tnt_a")
        ok, reported = self.store.consume_storage("tnt_a", 5, limit=used + 10)
        self.assertTrue(ok)
        ok, reported = self.store.consume_storage("tnt_a", 1000, limit=used + 10)
        self.assertFalse(ok)
        self.assertEqual(reported, used)


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO MEDIA WAS PROBED")
class TestShotDetection(unittest.TestCase):
    """§10.1 — shots are the unit the planner selects on."""

    @classmethod
    def setUpClass(cls):
        a = clip("s1.mp4", 48, F(24), pattern="testsrc2")
        b = clip("s2.mp4", 48, F(24), pattern="testsrc", vf="hue=h=180")
        cls.cut = TMP / "cut.mp4"
        subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-i", str(a), "-i", str(b),
                        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0",
                        "-c:v", "libx264", "-preset", "ultrafast", str(cls.cut)],
                       check=True)

    def test_a_hard_cut_is_found(self):
        self.assertEqual(An.shots(self.cut), [(0, 48), (48, 96)])

    def test_shots_are_contiguous_and_half_open(self):
        shots = An.shots(self.cut)
        self.assertEqual(shots[0][0], 0)
        for a, b in zip(shots, shots[1:]):
            self.assertEqual(a[1], b[0])
        self.assertEqual(shots[-1][1], 96)


class TestTranscriptRemap(unittest.TestCase):
    """§5.10 — a caption whose time was not remapped is on the wrong frame."""

    def setUp(self):
        self.transcript = An.Transcript.from_json(
            Path(__file__).parent / "golden" / "transcript.json")

    def test_word_times_scale_with_the_conform_map(self):
        out = self.transcript.remap({"source_rate": "25/1",
                                     "project_rate": "30000/1001"})
        self.assertEqual(out[0]["start"], 0)
        self.assertEqual(out[1]["start"], 7)        # 6 frames at 25 fps -> 7.19 at 29.97

    def test_a_same_rate_map_is_the_identity(self):
        out = self.transcript.remap({"source_rate": "25/1", "project_rate": "25/1"})
        self.assertEqual([w["start"] for w in out], [0, 6, 12, 18, 40, 60])

    def test_speed_divides_the_record_time(self):
        out = self.transcript.remap({"source_rate": "25/1", "project_rate": "25/1"},
                                    speed=2)
        self.assertEqual([w["start"] for w in out], [0, 3, 6, 9, 20, 30])

    def test_a_record_offset_shifts_every_word(self):
        out = self.transcript.remap({"source_rate": "25/1", "project_rate": "25/1"},
                                    record_in=100)
        self.assertEqual(out[0]["start"], 100)

    def test_a_word_never_has_zero_duration(self):
        for word in self.transcript.remap({"source_rate": "25/1", "project_rate": "30000/1001"},
                                          speed=8):
            self.assertGreater(word["end"], word["start"])


class TestUsageRollover(unittest.TestCase):
    """§16.1 — a quota that never resets is a quota that eventually refuses all."""

    def test_a_new_period_starts_from_zero(self):
        store = St.Store(":memory:")
        store.consume_render_minutes("tnt_a", 60, limit=60, period="2026-11")
        self.assertFalse(store.consume_render_minutes("tnt_a", 1, limit=60,
                                                      period="2026-11")[0])
        self.assertTrue(store.consume_render_minutes("tnt_a", 1, limit=60,
                                                     period="2026-12")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
