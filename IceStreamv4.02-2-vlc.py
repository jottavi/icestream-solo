import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
import subprocess
import threading
import json
import wave
import sounddevice as sd
import numpy as np

class AudioStreamer:
    def __init__(self, master):
        self.master = master
        self.master.title("IceStream-Solo by Apo33 - Audio Streamer and Player GUI")

        title_frame = tk.Frame(master)
        title_frame.pack(pady=5)

        title_label = tk.Label(title_frame, text="IceStream-Solo by Apo33", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT, padx=5)

        link_label = tk.Label(title_frame, text="Visit Apo33", fg="blue", cursor="hand2")
        link_label.pack(side=tk.LEFT, padx=5)
        link_label.bind("<Button-1>", lambda e: self.open_link("http://apo33.org"))

        self.stream_process = None
        self.play_process = None
        self.recording = False
        self.fs = 44100  # Default sample rate
        self.recorded_audio = []
        self.vu_meter_running = False

        self.notebook = ttk.Notebook(master)
        self.stream_tab = ttk.Frame(self.notebook)
        self.play_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.stream_tab, text="Streamer")
        self.notebook.add(self.play_tab, text="Player")
        self.notebook.pack(expand=True, fill="both")

        self.setup_stream_tab()
        self.setup_play_tab()

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

    def setup_stream_tab(self):
        # Stream Tab Widgets
        ttk.Label(self.stream_tab, text="Icecast2 Server:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.server_entry = ttk.Entry(self.stream_tab, width=40)
        self.server_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Port:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.port_entry = ttk.Entry(self.stream_tab, width=40)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Password:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.password_entry = ttk.Entry(self.stream_tab, width=40, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Mount Point:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.mount_entry = ttk.Entry(self.stream_tab, width=40)
        self.mount_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Metadata (Title):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.metadata_title_entry = ttk.Entry(self.stream_tab, width=40)
        self.metadata_title_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Metadata (Description):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.metadata_desc_entry = ttk.Entry(self.stream_tab, width=40)
        self.metadata_desc_entry.grid(row=5, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Metadata (Genre):").grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.metadata_genre_entry = ttk.Entry(self.stream_tab, width=40)
        self.metadata_genre_entry.grid(row=6, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Bitrate (kbps):").grid(row=7, column=0, sticky="e", padx=5, pady=5)
        self.bitrate_choice = ttk.Combobox(self.stream_tab, values=["96", "128", "192", "256", "320"], state="readonly")
        self.bitrate_choice.set("128")
        self.bitrate_choice.grid(row=7, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Audio Device:").grid(row=8, column=0, sticky="e", padx=5, pady=5)
        self.device_entry = ttk.Entry(self.stream_tab, width=40)
        self.device_entry.insert(0, "default")
        self.device_entry.grid(row=8, column=1, padx=5, pady=5)

        ttk.Label(self.stream_tab, text="Sound Driver:").grid(row=9, column=0, sticky="e", padx=5, pady=5)
        self.driver_choice = ttk.Combobox(self.stream_tab, values=["alsa", "jack", "oss"])
        self.driver_choice.set("alsa")
        self.driver_choice.grid(row=9, column=1, padx=5, pady=5)

        ttk.Button(self.stream_tab, text="Save Configuration", command=self.save_configuration).grid(row=10, column=0, padx=5, pady=10)
        ttk.Button(self.stream_tab, text="Load Configuration", command=self.load_configuration).grid(row=10, column=1, padx=5, pady=10)

        ttk.Button(self.stream_tab, text="Start Streaming", command=self.start_streaming).grid(row=11, column=0, padx=5, pady=10)
        self.stop_stream_button = ttk.Button(self.stream_tab, text="Stop Streaming", command=self.stop_streaming, state="disabled")
        self.stop_stream_button.grid(row=11, column=1, padx=5, pady=10)

        ttk.Button(self.stream_tab, text="Start Recording", command=self.start_recording).grid(row=12, column=0, padx=5, pady=10)
        self.stop_record_button = ttk.Button(self.stream_tab, text="Stop Recording", command=self.stop_recording, state="disabled")
        self.stop_record_button.grid(row=12, column=1, padx=5, pady=10)

        ttk.Label(self.stream_tab, text="Stream Logs:").grid(row=13, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        self.stream_log = scrolledtext.ScrolledText(self.stream_tab, width=70, height=15, state="disabled")
        self.stream_log.grid(row=14, column=0, columnspan=2, padx=5, pady=5)

    def setup_play_tab(self):
        # Player Tab Widgets
        ttk.Label(self.play_tab, text="Stream URL:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.stream_url_entry = ttk.Entry(self.play_tab, width=40)
        self.stream_url_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(self.play_tab, text="Play", command=self.start_playing).grid(row=1, column=0, padx=5, pady=10)
        self.stop_play_button = ttk.Button(self.play_tab, text="Stop", command=self.stop_playing, state="disabled")
        self.stop_play_button.grid(row=1, column=1, padx=5, pady=10)

        ttk.Label(self.play_tab, text="Playback Logs:").grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        self.play_log = scrolledtext.ScrolledText(self.play_tab, width=70, height=15, state="disabled")
        self.play_log.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        ttk.Label(self.play_tab, text="VU Meter:").grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        self.vu_meter = tk.Canvas(self.play_tab, width=200, height=50, bg="black")
        self.vu_meter.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

    def save_configuration(self):
        config = {
            "server": self.server_entry.get(),
            "port": self.port_entry.get(),
            "password": self.password_entry.get(),
            "mount": self.mount_entry.get(),
            "title": self.metadata_title_entry.get(),
            "description": self.metadata_desc_entry.get(),
            "genre": self.metadata_genre_entry.get(),
            "bitrate": self.bitrate_choice.get(),
            "device": self.device_entry.get(),
            "driver": self.driver_choice.get()
        }
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            with open(filepath, "w") as f:
                json.dump(config, f)
            self.log_message(self.stream_log, f"Configuration saved to {filepath}")

    def load_configuration(self):
        filepath = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            with open(filepath, "r") as f:
                config = json.load(f)
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, config.get("server", ""))
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, config.get("port", ""))
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, config.get("password", ""))
            self.mount_entry.delete(0, tk.END)
            self.mount_entry.insert(0, config.get("mount", ""))
            self.metadata_title_entry.delete(0, tk.END)
            self.metadata_title_entry.insert(0, config.get("title", ""))
            self.metadata_desc_entry.delete(0, tk.END)
            self.metadata_desc_entry.insert(0, config.get("description", ""))
            self.metadata_genre_entry.delete(0, tk.END)
            self.metadata_genre_entry.insert(0, config.get("genre", ""))
            self.bitrate_choice.set(config.get("bitrate", "128"))
            self.device_entry.delete(0, tk.END)
            self.device_entry.insert(0, config.get("device", ""))
            self.driver_choice.set(config.get("driver", "alsa"))
            self.log_message(self.stream_log, f"Configuration loaded from {filepath}")

    def start_streaming(self):
        server = self.server_entry.get()
        port = self.port_entry.get()
        password = self.password_entry.get()
        mount = self.mount_entry.get()
        bitrate = self.bitrate_choice.get()
        device = self.device_entry.get()
        driver = self.driver_choice.get()

        if not server or not port or not password or not mount:
            messagebox.showerror("Error", "All fields are required for streaming!")
            return

        ffmpeg_command = [
            "ffmpeg",
            "-f", driver,  # Use the selected driver
            "-i", device,  # Specify the input device
            "-ac", "2",  # Stereo audio
            "-ar", "44100",  # Sample rate
            "-b:a", f"{bitrate}k",  # Bitrate
            "-content_type", "audio/mpeg",  # Content type
            "-metadata", f"title={self.metadata_title_entry.get()}",
            "-metadata", f"description={self.metadata_desc_entry.get()}",
            "-metadata", f"genre={self.metadata_genre_entry.get()}",
            "-f", "mp3",  # Output format
            f"icecast://source:{password}@{server}:{port}/{mount}"
        ]

        try:
            self.stream_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.stop_stream_button.config(state="normal")

            threading.Thread(target=self.monitor_process, args=(self.stream_process, self.stream_log)).start()
            self.log_message(self.stream_log, "Streaming started...")
        except Exception as e:
            self.log_message(self.stream_log, f"Error starting streaming: {e}")

    def stop_streaming(self):
        if self.stream_process:
            self.stream_process.terminate()
            self.stream_process = None
            self.log_message(self.stream_log, "Streaming stopped.")
        self.stop_stream_button.config(state="disabled")

    def start_recording(self):
        self.recording = True
        self.recorded_audio = []
        self.stop_record_button.config(state="normal")
        threading.Thread(target=self.record_audio).start()
        self.log_message(self.stream_log, "Recording started...")

    def record_audio(self):
        try:
            with sd.InputStream(samplerate=self.fs, channels=2, callback=self.audio_callback):
                while self.recording:
                    sd.sleep(100)
        except Exception as e:
            self.log_message(self.stream_log, f"Recording error: {e}")

    def audio_callback(self, indata, frames, time, status):
        if self.recording:
            self.recorded_audio.append(indata.copy())

    def stop_recording(self):
        self.recording = False
        self.stop_record_button.config(state="disabled")
        filepath = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if filepath:
            with wave.open(filepath, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(self.fs)
                wf.writeframes(b"".join([chunk.tobytes() for chunk in self.recorded_audio]))
            self.log_message(self.stream_log, f"Recording saved to {filepath}")

    def start_playing(self):
        stream_url = self.stream_url_entry.get()
        if not stream_url:
            messagebox.showerror("Error", "Stream URL is required!")
            return

        # Use VLC for playback
        vlc_command = ["cvlc", "--aout", "jack", stream_url, "--no-video"]
        try:
            self.play_process = subprocess.Popen(vlc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.stop_play_button.config(state="normal")
            self.vu_meter_running = True
            threading.Thread(target=self.monitor_vu_meter).start()
            threading.Thread(target=self.monitor_process, args=(self.play_process, self.play_log)).start()
            self.log_message(self.play_log, "Playback started with VLC using JACK...")
        except Exception as e:
            self.log_message(self.play_log, f"Error starting playback: {e}")

    def stop_playing(self):
        if self.play_process:
            self.play_process.terminate()
            self.play_process = None
            self.log_message(self.play_log, "Playback stopped.")
        self.vu_meter_running = False
        self.stop_play_button.config(state="disabled")

    def monitor_process(self, process, log_widget):
        try:
            for line in iter(process.stderr.readline, b''):
                decoded_line = line.decode('utf-8', errors='replace').strip()
                self.log_message(log_widget, decoded_line)
        except Exception as e:
            self.log_message(log_widget, f"Error in monitoring process: {e}")

    def monitor_vu_meter(self):
        while self.vu_meter_running:
            try:
                # Simulated VU meter value
                value = np.random.randint(0, 200)
                self.vu_meter.delete("all")
                self.vu_meter.create_rectangle(0, 50 - value / 2, 200, 50, fill="green")
                self.master.update_idletasks()
                self.master.after(100)
            except Exception as e:
                self.log_message(self.play_log, f"Error updating VU Meter: {e}")
                break

    def log_message(self, log_widget, message):
        log_widget.config(state="normal")
        log_widget.insert("end", message + "\n")
        log_widget.see("end")
        log_widget.config(state="disabled")

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = AudioStreamer(root)
    root.mainloop()

