import pyaudio
import wave
from pymongo import MongoClient
import tkinter as tk
import threading
import pygame
import io
import tempfile

class VoiceRecorder:
    def __init__(self):
        self.chunk = 1024  
        self.sample_format = pyaudio.paInt16  
        self.channels = 2  
        self.fs = 44100  
        self.p = pyaudio.PyAudio()
        self.recording = False
        self.audio_data = []
        self.recording_name = "default_recording.wav"  

        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['voice_recordings']
        self.collection = self.db['recordings']

        pygame.mixer.init()

        self.create_gui()

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Voice Recorder")
        self.root.geometry("400x500")  
        self.root.configure(bg="#f0f0f0")  

        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(pady=20)

        
        self.filename_label = tk.Label(frame, text="Enter Recording Filename:", bg="#f0f0f0", font=("Helvetica", 10))
        self.filename_label.pack(pady=5)

        self.filename_entry = tk.Entry(frame, width=30, font=("Helvetica", 12))
        self.filename_entry.pack(pady=5)
        self.filename_entry.insert(0, self.recording_name)  
        
        self.toggle_button = tk.Button(frame, text="Start Recording", command=self.toggle_recording, bg="#4CAF50", fg="white", font=("Helvetica", 12), relief=tk.GROOVE)
        self.toggle_button.pack(pady=10)

        
        self.list_button = tk.Button(frame, text="List Recordings", command=self.list_recordings, bg="#2196F3", fg="white", font=("Helvetica", 12), relief=tk.GROOVE)
        self.list_button.pack(pady=10)

        
        self.recordings_listbox = tk.Listbox(self.root, width=50, height=10, font=("Helvetica", 10))
        self.recordings_listbox.pack(pady=10)

        
        self.play_button = tk.Button(self.root, text="Play Selected Recording", command=self.play_selected_recording, bg="#FF9800", fg="white", font=("Helvetica", 12), relief=tk.GROOVE)
        self.play_button.pack(pady=10)

        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recording = True
        self.audio_data = []
        self.toggle_button.config(text="Stop Recording")
        
        
        self.recording_name = self.filename_entry.get() or "default_recording.wav"
        
        threading.Thread(target=self.record_audio, daemon=True).start()

    def record_audio(self):
        print("Recording started...")
        stream = self.p.open(format=self.sample_format,
                             channels=self.channels,
                             rate=self.fs,
                             frames_per_buffer=self.chunk,
                             input=True)

        while self.recording:
            data = stream.read(self.chunk)
            self.audio_data.append(data)

        stream.stop_stream()
        stream.close()
        self.save_to_mongodb()

    def stop_recording(self):
        self.recording = False
        self.toggle_button.config(text="Start Recording")
        print("Recording stopped.")

    def save_to_mongodb(self):
        
        audio_buffer = io.BytesIO()
        wf = wave.open(audio_buffer, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.audio_data))
        wf.close()

        
        audio_buffer.seek(0)

       
        audio_content = audio_buffer.read()
        audio_document = {
            "filename": self.recording_name,  
            "data": audio_content
        }
        self.collection.insert_one(audio_document)

        print("Audio saved to MongoDB.")
        audio_buffer.close()  

    def list_recordings(self):
        self.recordings_listbox.delete(0, tk.END)  
        recordings = self.collection.find()
        for recording in recordings:
            self.recordings_listbox.insert(tk.END, recording['filename'])  

    def play_selected_recording(self):
        selected_index = self.recordings_listbox.curselection()
        if selected_index:
            selected_recording = self.recordings_listbox.get(selected_index)

            
            recording = self.collection.find_one({"filename": selected_recording})
            if recording:
                audio_data = recording['data']

                
                audio_buffer = io.BytesIO(audio_data)
                audio_buffer.seek(0)

                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_filename = temp_file.name
                    temp_file.write(audio_buffer.read())

                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()

                print(f"Playing: {selected_recording}")

    def on_closing(self):
        if self.recording:
            self.stop_recording()
        self.p.terminate()
        pygame.mixer.quit()
        self.root.destroy()

if __name__ == "__main__":
    VoiceRecorder()
