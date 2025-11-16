import logging
from io import BytesIO
from faster_whisper import WhisperModel
from config import config

logger = logging.getLogger(__name__)

# Singleton для модели Whisper (инициализируется один раз)
_whisper_model = None


def get_whisper_model() -> WhisperModel:
    """Получить или создать экземпляр модели Whisper (singleton)."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(
            f"Initializing Faster-Whisper model: {config.WHISPER_MODEL} "
            f"on {config.WHISPER_DEVICE} with {config.WHISPER_COMPUTE_TYPE}"
        )
        _whisper_model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE
        )
        logger.info("Faster-Whisper model initialized successfully")
    return _whisper_model


async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Транскрибировать аудио в текст с помощью Faster-Whisper.
    
    Args:
        audio_bytes: Байты аудио файла (поддерживаются форматы: ogg, mp3, wav, и др.)
    
    Returns:
        Транскрибированный текст
    """
    try:
        model = get_whisper_model()
        
        # Создаем BytesIO объект для передачи в модель
        audio_file = BytesIO(audio_bytes)
        
        # Транскрибация с автоматическим определением языка (русский приоритет)
        segments, info = model.transcribe(
            audio_file,
            language="ru",  # Указываем русский язык
            beam_size=5,
            vad_filter=True,  # Voice Activity Detection для лучшего качества
        )
        
        # Собираем текст из всех сегментов
        text = " ".join([segment.text for segment in segments])
        
        logger.info(
            f"Audio transcribed successfully. "
            f"Detected language: {info.language} "
            f"(probability: {info.language_probability:.2f})"
        )
        logger.info(f"Transcribed text: {text}")
        
        return text.strip()
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        raise
