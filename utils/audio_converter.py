import io
import subprocess
from pydub import AudioSegment

def convert_stream_to_ulaw(mp3_stream: io.BytesIO) -> bytes:
    try:
        audio_segment = AudioSegment.from_file(mp3_stream, format="mp3")
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        process = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-ar", "8000", "-ac", "1", "-acodec", "pcm_mulaw", "-f", "mulaw", "pipe:1"],
            input=wav_buffer.read(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if process.returncode == 0:
            print("✅ Audio converted to μ-law")
            return process.stdout
        else:
            print("⚠️ FFmpeg error:", process.stderr.decode())
            return b""
    except Exception as e:
        print(f"⚠️ Conversion error: {e}")
        return b""
