"""Golden-file tests for the reference compiler.

The rules are proved by test_conformance.py. This proves the translation:
the same IR must compile to the same graph, and the graph must be the one a
reviewer approved. A change to the graph is then a reviewable diff rather
than a silent behavioural change.
"""
import unittest
from fractions import Fraction as F
from pathlib import Path

import compiler
import spec_rules as R

FPS_2997 = F(30000, 1001)


class TestGoldenGraph(unittest.TestCase):
    """§11.6 — determinism is same manifest, same bytes."""

    def test_matches_the_golden_file(self):
        golden_path = Path(__file__).parent / "golden" / "appendix_a.graph"
        golden = golden_path.read_text()
        self.assertEqual(compiler.compile_ir(compiler.appendix_a_ir()) + "\n", golden)

    def test_compilation_is_deterministic(self):
        a = compiler.compile_ir(compiler.appendix_a_ir())
        b = compiler.compile_ir(compiler.appendix_a_ir())
        self.assertEqual(a, b)

    def test_graph_carries_no_paths_or_timestamps(self):
        # §11.6: an IR containing a path or a wall clock cannot be reproduced.
        graph = compiler.compile_ir(compiler.appendix_a_ir())
        for forbidden in ("/", "http", "2026", "tmp"):
            self.assertNotIn(forbidden, graph)

    def test_every_clip_is_produced_exactly_once(self):
        # A label appears twice when the clip is in a transition: once as a
        # producer and once as an xfade input. Only producers are counted.
        graph = compiler.compile_ir(compiler.appendix_a_ir())
        producers = [l for l in graph.split("\n") if "trim=start_frame" in l]
        self.assertEqual(len(producers), 5)
        for cid in ("c1", "c2", "c3", "c4", "c5"):
            self.assertEqual(sum(1 for l in producers if l.rstrip(";").endswith(f"[v_{cid}]")), 1, cid)

    def test_transitions_overlap_their_clips(self):
        graph = compiler.compile_ir(compiler.appendix_a_ir())
        self.assertEqual(graph.count("xfade"), 4)
        # 12 frames at 30000/1001 is 0.4004 s, and the offset is the cut point
        self.assertIn("duration=0.400400", graph)


class TestCompilerRules(unittest.TestCase):
    """The compiler must apply §5.9.2 and §6.3, not just copy the IR."""

    def test_gap_compiles_to_black_not_a_hole(self):
        ir = compiler.appendix_a_ir()
        ir["sequence"]["tracks"][0]["items"].append(
            {"kind": "gap", "id": "g1", "record": {"in": 1349, "out": 1373}})
        graph = compiler.compile_ir(ir)
        self.assertIn("color=c=black", graph)
        self.assertIn("[v_g1]", graph)

    def test_speed_consumes_conformed_frames(self):
        ir = compiler.appendix_a_ir()
        clip = ir["sequence"]["tracks"][0]["items"][1]        # c2: 221 native frames
        clip["speed"] = {"num": "2", "den": "1", "audio": "atempo"}
        graph = compiler.compile_ir(ir)
        # §5.9.3: C = R x s = 265 x 2 = 530 from the record duration, so the
        # conformed source span ends at 96 + 530 = 626 — not 96 + 221 x 2.
        self.assertIn("start_frame=96:end_frame=626", graph)
        self.assertIn("setpts=PTS/2.0", graph)

    def test_audio_speed_uses_the_cascade(self):
        ir = compiler.appendix_a_ir()
        ir["sequence"]["tracks"].append({
            "id": "A1", "kind": "audio",
            "items": [{"kind": "clip", "id": "a1", "asset": "ast_b07",
                       "source": {"in_sample": 0, "out_sample": 480480},
                       "record": {"in": 0, "out": 300},
                       "speed": {"num": "37", "den": "10", "audio": "atempo"}}]})
        graph = compiler.compile_ir(ir)
        self.assertIn("atempo=2", graph)          # 3.7 -> 2.0 x 1.85
        self.assertIn("atempo=1.85", graph)

    def test_unknown_asset_is_rejected(self):
        # §6.5: every asset id must exist in the manifest.
        ir = compiler.appendix_a_ir()
        ir["sequence"]["tracks"][0]["items"][0]["asset"] = "ast_missing"
        with self.assertRaises(KeyError):
            compiler.compile_ir(ir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
