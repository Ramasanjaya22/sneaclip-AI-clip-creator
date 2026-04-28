import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, CompositeVideoClip, CompositeAudioClip,
    AudioFileClip, TextClip, ImageClip, vfx, afx,
    concatenate_audioclips
)

TARGET_VERTICAL = (1080, 1920)
BLUR_RADIUS_DEFAULT = 12


def _blur_frame_fast(frame, radius=BLUR_RADIUS_DEFAULT):
    img = Image.fromarray(frame)
    w, h = img.size
    small = img.resize((max(1, w // 4), max(1, h // 4)), Image.BILINEAR)
    blurred_small = small.filter(ImageFilter.GaussianBlur(radius=max(1, radius // 4)))
    blurred = blurred_small.resize((w, h), Image.BILINEAR)
    return np.array(blurred)


def _resolve_font_path(config):
    font_path = config.get("font_path", "")
    if font_path and os.path.exists(font_path):
        return font_path
    candidates = [
        "Arial-Bold",
        "Arial-Bold-Italic",
        "Arial-Black",
        "Helvetica-Bold",
        "DejaVuSans-Bold",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "Arial-Bold"


def _normalize_position(position):
    position_map = {
        "top-left": ("left", "top"),
        "top-right": ("right", "top"),
        "bottom-left": ("left", "bottom"),
        "bottom-right": ("right", "bottom"),
        "center": "center",
        "left": "left",
        "right": "right",
        "top": "top",
        "bottom": "bottom",
    }
    if isinstance(position, str) and position in position_map:
        return position_map[position]
    return position


def _get_preview_overlay_xy(image_size, overlay_size, position, pad=20):
    iw, ih = image_size
    ow, oh = overlay_size
    pos_map = {
        "bottom-right": (iw - ow - pad, ih - oh - pad),
        "bottom-left": (pad, ih - oh - pad),
        "top-right": (iw - ow - pad, pad),
        "top-left": (pad, pad),
        "center": ((iw - ow) // 2, (ih - oh) // 2),
    }
    return pos_map.get(position, pos_map["bottom-right"])


def _render_vertical_frame(frame, blur_bg=True, blur_radius=BLUR_RADIUS_DEFAULT):
    h, w = frame.shape[:2]
    aspect = w / max(h, 1)
    target_w, target_h = TARGET_VERTICAL
    target_aspect = target_w / target_h
    img = Image.fromarray(frame)

    if aspect > target_aspect and blur_bg:
        bg = img.resize((int(h * target_aspect), h), Image.LANCZOS) if aspect > 1 else img.copy()
        bg = bg.resize((target_w, target_h), Image.LANCZOS)
        blurred = _blur_frame_fast(np.array(bg), blur_radius)
        blurred_img = Image.fromarray(blurred)

        fg_w = target_w
        fg_h = int(target_w / aspect)
        fg = img.resize((fg_w, fg_h), Image.LANCZOS)

        y_offset = (target_h - fg_h) // 2
        blurred_img.paste(fg, (0, y_offset))
        return np.array(blurred_img)

    resized = img.resize((target_w, target_h), Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    cropped = resized.crop((left, top, left + target_w, top + target_h))
    return np.array(cropped)


def render_vertical_9_16(clip, blur_bg=True, blur_radius=BLUR_RADIUS_DEFAULT):
    w, h = clip.size
    aspect = w / max(h, 1)
    target_w, target_h = TARGET_VERTICAL
    target_aspect = target_w / target_h

    if aspect > target_aspect and blur_bg:
        bg = clip.resized(height=target_h)
        bg = bg.image_transform(lambda frame: _blur_frame_fast(frame, blur_radius))
        bg = bg.cropped(x_center=0.5, y_center=0.5, width=target_w, height=target_h)

        fg = clip.resized(width=target_w)
        fg = fg.with_position("center")
        fg = fg.with_duration(clip.duration)
        bg = bg.with_duration(clip.duration)
        return CompositeVideoClip([bg, fg], size=(target_w, target_h))

    resized = clip.resized(height=target_h)
    return resized.cropped(x_center=0.5, y_center=0.5, width=target_w, height=target_h)


def add_watermark(clip, config):
    if not config.get("enabled", False):
        return clip

    wm_type = config.get("type", "text")
    position = _normalize_position(config.get("position", "bottom-right"))
    opacity = float(config.get("opacity", 0.7))

    if wm_type == "text":
        font = _resolve_font_path(config)
        watermark = TextClip(
            text=config.get("text", ""),
            font=font,
            font_size=int(config.get("fontsize", 48)),
            color=config.get("color", "white"),
            stroke_color="black",
            stroke_width=2,
        )
    else:
        image_path = config.get("image_path", "")
        if not image_path or not os.path.exists(image_path):
            return clip
        watermark = ImageClip(image_path).resized(height=int(config.get("height", 100)))

    watermark = watermark.with_opacity(opacity)
    watermark = watermark.with_position(position)
    watermark = watermark.with_duration(clip.duration)
    return CompositeVideoClip([clip, watermark])


def mix_audio(clip, config):
    if not config:
        return clip

    music_path = config.get("music_path", "")
    music_volume = float(config.get("music_volume", 0.25))
    original_volume = float(config.get("original_volume", 1.0))

    original = clip.audio
    if original is not None:
        original = original.with_volume_scaled(original_volume)

    if music_path and os.path.exists(music_path):
        music = AudioFileClip(music_path)
        if music.duration < clip.duration:
            n_loops = int(clip.duration / music.duration) + 1
            music = concatenate_audioclips([music] * n_loops)
        music = music.subclipped(0, clip.duration)
        music = music.with_volume_scaled(music_volume)
        final_audio = CompositeAudioClip([original, music]) if original else music
        clip = clip.with_audio(final_audio)
    elif original is not None:
        clip = clip.with_audio(original)

    return clip


def apply_fades(clip, config):
    fade_in = float(config.get("fade_in", 0))
    fade_out = float(config.get("fade_out", 0))

    if fade_in > 0:
        clip = clip.with_effects([vfx.FadeIn(fade_in)])
    if fade_out > 0:
        clip = clip.with_effects([vfx.FadeOut(fade_out)])

    if clip.audio is not None:
        audio = clip.audio
        audio_effects = []
        if fade_in > 0:
            audio_effects.append(afx.AudioFadeIn(fade_in))
        if fade_out > 0:
            audio_effects.append(afx.AudioFadeOut(fade_out))
        if audio_effects:
            audio = audio.with_effects(audio_effects)
            clip = clip.with_audio(audio)

    return clip


def process_clip(clip, editor_options):
    if not editor_options:
        return clip

    if editor_options.get("aspect_ratio") == "9:16":
        clip = render_vertical_9_16(
            clip,
            blur_bg=editor_options.get("blur_background", True),
            blur_radius=int(editor_options.get("blur_radius", BLUR_RADIUS_DEFAULT)),
        )

    if "watermark" in editor_options:
        clip = add_watermark(clip, editor_options["watermark"])

    if "audio" in editor_options:
        clip = mix_audio(clip, editor_options["audio"])

    if "fade" in editor_options:
        clip = apply_fades(clip, editor_options["fade"])

    return clip


def generate_preview_frame(video_path, editor_options, t=None):
    with VideoFileClip(video_path) as clip:
        if t is None:
            t = clip.duration / 2
        frame = clip.get_frame(t)

    if not editor_options:
        return Image.fromarray(frame)

    if editor_options.get("aspect_ratio") == "9:16":
        frame = _render_vertical_frame(
            frame,
            blur_bg=editor_options.get("blur_background", True),
            blur_radius=int(editor_options.get("blur_radius", BLUR_RADIUS_DEFAULT)),
        )

    if "watermark" in editor_options:
        wm_cfg = editor_options["watermark"]
        if wm_cfg.get("enabled", False) and wm_cfg.get("type") == "text":
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img)
            font_path = _resolve_font_path(wm_cfg)
            try:
                font = ImageFont.truetype(font_path, int(wm_cfg.get("fontsize", 48)))
            except Exception:
                font = ImageFont.load_default()
            text = wm_cfg.get("text", "")
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            iw, ih = img.size
            opacity = int(float(wm_cfg.get("opacity", 0.7)) * 255)
            pos = wm_cfg.get("position", "bottom-right")
            pad = 20
            pos_map = {
                "bottom-right": (iw - tw - pad, ih - th - pad),
                "bottom-left": (pad, ih - th - pad),
                "top-right": (iw - tw - pad, pad),
                "top-left": (pad, pad),
                "center": ((iw - tw) // 2, (ih - th) // 2),
            }
            x, y = pos_map.get(pos, pos_map["bottom-right"])
            draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
            frame = np.array(img)
        elif wm_cfg.get("enabled", False) and wm_cfg.get("type") == "image":
            image_path = wm_cfg.get("image_path", "")
            if image_path and os.path.exists(image_path):
                img = Image.fromarray(frame).convert("RGBA")
                overlay = Image.open(image_path).convert("RGBA")
                target_h = int(wm_cfg.get("height", 100))
                scale = target_h / max(overlay.height, 1)
                target_w = max(1, int(overlay.width * scale))
                overlay = overlay.resize((target_w, target_h), Image.LANCZOS)
                opacity = int(float(wm_cfg.get("opacity", 0.7)) * 255)
                if opacity < 255:
                    alpha = overlay.getchannel("A").point(lambda a: int(a * opacity / 255))
                    overlay.putalpha(alpha)
                x, y = _get_preview_overlay_xy(img.size, overlay.size, wm_cfg.get("position", "bottom-right"))
                img.alpha_composite(overlay, (x, y))
                frame = np.array(img.convert("RGB"))

    return Image.fromarray(frame)


VIDEO_WRITE_KWARGS = dict(
    codec="libx264",
    audio_codec="aac",
    fps=None,
    audio_fps=None,
    logger=None,
    threads=os.cpu_count() or 4,
    preset="fast",
    ffmpeg_params=["-movflags", "+faststart"],
)
