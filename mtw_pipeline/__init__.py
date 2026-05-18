"""MTW recipe-driven video generation package."""

from .assembler import generate_video
from .labeler import load_clip_labels
from .models import ClipRecord, RenderPlan, SlotSelection

__all__ = ["ClipRecord", "RenderPlan", "SlotSelection", "generate_video", "load_clip_labels"]
