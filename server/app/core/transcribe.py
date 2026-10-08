"""服务端语音转写:基于 faster-whisper,模型懒加载,失败时返回空字符串不影响上传。"""
import os
from pathlib import Path

_model = None
_model_name = os.environ.get("WHISPER_MODEL", "base")
_cache_dir = os.environ.get("WHISPER_CACHE", "")


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        kwargs = {"device": "cpu", "compute_type": "int8"}
        if _cache_dir:
            Path(_cache_dir).mkdir(parents=True, exist_ok=True)
            kwargs["download_root"] = _cache_dir
        _model = WhisperModel(_model_name, **kwargs)
    return _model


def transcribe(audio_path: Path, language: str | None = None) -> str:
    """转写音频文件,返回纯文本;language=None 自动检测;任何失败都返回空串。"""
    try:
        model = _get_model()
        segments, _ = model.transcribe(str(audio_path), language=language, vad_filter=True)
        return "".join(s.text for s in segments).strip()
    except Exception:
        return ""
