import os
import math
import time
import shutil
from pydub import AudioSegment
from groq import Groq
import gradio as gr

# Initialize Groq client
client = Groq(api_key="****************")

# === CONFIGURATION ===
CHUNKS_DIR = "chunks"
TRANSLATIONS_DIR = "translations"
CHUNK_LENGTH_MS = 10 * 60 * 1000  # 10 minutes

# === Helper Functions ===
def countdown(seconds):
    """Show a countdown timer"""
    for remaining in range(int(seconds), 0, -1):
        mins, secs = divmod(remaining, 60)
        timer = f'{mins:02d}:{secs:02d}'
        yield f"⏳ Waiting for rate limit reset: {timer} remaining..."
        time.sleep(1)
    yield "✅ Wait complete! Resuming..."

def split_audio(path, progress=gr.Progress()):
    """Split audio into chunks"""
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    
    progress(0, desc="Loading audio file...")
    audio = AudioSegment.from_file(path)
    total_chunks = math.ceil(len(audio) / CHUNK_LENGTH_MS)
    
    progress(0.1, desc=f"Splitting into {total_chunks} chunks...")
    
    for i in range(total_chunks):
        start = i * CHUNK_LENGTH_MS
        end = start + CHUNK_LENGTH_MS
        chunk = audio[start:end]
        chunk_filename = f"chunk_{i+1:03}.mp3"
        chunk_path = os.path.join(CHUNKS_DIR, chunk_filename)
        
        if not os.path.exists(chunk_path):
            chunk.export(chunk_path, format="mp3")
        
        progress((i + 1) / total_chunks * 0.2, desc=f"Created chunk {i+1}/{total_chunks}")
    
    return total_chunks

def translate_chunks(progress=gr.Progress()):
    """Translate all chunks"""
    os.makedirs(TRANSLATIONS_DIR, exist_ok=True)
    results = []
    
    chunk_files = sorted([f for f in os.listdir(CHUNKS_DIR) if f.endswith(".mp3")])
    total_files = len(chunk_files)
    
    for idx, file_name in enumerate(chunk_files):
        file_path = os.path.join(CHUNKS_DIR, file_name)
        translation_file = os.path.join(TRANSLATIONS_DIR, file_name.replace(".mp3", ".txt"))
        
        # Skip if already translated
        if os.path.exists(translation_file):
            progress(0.2 + (idx / total_files) * 0.6, desc=f"Loading cached: {file_name}")
            with open(translation_file, "r", encoding="utf-8") as f:
                text = f.read()
            results.append(f"\n--- {file_name} ---\n{text}")
            continue
        
        # Translate with retry
        max_retries = 5
        for attempt in range(max_retries):
            try:
                progress(0.2 + (idx / total_files) * 0.6, desc=f"Translating {file_name} ({idx+1}/{total_files})...")
                
                with open(file_path, "rb") as f:
                    translation = client.audio.translations.create(
                        file=f,
                        model="whisper-large-v3",
                        response_format="json",
                        temperature=0
                    )
                
                text = translation.text.strip()
                
                # Save immediately
                with open(translation_file, "w", encoding="utf-8") as out:
                    out.write(text)
                
                results.append(f"\n--- {file_name} ---\n{text}")
                time.sleep(2)
                break
                
            except Exception as e:
                error_msg = str(e)
                
                # Handle rate limit
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = 180
                    
                    try:
                        import re
                        match = re.search(r'(\d+)m([\d.]+)s', error_msg)
                        if match:
                            wait_time = int(match.group(1)) * 60 + float(match.group(2))
                    except:
                        pass
                    
                    wait_time = int(wait_time) + 10
                    
                    # Show countdown in progress
                    for msg in countdown(wait_time):
                        progress(0.2 + (idx / total_files) * 0.6, desc=msg)
                    continue
                
                # Other errors
                if attempt < max_retries - 1:
                    progress(0.2 + (idx / total_files) * 0.6, desc=f"Retrying {file_name}...")
                    time.sleep(10)
                else:
                    results.append(f"\n--- {file_name} ---\n[TRANSLATION FAILED: {error_msg}]")
                    break
    
    return "\n".join(results)

def summarize_text(text, progress=gr.Progress()):
    """Generate summary"""
    progress(0.9, desc="Generating summary...")
    
    prompt = f"""You are an expert at summarizing council meeting transcripts. 
Please provide a comprehensive summary of the following meeting transcript.

Include:
- Key discussion points
- Important decisions made
- Action items
- Any significant announcements

Transcript:
{text}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates clear, structured summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    except Exception as e:
        return f"⚠️ Summary generation failed: {str(e)}"

# === Main Processing Function ===
def process_audio(audio_file, progress=gr.Progress()):
    """Main function to process audio and return transcript + summary"""
    
    if audio_file is None:
        return "❌ Please upload an audio file", "", None, None
    
    try:
        # Clean up previous runs
        if os.path.exists(CHUNKS_DIR):
            shutil.rmtree(CHUNKS_DIR)
        if os.path.exists(TRANSLATIONS_DIR):
            shutil.rmtree(TRANSLATIONS_DIR)
        
        progress(0, desc="Starting processing...")
        
        # Step 1: Split audio
        total_chunks = split_audio(audio_file, progress)
        
        # Step 2: Translate chunks
        full_transcript = translate_chunks(progress)
        
        # Step 3: Generate summary
        summary = summarize_text(full_transcript, progress)
        
        progress(1.0, desc="✅ Complete!")
        
        # Save to files for download
        transcript_file = "full_transcript.txt"
        summary_file = "summary.txt"
        
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(full_transcript)
        
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        return (
            f"✅ Processed {total_chunks} chunks successfully!",
            full_transcript,
            summary,
            transcript_file,
            summary_file
        )
        
    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", None, None

# === Gradio Interface ===
with gr.Blocks(theme=gr.themes.Soft(), title="Audio Transcription & Summary") as demo:
    
    gr.Markdown("""
    # 🎙️ Audio Transcription & Summarization
    Upload an audio file (MP3, M4A, WAV, etc.) to get a full transcript and AI-generated summary.
    
    **Note:** Processing may take several minutes depending on audio length. Rate limits may cause delays.
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            audio_input = gr.Audio(
                label="Upload Audio File",
                type="filepath",
                sources=["upload"]
            )
            
            process_btn = gr.Button("🚀 Process Audio", variant="primary", size="lg")
            
            status_output = gr.Textbox(
                label="Status",
                interactive=False,
                lines=2
            )
    
    with gr.Tabs():
        with gr.Tab("📝 Summary"):
            summary_output = gr.Textbox(
                label="AI-Generated Summary",
                lines=15,
                interactive=False
            )
            summary_download = gr.File(label="Download Summary")
        
        with gr.Tab("📄 Full Transcript"):
            transcript_output = gr.Textbox(
                label="Complete Transcript",
                lines=20,
                interactive=False
            )
            transcript_download = gr.File(label="Download Transcript")
    
    # Button action
    process_btn.click(
        fn=process_audio,
        inputs=[audio_input],
        outputs=[
            status_output,
            transcript_output,
            summary_output,
            transcript_download,
            summary_download
        ]
    )
    
    gr.Markdown("""
    ---
    ### 💡 Tips:
    - Supports formats: MP3, M4A, WAV, FLAC, etc.
    - Long files are automatically split into 10-minute chunks
    - Progress is saved - you can re-run if interrupted
    - Rate limits: Max ~2 hours per hour of processing
    """)

# Launch the app
if __name__ == "__main__":
    demo.launch(share=False)  # Set share=True to create public link