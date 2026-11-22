# Benchmarks

§12.3's capacity model is built on NVENC session counts and NVDEC engines. Every number in it is a **target**, marked as such in §2.2, and none has been measured — the render tests in `tests/` run on a CPU with the pip-distributed ffmpeg at 320×180.

This directory is where measured numbers go, and the rule for adding one is the same rule the frame hashes use: **a number is recorded beside the hardware and build that produced it**, because a throughput figure without its hardware is a rumour.

## What the workflow does

`.github/workflows/benchmark.yml` runs **on demand only**, on a runner labelled `gpu`. It was weekly in v2.5 and that was a mistake: with no runner registered the job queues forever and reports nothing, which is the same shape as a test that skips. It renders the fixtures at each resolution in §12.9's matrix and writes the results here as JSON:

```
docs/benchmarks/<date>-<gpu>.json
```

Each file carries: the GPU model, the driver version, the ffmpeg build, the fixture, the resolution, the preset, frames rendered, wall time, and the derived realtime factor.

## What it does not do

It does not run on pull requests, because GPU minutes cost money and a regression in throughput is not a correctness failure. It does not gate a release; §12.9 says a release is gated on the numbers *matching* the matrix, and that gate is a human reading two files and comparing them.

## Until there is a GPU runner

The workflow is present and will skip with a clear message. That is deliberate: a benchmark job that silently does nothing is the failure mode this repository has been fixing since v1.8, so the skip prints which label was missing and exits green only because a missing runner is an infrastructure fact rather than a code defect. The README's technology table says **CPU only** for exactly this reason.
