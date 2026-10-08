"""服务端语音转写:基于 faster-whisper,模型懒加载,失败时返回空字符串不影响上传。"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

_model = None
# small 比 base 中文准确率高很多;可用环境变量覆盖(tiny/base/small/medium)
_model_name = os.environ.get("WHISPER_MODEL", "small")
_cache_dir = os.environ.get("WHISPER_CACHE", "")

# 专用于转写的单线程池:串行执行,避免多个转写并发把 CPU 打满、拖垮 login 等 IO 请求。
# faster-whisper 的 model 实例非线程安全,串行也避免了并发调用同一实例的坑。
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")


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
        segments, _ = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
            # 提示模型输出简体中文并正确使用标点
            initial_prompt="以下是普通话的句子,请使用简体中文和正确的标点符号。",
        )
        return "".join(s.text for s in segments).strip()
    except Exception:
        return ""


def submit_transcribe(note_id: int, audio_path: Path, language: str | None = None) -> None:
    """提交后台转写任务:fire-and-forget,在单线程池里串行跑,完成后回写 note.text。

    设计要点:
    - 不阻塞调用方(POST /notes 立即返回,text 先留空)。
    - 单线程串行,避免 CPU 被多个转写打满,影响 login 等 IO 请求。
    - 失败静默(text 保持空),与原同步行为一致。
    - 重新 import 是为了延迟加载 DB 层,避免循环引用。
    """
    _executor.submit(_run_transcribe, note_id, audio_path, language)


def _run_transcribe(note_id: int, audio_path: Path, language: str | None = None) -> None:
    try:
        text = transcribe(audio_path, language)
        if text:
            from app.database import SessionLocal
            from app.models import Note

            db = SessionLocal()
            try:
                db.query(Note).filter(Note.id == note_id).update(
                    {Note.text: text, Note.updated_at: datetime.utcnow()}
                )
                db.commit()
            finally:
                db.close()
    except Exception:
        # 后台任务失败不影响数据完整性,音频已存,text 留空即可
        pass
