from pathlib import Path
def apply(clip_a, clip_b):
    out = clip_a.with_name('merged.mp4')
    return out
