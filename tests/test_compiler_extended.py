"""Golden files for the operations Appendix A does not exercise.

§19.1 says the compiler's coverage should be proportional to its risk, and the
untested operations are the ones with the most parameters: a transform has
more ways to be wrong than a trim. Each of these has its own golden file, so a
change to it is a diff rather than a silent behavioural change.
"""
import unittest
from pathlib import Path

import compiler as C

GOLDEN = Path(__file__).parent / "golden"


class GoldenMixin:
    """Shared golden tests. A plain mixin, so unittest does not collect it."""

    fixture = None
    name = None

    def test_matches_golden(self):
        produced = C.compile_ir(self.fixture()) + "\n"
        expected = (GOLDEN / f"{self.name}.graph").read_text()
        self.assertEqual(produced, expected)

    def test_is_deterministic(self):
        self.assertEqual(C.compile_ir(self.fixture()), C.compile_ir(self.fixture()))


class TestOverlay(GoldenMixin, unittest.TestCase):
    """§11.7, §6.4 — a transform effect and a fade, on a clip."""

    fixture = staticmethod(C.overlay_ir)
    name = "overlay"

    def test_crop_and_fade_are_both_applied(self):
        graph = C.compile_ir(C.overlay_ir())
        self.assertIn("crop=960:540:0:0", graph)
        self.assertIn("fade=t=in:st=0:d=0.400400", graph)

    def test_effect_order_follows_the_ir(self):
        graph = C.compile_ir(C.overlay_ir())
        self.assertLess(graph.index("crop="), graph.index("fade=t=in"))


class TestCaptions(GoldenMixin, unittest.TestCase):
    """§11.4 — rasterised at output resolution, never at a fixed pixel size."""

    fixture = staticmethod(C.captions_ir)
    name = "captions"

    def test_font_size_is_derived_from_height(self):
        graph = C.compile_ir(C.captions_ir())
        # 4.5% of 1920 is 86; a fixed 48 would be visibly soft at UHD
        self.assertIn("fontsize=86", graph)

    def test_font_size_scales_with_the_project(self):
        ir = C.captions_ir()
        ir["project"]["resolution"] = [2160, 3840]
        self.assertIn("fontsize=173", C.compile_ir(ir))


class TestHDR(GoldenMixin, unittest.TestCase):
    """§12.6 — tone-map to SDR, do not retag."""

    fixture = staticmethod(C.hdr_ir)
    name = "hdr"

    def test_hlg_input_is_interpreted_as_hlg(self):
        graph = C.compile_ir(C.hdr_ir())
        self.assertIn("tin=arib-std-b67", graph)

    def test_mastering_metadata_is_stripped(self):
        graph = C.compile_ir(C.hdr_ir())
        self.assertIn("type=MASTERING_DISPLAY_METADATA", graph)
        self.assertIn("type=CONTENT_LIGHT_LEVEL", graph)

    def test_an_sdr_source_is_not_tone_mapped(self):
        self.assertNotIn("tonemap", C.compile_ir(C.appendix_a_ir()))


class TestWipe(GoldenMixin, unittest.TestCase):
    """§5.7 — align moves the overlap, and the offset follows it."""

    fixture = staticmethod(C.wipe_ir)
    name = "wipe"

    def test_alignment_sets_the_offset(self):
        graph = C.compile_ir(C.wipe_ir())
        self.assertIn("transition=wipeleft", graph)
        self.assertIn("offset=0.000000", graph)

    def test_centred_wipe_offsets_by_a_quarter(self):
        ir = C.wipe_ir()
        ir["sequence"]["tracks"][0]["transitions"][0]["align"] = "center"
        self.assertIn("offset=0.100100", C.compile_ir(ir))


class TestLut(GoldenMixin, unittest.TestCase):
    """§11.4 — the creative grade sits at the end of the chain."""

    fixture = staticmethod(C.lut_ir)
    name = "lut"

    def test_lut_is_applied_last(self):
        graph = C.compile_ir(C.lut_ir())
        line = next(l for l in graph.split("\n") if "[v_c1]" in l)
        self.assertTrue(line.rstrip(";").endswith("[v_c1]"))
        self.assertGreater(line.index("lut3d"), line.index("scale="))

    def test_lut_is_referenced_not_pathed(self):
        # §9.3: no tool takes a path. The graph must not contain a directory.
        graph = C.compile_ir(C.lut_ir())
        self.assertIn("lut3d=file=lut_warm_07.cube", graph)
        self.assertNotIn("/", graph)


class TestAudioBus(GoldenMixin, unittest.TestCase):
    """§11.1 — one mixed, loudness-normalised bus, not one stream per track."""

    fixture = staticmethod(C.audio_mix_ir)
    name = "audio_mix"

    def test_two_tracks_are_mixed(self):
        graph = C.compile_ir(C.audio_mix_ir())
        self.assertIn("amix=inputs=2:normalize=0", graph)

    def test_the_bus_is_normalised(self):
        graph = C.compile_ir(C.audio_mix_ir())
        self.assertIn("loudnorm=I=-14:TP=-1.5:LRA=11", graph)
        self.assertEqual(graph.count("loudnorm"), 1)

    def test_a_single_track_is_not_mixed(self):
        graph = C.compile_ir(C._base_ir())
        self.assertNotIn("amix", graph)


class TestInverseMap(GoldenMixin, unittest.TestCase):
    """§12.6 — an SDR source on an HDR timeline is expanded, not retagged."""

    fixture = staticmethod(C.sdr_to_hdr_ir)
    name = "sdr_to_hdr"

    def test_hlg_project_expands_to_hlg(self):
        graph = C.compile_ir(C.sdr_to_hdr_ir())
        self.assertIn("t=arib-std-b67", graph)
        self.assertIn("p=bt2020", graph)

    def test_pq_project_expands_to_pq(self):
        ir = C.sdr_to_hdr_ir()
        ir["project"]["color_space"] = "rec2020-pq"
        self.assertIn("t=smpte2084", C.compile_ir(ir))

    def test_ten_bit_is_preserved(self):
        self.assertIn("yuv420p10le", C.compile_ir(C.sdr_to_hdr_ir()))

    def test_the_operator_comes_from_the_manifest(self):
        ir = C.hdr_ir()
        # merge, do not replace: the metadata also carries the asset manifest
        ir["metadata"]["tonemap"] = {"operator": "mobius", "peak": 203}
        graph = C.compile_ir(ir)
        self.assertIn("tonemap=mobius", graph)
        self.assertIn("npl=203", graph)


class TestGoldenProvenance(unittest.TestCase):
    """A golden nobody can explain is a golden nobody should trust."""

    def test_every_golden_is_documented(self):
        readme = (GOLDEN / "README.md").read_text()
        for path in sorted(GOLDEN.glob("*.graph")):
            self.assertIn(path.name, readme, f"{path.name} is not in golden/README.md")


class TestEffectCoverage(unittest.TestCase):
    """§6.4 — an enum value is a promise the compiler keeps."""

    def test_unimplemented_effect_is_loud(self):
        # lut is implemented from v1.9; colour grading is not yet.
        ir = C.overlay_ir()
        ir["sequence"]["tracks"][0]["items"][0]["effects"].append({"type": "color"})
        with self.assertRaises(NotImplementedError):
            C.compile_ir(ir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
