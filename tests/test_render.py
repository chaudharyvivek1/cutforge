"""The renderer, executed: the first check in this repository that produces pixels.

§19's first compiler gate is "golden frame hashes match for every fixture".
Until v2.0 that gate did not exist, and the compiler's guarantees were
syntactic — a trim with the wrong end frame compiled cleanly.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import compiler as C
import renderer as R

HASHES = Path(__file__).parent / "golden" / "frame_hashes.json"

# A tiny timeline: two clips cut together, then the same with a dissolve.
SIMPLE = """[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_a];
[1:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_b];
[v_a][v_b]concat=n=2:v=1:a=0[v_out]"""

DISSOLVE = """[0:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_a];
[1:v]trim=start_frame=0:end_frame=24,setpts=PTS-STARTPTS,scale=320:180[v_b];
[v_a][v_b]xfade=transition=fade:duration=0.5:offset=0.5[v_out]"""


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO FRAMES WERE RENDERED")
class TestRender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.a = R.make_source(cls.tmp / "a.mp4", pattern="testsrc2")
        cls.b = R.make_source(cls.tmp / "b.mp4", pattern="smptebars")
        cls.hashes = R.load_hashes(HASHES)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _check(self, name, graph):
        digest = R.render_raw(graph, [self.a, self.b])
        recorded = self.hashes.get(name)
        self.assertIsNotNone(recorded, f"no golden hash for {name}")
        if recorded["ffmpeg"] != R.major():
            self.skipTest(f"ffmpeg {recorded['ffmpeg']} recorded, {R.major()} running — "
                          f"hashes are only comparable within a build (§11.6)")
        self.assertEqual(digest, recorded["sha256"], f"{name} renders differently")

    def test_a_cut_renders_identically(self):
        self._check("cut", SIMPLE)

    def test_a_dissolve_renders_identically(self):
        self._check("dissolve", DISSOLVE)

    def test_rendering_is_repeatable(self):
        first = R.render_raw(SIMPLE, [self.a, self.b])
        second = R.render_raw(SIMPLE, [self.a, self.b])
        self.assertEqual(first, second)

    def test_the_graph_and_the_pixels_agree_on_length(self):
        # v2.1 asserted that ffmpeg mentioned "frame=" on stderr, which is true
        # of every run including a broken one. This counts the frames instead.
        raw = R.render_bytes(SIMPLE, [self.a, self.b])
        frames = len(raw) // (320 * 180 * 3 // 2)          # yuv420p
        self.assertEqual(frames, 48)                        # 24 + 24

    def test_a_dissolve_costs_its_overlap(self):
        # §5.7: a transition consumes record time, so the output is shorter
        raw = R.render_bytes(DISSOLVE, [self.a, self.b])
        frames = len(raw) // (320 * 180 * 3 // 2)
        self.assertEqual(frames, 36)                        # 48 - 12 at 24 fps

    def test_a_broken_graph_fails_loudly(self):
        with self.assertRaises(RuntimeError):
            R.render_raw("[0:v]nosuchfilter=1[v_out]", [self.a])


if __name__ == "__main__":
    unittest.main(verbosity=2)


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NO FRAMES WERE RENDERED")
class TestCompilerFixturesRender(unittest.TestCase):
    """The compiler's own fixtures, rendered.

    v2.0 hashed two graphs written as string literals, which proves that *a*
    graph renders identically and says nothing about the graph the compiler
    emits. These compile the fixtures and render them, so the golden graph and
    the golden hash describe the same artefact.
    """

    @classmethod
    def setUpClass(cls):
        import assets
        cls.tmp = Path(tempfile.mkdtemp())
        cls.a = assets.appendix_a_assets(cls.tmp)
        cls.music = assets.audio(cls.tmp / "music.wav", seconds=12, tone=440)
        cls.dialogue = assets.audio(cls.tmp / "dialogue.wav", seconds=12, tone=660)
        cls.hashes = R.load_hashes(HASHES)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _recorded(self, name):
        recorded = self.hashes.get(name)
        self.assertIsNotNone(recorded, f"no golden hash for {name}")
        if recorded["ffmpeg"] != R.major():
            self.skipTest(f"ffmpeg {recorded['ffmpeg']} recorded, {R.major()} running")
        return recorded

    def test_appendix_a_renders_from_the_compilers_own_graph(self):
        ir = C.appendix_a_ir()
        ir["project"]["resolution"] = [180, 320]      # small, for speed
        graph = C.compile_ir(ir)
        self.assertTrue(graph.rstrip().endswith("[v_out]"))
        digest = R.render_raw(graph, [self.a[x] for x in
                                      ["ast_a91", "ast_b07", "ast_c13", "ast_d22"]])
        self.assertEqual(digest, self._recorded("appendix_a_compiled")["sha256"])

    def test_an_acrossfade_renders_to_the_expected_length(self):
        # §11.5's acceptance test: the decoded sample count, not just a hash
        from fractions import Fraction as F
        graph = C.compile_ir(C.audio_transition_ir())
        raw = R.render_audio_raw(graph, [self.music, self.dialogue])
        samples = len(raw) // 4                       # 16-bit stereo
        expected = R.samples_for(588, F(30000, 1001)) if hasattr(R, "samples_for") else None
        if expected is None:
            import spec_rules as SR
            expected = SR.samples_for(588, F(30000, 1001))
        self.assertEqual(samples, expected)
        # a fade at the wrong offset produces the same length, so pin content too
        import hashlib
        digest = hashlib.sha256(raw).hexdigest()
        recorded = self._recorded("audio_transition")
        self.assertEqual(digest, recorded["sha256"])

    def test_the_audio_bus_renders(self):
        graph = C.compile_ir(C.audio_only_ir())
        digest = R.render_audio(graph, [self.music, self.dialogue])
        self.assertEqual(digest, self._recorded("audio_mix_compiled")["sha256"])

    def test_the_fixture_is_sensitive_to_asset_content(self):
        # A hash that does not change when the inputs do is measuring nothing.
        ir = C.appendix_a_ir()
        ir["project"]["resolution"] = [180, 320]
        graph = C.compile_ir(ir)
        order = ["ast_a91", "ast_b07", "ast_c13", "ast_d22"]
        base = R.render_raw(graph, [self.a[x] for x in order])
        swapped = R.render_raw(graph, [self.a[x] for x in
                                       ["ast_b07", "ast_a91", "ast_c13", "ast_d22"]])
        self.assertNotEqual(base, swapped)

    def test_the_graph_carries_a_final_label(self):
        # v2.0 emitted transitions and never joined them: no [v_out] existed
        for fixture in (C.appendix_a_ir, C.overlay_ir, C.wipe_ir):
            self.assertIn("[v_out]", C.compile_ir(fixture()))

    def test_a_cut_without_transitions_uses_concat(self):
        ir = C.appendix_a_ir()
        ir["sequence"]["tracks"][0]["transitions"] = []
        self.assertIn("concat=n=2", C.compile_ir(ir))
