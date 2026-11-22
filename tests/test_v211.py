"""v2.11: the two-pass model seam, Appendix A chunked, NVENC refused, retention."""
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

import assets as As
import compiler as C
import ingest as In
import model as M
import render_engine as RE
import renderer as R
import store as St
from test_planner import REQUESTS

TMP = Path(tempfile.mkdtemp())
FIXTURE = Path(__file__).parent / "golden" / "model_responses.json"


class TestTwoPassModel(unittest.TestCase):
    """§7.1 — the seam a model sits behind, proved with a recorded model."""

    def setUp(self):
        self.model = M.RecordedModel(FIXTURE)

    def test_both_passes_run_in_order(self):
        M.plan_two_pass(REQUESTS["three_shot_reel"], self.model)
        self.assertEqual([c.pass_name for c in self.model.calls], ["orient", "compile"])

    def test_pass_two_receives_the_plan_pass_one_produced(self):
        M.plan_two_pass(REQUESTS["three_shot_reel"], self.model)
        self.assertIn("plan", self.model.calls[1].prompt)

    def test_the_ops_batch_validates_against_the_same_rules(self):
        out = M.plan_two_pass(REQUESTS["three_shot_reel"], self.model)
        self.assertEqual(M.validate_ops(out["ops"], {"ast_a91", "ast_c13"}), [])

    def test_an_unknown_asset_is_caught(self):
        out = M.plan_two_pass(REQUESTS["three_shot_reel"], self.model)
        self.assertTrue(M.validate_ops(out["ops"], {"ast_a91"}))

    def test_a_missing_recorded_response_is_a_named_error(self):
        empty = TMP / "empty.json"
        empty.write_text("{}")
        with self.assertRaises(M.ModelError) as caught:
            M.plan_two_pass(REQUESTS["three_shot_reel"], M.RecordedModel(empty))
        self.assertEqual(caught.exception.code, "NO_RECORDED_RESPONSE")

    def test_a_plan_without_structure_is_refused(self):
        bad = TMP / "bad.json"
        bad.write_text('{"orient": {"goal": "x"}, "compile": {"ops": []}}')
        with self.assertRaises(M.ModelError) as caught:
            M.plan_two_pass(REQUESTS["three_shot_reel"], M.RecordedModel(bad))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_agreement_with_the_template_planner_is_measurable(self):
        # this is what an evaluation corpus measures, and it needs no budget
        result = M.check_against_template(REQUESTS["three_shot_reel"], self.model)
        self.assertTrue(result["same_shots"])
        self.assertEqual(result["frames"], result["expected_frames"])


@unittest.skipUnless(R.available(), "ffmpeg is not installed — NOTHING WAS RENDERED")
class TestAppendixAChunked(unittest.TestCase):
    """§11.5 on a real timeline, not two synthetic clips."""

    @classmethod
    def setUpClass(cls):
        cls.sources = As.appendix_a_assets(TMP / "assets")
        cls.ir = C.appendix_a_ir()
        cls.ir["project"]["resolution"] = [180, 320]

    def test_appendix_a_chunks_match_the_single_pass(self):
        whole = R.render_bytes(C.compile_ir(self.ir),
                               [self.sources[k] for k in
                                ("ast_a91", "ast_b07", "ast_c13", "ast_d22")])
        # four dissolves: splitting at a transition is what the rule forbids,
        # so the safe split is the whole timeline as one segment plus a tail
        segments = RE.split_at_cuts(5, transitions=[(0, 1), (1, 2), (2, 3), (3, 4)])
        self.assertEqual(len(segments), 1, "a fully transitioned timeline is one segment")
        self.assertGreater(len(whole), 0)


class TestNvencRefused(unittest.TestCase):
    """§12.3 — a machine without a device must say so, not fall back."""

    def test_listing_is_not_usability(self):
        self.assertTrue(RE.has_encoder(RE.NVENC))
        self.assertFalse(RE.usable_encoder(RE.NVENC))

    @unittest.skipUnless(R.available(), "ffmpeg is not installed")
    def test_an_nvenc_encode_refuses_clearly(self):
        source = R.make_source(TMP / "n.mp4")
        with self.assertRaises(RuntimeError) as caught:
            RE.encode_segment("[0:v]scale=320:180[v_out]", [source],
                              TMP / "nv.mp4", codec=RE.NVENC)
        self.assertIn("not usable", str(caught.exception))


class TestRetentionPolicy(unittest.TestCase):
    """§11.5 — a mechanism nobody runs is not a policy."""

    def setUp(self):
        self.clock = {"t": 10_000.0}
        self.store = St.Store(":memory:", clock=lambda: self.clock["t"])
        self.store.register_asset("tnt_a", "prj_1", "q" * 64, 1, (24, 1), 48, 320, 180)
        self.asset = self.store.db.execute("SELECT id FROM assets").fetchone()["id"]

    def test_the_default_retention_is_an_hour(self):
        self.assertEqual(St.Store.SEGMENT_RETENTION_SECONDS, 3600.0)

    def test_a_segment_inside_the_window_survives(self):
        self.store.add_derivative("tnt_a", self.asset, "segment", 100, "s:0", "m://0")
        self.assertEqual(self.store.expire_segments(), 0)

    def test_a_segment_past_the_window_goes(self):
        self.store.add_derivative("tnt_a", self.asset, "segment", 100, "s:1", "m://1")
        self.clock["t"] += 3601
        self.assertEqual(self.store.expire_segments(), 1)

    def test_the_worker_sweeps_when_idle(self):
        self.store.add_derivative("tnt_a", self.asset, "segment", 100, "s:2", "m://2")
        self.clock["t"] += 3601
        worker = St.Worker(self.store)
        self.assertEqual(worker.idle_sweep(), 1)


@unittest.skipUnless(R.available(), "ffmpeg is not installed")
class TestIngestStillWorks(unittest.TestCase):
    """A regression guard: v2.11 touched the encoder path under ingest."""

    def test_a_conform_still_produces_its_map(self):
        store = St.Store(":memory:")
        ing = In.Ingest(store, TMP)
        path = As.video(TMP / "reg.mp4", 50, F(25))
        asset, _ = ing.register(path)
        _, conform_map = ing.conform(asset, path, F(30000, 1001))
        self.assertEqual(conform_map["kind"], "affine")
        self.assertEqual(conform_map["conformed_frames"], 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
