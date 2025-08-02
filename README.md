# RealTimeAdvisor Overlay

A lightweight Windows application that displays a semi-transparent “floating” window on top of all programs, captures system audio (client’s voice) and microphone (advisor’s voice), transcribes the conversation, and lets you send the current context to an LLM (Cohere) for live suggestions directly in the interface.

---

## 📦 Features

- **Floating Overlay** — semi-transparent, minimalistic design that stays on top of all windows.  
- **Speech Transcription**  
  - **Inputs:**  
    - _CABLE-A Output_ — client (system audio)  
    - _Headset Microphone_ — advisor (mic)  
  - Automatically switches audio devices via `nircmdc.exe`.  
  - Logs saved to `log_YYYYMMDD.txt`.  
- **LLM Chat**  
  - **GPT** button opens a companion panel to the right of the main window.  
  - The “Ask…” field accepts your custom query or, if left empty, sends the entire transcription context.  
  - Responses stream in real time and the window grows downward as new content arrives.  
- **Interface Controls**  
  - “Listen/Stop” button  
  - “Hide/Show Transcript” toggle  
  - Drag to reposition  
  - “Exit” button

---

## ⚙️ Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KozuyutovAndrey/RealTimeAdvisor.git
   cd RealTimeAdvisor
   
