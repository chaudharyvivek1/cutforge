"""Media analysis: shot detection and the transcript contract (§10).

Two things the planner actually consumes. Shot detection is real — ffmpeg's
scene score is a legitimate detector and it runs here. Transcription needs a
speech model this repository does not carry, so what is implemented is the
*contract*: a transcript with word times in source frames, and the remap that
takes it to record frames through the conform map.
"""
import json
import re
import subprocess
from dataclasses import dataclass, field
from fractions import Fraction as F

import renderer as R
import spec_rules as SR


def shots(path, threshold=0.30):
    """Cut points from ffmpeg's scene score, as half-open frame ranges.

    §10.1: shots are the unit the planner selects on, so an off-by-one here
    shifts every clip in the timeline. The boundaries are half-open and
    contiguous, which is the same convention as §5.2.
    """
    # The frame count cannot come from this run: `select` only passes the
    # frames it keeps, so ffmpeg's own counter reports the number of cuts.
    import ingest as I
    info = I.probe(path)
    fps = F(info["fps"][0], info["fps"][1])
    total = info["frames"]

    result = subprocess.run(
        [R.FFMPEG, "-hide_banner", "-i", str(path),
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    cuts = sorted({SR.frames_for_seconds(
                       F(str(float(m.group(1)))).limit_denominator(10**6), fps)
                   for m in re.finditer(r"pts_time:([0-9.]+)", result.stderr)})
    boundaries = [0] + [c for c in cuts if 0 < c < total] + [total]
    return [(a, b) for a, b in zip(boundaries, boundaries[1:]) if b > a]


@dataclass
class Transcript:
    """Words in *source* frames, which is what an ASR engine produces."""
    words: list = field(default_factory=list)      # [{text, start, end}]

    @staticmethod
    def validate(words):
        """§10.4: word-level timings, or it is not a transcript."""
        for n, word in enumerate(words):
            if not {"text", "start", "end"} <= set(word):
                raise ValueError(f"word {n} has no timing: {word!r}")
        return words

    @classmethod
    def from_json(cls, path):
        data = json.loads(open(path).read())
        return cls(words=cls.validate(data["words"]))

    def remap(self, conform_map, record_in=0, speed=1):
        """Source frames to record frames, through the conform map (§5.10).

        A caption whose time was not remapped is a caption on the wrong frame,
        and a speed change makes the error grow with distance from the cut —
        which is why §5.10 insists every timed annotation shares one transform.
        """
        src = F(*[int(x) for x in conform_map["source_rate"].split("/")])
        project = F(*[int(x) for x in conform_map["project_rate"].split("/")])
        ratio = project / src
        out = []
        for word in self.words:
            start = SR.round_half_away(F(word["start"]) * ratio)
            end = SR.round_half_away(F(word["end"]) * ratio)
            start = record_in + SR.round_half_away((start) / F(speed))
            end = record_in + SR.round_half_away((end) / F(speed))
            out.append({"text": word["text"], "start": start, "end": max(start + 1, end)})
        return out


class Transcriber:
    """The interface any ASR adapter must satisfy (§10.4)."""

    def run(self, path=None):
        raise NotImplementedError


class RecordedTranscriber(Transcriber):
    """A recorded transcript, so the pipeline is testable without a model.

    Transcription needs a speech model this repository does not carry. What it
    does carry is the contract and one recorded instance, which is enough to
    prove that word times reach captions through the conform map.
    """

    def __init__(self, path):
        self.path = path

    def run(self, path=None):
        return Transcript.from_json(path or self.path)
