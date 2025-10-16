# 🎙️ AI Meeting Summarizer

An AI-powered tool that automatically transcribes, translates, and summarizes meeting recordings using advanced speech and language models.

## 🎥 Demo Video

[![AI Meeting Summarizer Demo](https://img.shields.io/badge/📺-Watch_Demo_Video-red?style=for-the-badge&logo=google-drive)](https://drive.google.com/file/d/1viUEwyPAsReyoWM7rEpQvx95IBtNEzIa/view?usp=sharing))

*Click above to watch the demo video showing the complete workflow*

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Core Language** | Python | Application logic and workflow |
| **AI API** | Groq API | Access to Whisper & LLaMA models |
| **Speech-to-Text** | whisper-large-v3 | Audio to text conversion |
| **Language Model** | llama-3.3-70b-versatile | Text summarization |
| **Audio Processing** | pydub | Split long audio files |
| **Web Interface** | gradio | Browser-based UI |
| **File Management** | os, shutil | Handle local files |
| **Progress Tracking** | gr.Progress() | Visual progress indicators |

## 🔄 Process Flow

### 1. **Audio Upload**
- User uploads audio file (.mp3, .wav, .m4a)
- Through Gradio web interface

### 2. **Audio Splitting**
- Split into 10-minute chunks using pydub
- Temporary storage in `/chunks` folder

### 3. **Transcription**
- Process each chunk with Whisper model
- Save transcripts in `/translations` folder
- Built-in caching system

### 4. **Transcript Assembly**
- Combine all chunks into `full_transcript.txt`

### 5. **AI Summarization**
- LLaMA-3.3-70B generates structured summary:
  - Key discussion points
  - Decisions made
  - Action items
  - Important announcements

### 6. **Output & Download**
- Display in Gradio interface
- Downloadable files:
  - `full_transcript.txt`
  - `summary.txt`

## 📊 Workflow Diagram

```
Audio File Upload
        ↓
Split into 10-min Chunks
        ↓
Whisper Transcription
        ↓
Combine Transcripts
        ↓
LLaMA Summarization
        ↓
Display & Download Results
```

---

