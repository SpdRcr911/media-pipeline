import os
import sys

from faster_whisper import WhisperModel

from summarize import summarize_transcript


def transcribe(input_file: str, output_dir: str = "/output") -> str:
    filename = os.path.basename(input_file)
    base_name = os.path.splitext(filename)[0]
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, base_name + ".txt")

    if os.path.exists(output_file):
        print(f"\n[SKIP] Transcript already exists at {output_file}.")
        print("Bypassing faster-whisper and proceeding directly to summarization...")
        return output_file

    print(f"\n[START] No existing transcript found. Starting transcription for {filename}...")

    model_size = "large-v3"
    print(f"Loading '{model_size}' model onto GPU...")
    model = WhisperModel(model_size, device="cuda", compute_type="float16")

    print(f"Transcribing: {filename}...")
    segments, info = model.transcribe(input_file, beam_size=5)
    print(f"Detected language: '{info.language}' (Probability: {info.language_probability:.2f})")

    with open(output_file, "w", encoding="utf-8") as f:
        for segment in segments:
            line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
            print(line, end="")
            f.write(line)

    print(f"\nTranscription complete. Saved to: {output_file}")
    return output_file


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <path_to_video>")
        return 1

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return 1

    output_file = transcribe(input_file)
    return 0 if summarize_transcript(output_file) else 1


if __name__ == "__main__":
    sys.exit(main())
