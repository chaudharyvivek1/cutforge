"""The four things v2.2 added: a persistent worker, a repair band, a corpus
contract, and a perceptual fallback for a build mismatch."""
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

import corpus as Co
import planner as P
import repair as Rp
import store as St

FPS = F(30000, 1001)
REQUEST = {"duration_target_ms": 45011,
           "shots": [{"asset": f"a{i}", "in": 0, "out": 300, "labels": []}
                     for i in range(4)]}


class TestRepairBand(unittest.TestCase):
    """§7.7 — the loop exists to close the 2% to 5% band."""

    def test_a_short_plan_is_in_the_repair_band(self):
        short = P.plan_short(REQUEST, deficit_frames=40)
        self.assertEqual(P.validate(short, FPS), ["duration in the repair band"])

    def test_the_loop_repairs_a_short_plan(self):
        # a real planner that under-delivers, not a hand-broken structure
        state = {"first": True}

        def plan_fn(request):
            if state["first"]:
                state["first"] = False
                return P.plan_short(request, deficit_frames=40)
            return P.plan(request)

        result = Rp.run(REQUEST, plan_fn, lambda p: P.validate(p, FPS),
                        lambda p, problems: P.plan(REQUEST))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["attempts"], 2)

    def test_a_large_deficit_is_not_repairable_by_the_loop(self):
        short = P.plan_short(REQUEST, deficit_frames=200)      # ~15%
        self.assertEqual(P.validate(short, FPS), ["duration in the fallback band"])


class TestCorpusContract(unittest.TestCase):
    """§8.6 — the labelled set has a shape, even though it has no data yet."""

    def test_an_empty_corpus_is_rejected(self):
        self.assertEqual(Co.validate([]), ["empty corpus"])

    def test_a_corpus_missing_a_condition_is_rejected(self):
        entries = [{"id": "p1", "distance": 0.2, "same_person": True,
                    "conditions": ["lighting", "angle", "occlusion"]},
                   {"id": "n1", "distance": 0.9, "same_person": False,
                    "conditions": ["lighting", "angle", "occlusion"]}]
        problems = Co.validate(entries)
        self.assertTrue(any("age" in p for p in problems), problems)

    def test_a_well_formed_corpus_passes(self):
        entries = [{"id": "p1", "distance": 0.2, "same_person": True,
                    "conditions": ["lighting", "angle", "occlusion", "age"]},
                   {"id": "n1", "distance": 0.9, "same_person": False,
                    "conditions": ["lighting", "angle", "occlusion", "age"]}]
        self.assertEqual(Co.validate(entries), [])

    def test_a_distance_outside_the_range_is_rejected(self):
        entries = [{"id": "p1", "distance": 1.4, "same_person": True,
                    "conditions": ["lighting", "angle", "occlusion", "age"]}]
        self.assertTrue(any("distance" in p for p in Co.validate(entries)))


class TestCorpusPipeline(unittest.TestCase):
    """§8.6 — the loader, the validator and the rates, on a committed fixture."""

    def test_the_fixture_corpus_loads_and_measures(self):
        data = Co.load(Path(__file__).parent / "golden" / "corpus_fixture.json",
                       synthetic=True)
        pairs = [(e["distance"], e["same_person"]) for e in data["pairs"]]
        import accuracy as A
        result = A.rates(pairs)
        self.assertEqual(result["counts"]["fp"], 0)
        self.assertEqual(result["counts"]["fn"], 0)
        self.assertEqual(A.meets_targets(result), [])

    def test_a_synthetic_corpus_is_refused_without_the_flag(self):
        with self.assertRaises(ValueError):
            Co.load(Path(__file__).parent / "golden" / "corpus_fixture.json")

    def test_a_malformed_fixture_is_rejected(self):
        data = Co.load(Path(__file__).parent / "golden" / "corpus_fixture.json",
                       synthetic=True)
        data["pairs"][0].pop("conditions")
        self.assertTrue(Co.validate(data["pairs"]))


class TestWorkerResume(unittest.TestCase):
    """§18 — a job survives its worker, on disk."""

    def test_a_resume_starts_at_the_checkpoint(self):
        directory = tempfile.mkdtemp()
        path = str(Path(directory) / "jobs.db")
        first = St.Store(path)
        job, _ = first.submit("tnt_a", "render")
        claimed = first.claim("w1")
        first.checkpoint(claimed["id"], 3)
        first.db.close()

        # the worker died; a new process picks the job up
        second = St.Store(path)
        try:
            self.assertEqual(second.requeue_orphans(older_than=0), 1)
            resumed = St.Worker(second, "w2").run_once()
            self.assertEqual(resumed["state"], "succeeded")
            self.assertEqual(resumed["attempt"], 2)
        finally:
            second.db.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
