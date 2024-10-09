import sys
import os
import threading
import time
import json
from datetime import datetime
import customtkinter as ctk
import sounddevice as sd
import numpy as np
import wave
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from transcription import transcribe_and_diarize
from topicrelevance import TopicRelevanceAndClusteringApp
from GdpHttpClient import GdpHttpClient
import pandas as pd
import logging
from PIL import Image, ImageTk  # For Logo icons
import tkinter as tk
from tkinter import ttk, messagebox  # Use standard messagebox as fallback
import queue
import pygame  # For audio playback
import logging

logging.basicConfig(filename='app_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Application started")


matplotlib.use('TkAgg')  # Use TkAgg backend for matplotlib

# Initialize pygame mixer for audio playback
pygame.mixer.init()

class MainApplication(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialize logging
        self.init_logging()

        self.title("Synchronizer 🎛")
        self.geometry("1200x900")  # Increased height to accommodate new widgets

        self.minsize(800, 900) 

        # Set appearance mode and color theme
        ctk.set_appearance_mode("Dark")  # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

        # Initialize variables
        self.IP = ''
        self.PORT = ''
        self.UNIQUE_KEY = '12345abcde'
        self.num_speakers = ctk.IntVar(value=2)
        self.topics = []
        self.selected_models = []
        self.audio_data = None
        self.recording = False
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.start_time = None
        self.message_queue = queue.Queue()
        self.PROCEED = False
        self.connected = False  # Connection status
        self.wifi_icon = None  # Initialize wifi_icon
        self.wifi_icon_label = None  # Initialize wifi_icon_label
        self.logo_photo = None  # Initialize logo_photo
        self.audio_file_path = None  # Path to the recorded audio

        # Initialize UI components
        self.initUI()

    def init_logging(self):
        # Configure the root logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # Capture all levels of logs

        # Create a logging format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Create console handler and set level to debug
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def initUI(self):
        # Create a main frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Configure grid
        for i in range(6):
            main_frame.columnconfigure(i, weight=1)
        for i in range(14):  # Increased rows to accommodate new widgets
            main_frame.rowconfigure(i, weight=1)

        # Logo placeholder replaced with an image
        logo_frame = ctk.CTkFrame(main_frame, corner_radius=10 )
        logo_frame.grid(row=0, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        logo_frame.grid_propagate(False)
        logo_frame.configure(height=100)  # Adjust height for logo

        try:
            logo_image = Image.open("ressources/images/logo.png")  # Ensure you have a 'logo.png' image in your directory
            logo_image = logo_image.resize((200, 60), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = ctk.CTkLabel(logo_frame, image=self.logo_photo, text="" )
            logo_label.grid(row=0, column=0, padx = 5, pady = 20)
            logging.info("Logo image loaded successfully.")
        except Exception as e:
            logo_label = ctk.CTkLabel(logo_frame, text="Logo Placeholder")
            logo_label.grid(row=0, column=0)
            logging.error(f"Failed to load logo image: {e}")

        small_text = "Version 1.0 | Now I won't be on camera Vale.. 😔"
        text_label = ctk.CTkLabel(logo_frame, text=small_text, font=("Helvetica", 12))  # Set font to sans serif
        text_label.grid(row=0, column=6, sticky="e", padx=650, pady=20)

        # Adjust for connection widget
        connection_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        connection_frame.grid(row=1, column=0, rowspan=4, columnspan=2, sticky="nw", padx=10, pady=20)
        connection_frame.grid_propagate(False)
        connection_frame.configure(width=370, height=180)

        # Connection inputs inside the connection_frame
        ip_label = ctk.CTkLabel(connection_frame, text="IP Address 💻:", font=("Helvetica", 12))
        self.ip_input = ctk.CTkEntry(connection_frame, font=("Helvetica", 12))
        self.ip_input.insert(0, "10.16.41.121")  # Default IP

        port_label = ctk.CTkLabel(connection_frame, text="Port Number 🎛️ :", font=("Helvetica", 12))
        self.port_input = ctk.CTkEntry(connection_frame, font=("Helvetica", 12))
        self.port_input.insert(0, "8080")  # Default Port

        unique_key_label = ctk.CTkLabel(connection_frame, text="Secret Key 🗝️:", font=("Helvetica", 12))
        self.unique_key_input = ctk.CTkEntry(connection_frame, show="*", font=("Helvetica", 12))
        self.unique_key_input.insert(0, "12345abcde")  # Default Unique Key

        # Increase the width of input fields
        self.ip_input.configure(width=200)
        self.port_input.configure(width=200)
        self.unique_key_input.configure(width=200)

        # Connect button
        self.connect_button = ctk.CTkButton(connection_frame, text="Connect 🔗", command=self.connect_to_server_thread, font=("Helvetica", 12))

        # Connection status indicator using emojis
        self.connection_status_label = ctk.CTkLabel(connection_frame, text="🔴", font=("Helvetica", 16))
        self.connection_status_label.grid(row=3, column=2, padx=5, pady=10, sticky="w")  # Red circle by default

        # Arrange connection widgets using grid
        ip_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ip_input.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        port_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.port_input.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        unique_key_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.unique_key_input.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10, padx=100)

        # Recording status indicator using emojis
        self.recording_status_label = ctk.CTkLabel(main_frame, text="", font=("Helvetica", 16))
        self.recording_status_label.grid(row=1, column=5, padx=5, pady=5, sticky="w")  # Hidden initially

        # Other widgets in the main frame
        num_speakers_label = ctk.CTkLabel(main_frame, text="Number of Speakers:", font=("Helvetica", 12))
        self.num_speakers_slider = ctk.CTkSlider(main_frame, from_=1, to=10, number_of_steps=9, command=self.update_num_speakers)
        self.num_speakers_slider.set(2)
        num_speakers_value_label = ctk.CTkLabel(main_frame, textvariable=self.num_speakers, font=("Helvetica", 12))

        topics_label = ctk.CTkLabel(main_frame, text="Enter Keywords (comma-separated): 📝", font=("Helvetica", 12))
        self.topics_input = ctk.CTkEntry(main_frame, font=("Helvetica", 12))

        models_label = ctk.CTkLabel(main_frame, text="Select Models:", font=("Helvetica", 12))

        # Fixing spacing and resizing the models listbox
        self.models_listbox = ctk.CTkFrame(main_frame)
        self.models_listbox.grid_propagate(False)
        self.models_listbox.configure(width=250, height=120)  # Resize to fit the model checkboxes better

        self.model_vars = []
        models = ['paraphrase-MiniLM-L12-v2', 'paraphrase-mpnet-base-v2', 'all-mpnet-base-v2', 'LaBSE']
        for idx, model in enumerate(models):
            var = ctk.IntVar(value=0)
            checkbox = ctk.CTkCheckBox(self.models_listbox, text=model, variable=var, font=("Helvetica", 12))
            checkbox.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            self.model_vars.append((var, model))
            if model == 'paraphrase-mpnet-base-v2':
                var.set(1)

        # Adjust button layout (increase row height and padding)
        self.start_recording_button = ctk.CTkButton(main_frame, text="Start Recording 🎤", command=self.start_recording_thread, state="normal", font=("Helvetica", 12))  # Changed state to "normal"
        self.stop_recording_button = ctk.CTkButton(main_frame, text="Stop Recording 🛑", command=self.stop_recording, state="disabled", font=("Helvetica", 12))

        self.transcribe_button = ctk.CTkButton(main_frame, text="Transcribe and Diarize 📝🔊", command=self.transcribe_and_analyze, state="disabled", font=("Helvetica", 12))
        self.parameters_button = ctk.CTkButton(main_frame, text="Show Parameters 📊", command=self.show_parameters, font=("Helvetica", 12))

        # Audio player controls
        self.audio_player_frame = ctk.CTkFrame(main_frame)
        self.audio_player_frame.grid(row=6, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        self.audio_player_frame.grid_propagate(False)
        self.audio_player_frame.configure(height=50)

        self.play_button = ctk.CTkButton(self.audio_player_frame, text="Play ▶️", command=self.play_audio, state="disabled", font=("Helvetica", 12))
        self.pause_button = ctk.CTkButton(self.audio_player_frame, text="Pause ⏸️", command=self.pause_audio, state="disabled", font=("Helvetica", 12))
        self.stop_button = ctk.CTkButton(self.audio_player_frame, text="Stop ⏹️", command=self.stop_audio, state="disabled", font=("Helvetica", 12))

        self.play_button.pack(side="left", padx=10, pady=10)
        self.pause_button.pack(side="left", padx=10, pady=10)
        self.stop_button.pack(side="left", padx=10, pady=10)

        # One set of tabs for Transcription, Parameters, Cluster Plot, and Relevance Plot
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=7, column=0, columnspan=6, sticky="nsew", padx=5, pady=5)

        # Create frames for each tab
        transcription_tab = tk.Frame(notebook)
        parameters_tab = tk.Frame(notebook)
        cluster_tab = tk.Frame(notebook)
        relevance_tab = tk.Frame(notebook)

        # Add tabs to the notebook
        notebook.add(transcription_tab, text="Transcription 📝")
        notebook.add(parameters_tab, text="Collected Parameters 📋")
        notebook.add(cluster_tab, text="Cluster Plot 📈")
        notebook.add(relevance_tab, text="Relevance Plot 🔍")

        # Transcription textbox in the Transcription tab
        self.transcription_text = ctk.CTkTextbox(transcription_tab, height=200, font=("Helvetica", 12))
        self.transcription_text.pack(fill="both", expand=True)

        # Parameters textbox in the Parameters tab
        self.parameters_text = ctk.CTkTextbox(parameters_tab, height=200, font=("Helvetica", 12))
        self.parameters_text.pack(fill="both", expand=True)

        # Cluster Plot in the Cluster Plot tab
        self.cluster_fig = Figure(figsize=(5, 4), dpi=100)
        self.cluster_canvas = FigureCanvasTkAgg(self.cluster_fig, master=cluster_tab)
        self.cluster_canvas.draw()
        self.cluster_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Relevance Plot in the Relevance Plot tab
        self.relevance_fig = Figure(figsize=(5, 4), dpi=100)
        self.relevance_canvas = FigureCanvasTkAgg(self.relevance_fig, master=relevance_tab)
        self.relevance_canvas.draw()
        self.relevance_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Configure and add logging to the console only
        logging.info("UI initialized successfully.")

        # Arrange other widgets using grid
        num_speakers_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.num_speakers_slider.grid(row=1, column=3, sticky="ew", padx=5, pady=5)
        num_speakers_value_label.grid(row=1, column=4, sticky="w", padx=5, pady=5)

        topics_label.grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.topics_input.grid(row=2, column=3, columnspan=3, sticky="ew", padx=5, pady=5)

        models_label.grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.models_listbox.grid(row=3, column=3, columnspan=2, sticky="w", padx=5, pady=10)  # Add padding to avoid overlap

        self.start_recording_button.grid(row=4, column=0, padx=5, pady=20, sticky="ew")
        self.stop_recording_button.grid(row=4, column=1, padx=5, pady=20, sticky="ew")
        self.transcribe_button.grid(row=4, column=2, padx=5, pady=20, sticky="ew")
        self.parameters_button.grid(row=4, column=3, padx=5, pady=20, sticky="ew")

        # Initialize pygame mixer for audio playback controls
        self.is_paused = False

    def play_audio(self):
        if self.audio_file_path and os.path.exists(self.audio_file_path):
            try:
                pygame.mixer.music.load(self.audio_file_path)
                pygame.mixer.music.play()
                logging.info(f"Playing audio: {self.audio_file_path}")
            except Exception as e:
                logging.error(f"Error playing audio: {e}")
                self.show_message("Playback Error", f"Error playing audio: {e}", "error")
        else:
            self.show_message("No Audio", "No audio file available to play.", "warning")
            logging.warning("Play audio attempted without an available audio file.")

    def pause_audio(self):
        if pygame.mixer.music.get_busy():
            if not self.is_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
                logging.info("Audio playback paused.")
            else:
                pygame.mixer.music.unpause()
                self.is_paused = False
                logging.info("Audio playback resumed.")

    def stop_audio(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self.is_paused = False
            logging.info("Audio playback stopped.")

    def play_sound(self, sound_file):
        """
        Play a sound file asynchronously using pygame to avoid blocking the main thread.
        """
        def _play():
            try:
                if os.path.exists(sound_file):
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    logging.debug(f"Playing sound: {sound_file}")
                else:
                    logging.error(f"Sound file {sound_file} does not exist.")
            except Exception as e:
                logging.error(f"Error playing sound {sound_file}: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def connect_to_server_thread(self):
        """Start a new thread to connect to the server to avoid blocking the main thread."""
        threading.Thread(target=self.connect_to_server, daemon=True).start()

    def connect_to_server(self):
        self.IP = self.ip_input.get()
        self.PORT = self.port_input.get()
        self.UNIQUE_KEY = self.unique_key_input.get()

        logging.info(f"Attempting to connect to server with IP: {self.IP}, Port: {self.PORT}, Unique Key: {self.UNIQUE_KEY}")

        # Try to establish a connection
        client = GdpHttpClient(name='TestConnection', ip=self.IP, port_number=self.PORT, unique_key=self.UNIQUE_KEY)
        cmd = client.make_Command('GetStimulationStatus')
        try:
            response = cmd.Send()
            logging.debug(f"GDP Response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                self.connected = True
                logging.info("Connection to the server established successfully.")
                self.show_wifi_icon()
                self.connection_status_label.configure(text="🟢")  # Green circle for connected
                # Enable other buttons in the main thread
                self.after(0, lambda: self.start_recording_button.configure(state="normal"))
                self.after(0, lambda: self.transcribe_button.configure(state="normal"))
                self.show_message("Connection Successful", "Connected to the server. 🎉", "info")
            else:
                self.connected = False
                logging.warning(f"Failed to connect to the server. Status Code: {response.status_code}")
                self.hide_wifi_icon()
                self.connection_status_label.configure(text="🔴")  # Red circle for disconnected
                self.show_message("Connection Failed", "Failed to connect to the server. ❌", "warning")
        except Exception as e:
            self.connected = False
            logging.error(f"Connection error: {e}")
            self.hide_wifi_icon()
            self.connection_status_label.configure(text="🔴")  # Red circle for disconnected
            self.show_message("Connection Error", f"Error: {str(e)} ⚠️", "error")

    def show_wifi_icon(self):
        # Since we're using emojis, this function can be used for additional actions if needed
        logging.debug("Wi-Fi icon displayed (using emoji).")

    def hide_wifi_icon(self):
        # Since we're using emojis, this function can be used for additional actions if needed
        logging.debug("Wi-Fi icon hidden.")

    def update_num_speakers(self, value):
        self.num_speakers.set(int(float(value)))
        logging.debug(f"Number of speakers set to: {self.num_speakers.get()}")

    def start_recording_thread(self):
        """Start the recording in a separate thread to prevent GUI blocking."""
        threading.Thread(target=self.start_recording, daemon=True).start()

    def start_recording(self):
        logging.info("Start Recording button pressed.")
        # Removed the connection check to allow recording without server connection

        self.start_time = datetime.now()
        hhmmss = self.start_time.strftime("%H%M%S")
        name = f'startRec{hhmmss}'
        logging.info(f"Recording started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.connected:
            threading.Thread(target=self.send_gdp_command, args=('GetStimulationStatus', name), daemon=True).start()
        else:
            logging.info("Not connected to server. Skipping GDP command sending.")

        self.stop_event.clear()
        if not self.recording:
            self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
            self.recording_thread.start()
            self.recording = True

            # Update button states in the main thread
            self.after(0, lambda: self.start_recording_button.configure(state="disabled"))
            self.after(0, lambda: self.stop_recording_button.configure(state="normal"))
            self.after(0, lambda: self.transcribe_button.configure(state="disabled"))

            logging.debug("Recording thread started.")

            # Play start recording sound
            self.play_sound("ressources/sounds/start.mp3")  # <-- Play start sound

            # Show recording indicator
            self.after(0, lambda: self.recording_status_label.configure(text="🔴 Recording... 🎤"))

            # Start periodic requests in a separate thread only if connected
            if self.connected:
                threading.Thread(target=self.periodic_request, daemon=True).start()
                logging.debug("Periodic request thread started.")
            else:
                logging.info("Not connected. Skipping periodic requests.")

    def stop_recording(self):
        logging.info("Stop Recording button pressed.")
        self.stop_event.set()
        self.recording = False

        hhmmss = datetime.now().strftime("%H%M%S")
        name = f'stopRec{hhmmss}'
        logging.info(f"Recording stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.connected:
            threading.Thread(target=self.send_gdp_command, args=('GetStimulationStatus', name), daemon=True).start()
        else:
            logging.info("Not connected to server. Skipping GDP command sending.")

        # Update button states in the main thread
        self.after(0, lambda: self.start_recording_button.configure(state="normal"))
        self.after(0, lambda: self.stop_recording_button.configure(state="disabled"))
        self.after(0, lambda: self.transcribe_button.configure(state="normal"))

        # Play stop recording sound
        self.play_sound("ressources/sounds/stop.mp3")  # <-- Play stop sound

        # Hide recording indicator and show audio saved message
        if self.connected:
            self.after(0, lambda: self.recording_status_label.configure(text="🟢 Recording stopped, audio saved! 🎉"))
        else:
            self.after(0, lambda: self.recording_status_label.configure(text="🟢 Recording stopped, audio saved! 🎉 (No server connection)"))

        # Enable audio player buttons
        self.after(0, lambda: self.play_button.configure(state="normal"))
        self.after(0, lambda: self.stop_button.configure(state="normal"))

    def record_audio(self):
        fs = 44100  # Sample rate
        channels = 1  # Mono
        self.audio_frames = []

        try:
            logging.debug("Audio recording started.")
            with sd.InputStream(samplerate=fs, channels=channels) as stream:
                while not self.stop_event.is_set():
                    data, _ = stream.read(1024)
                    self.audio_frames.append(data.copy())

            # Concatenate all recorded frames
            audio_data = np.concatenate(self.audio_frames, axis=0)

            # Save audio to file
            audio_file_path = self.save_audio_file(audio_data, fs)
            self.audio_file_path = audio_file_path  # Save path for later use
            logging.info(f"Audio recording saved to {self.audio_file_path}")

            # Notify user that audio has been saved
            self.after(0, lambda: self.show_message("Audio Saved", "🎉 Audio saved successfully!", "info"))

        except Exception as e:
            logging.error(f"An error occurred during recording: {e}")
            self.show_message("Recording Error", f"An error occurred during recording: {e} ⚠️", "error")

    def save_audio_file(self, audio_data, fs):
        logging.debug("Saving recording...")
        try:
            # Create directory structure: trials/sess_DDMMYY/rec_HHMMSS/
            base_dir = "trials"
            session_date = self.start_time.strftime("%d%m%y")  # Format: DDMMYY
            recording_time = self.start_time.strftime("%H%M%S")  # Format: HHMMSS

            session_folder = os.path.join(base_dir, f"sess_{session_date}")
            recording_folder = os.path.join(session_folder, f"rec_{recording_time}")

            # Ensure the base directory exists
            os.makedirs(recording_folder, exist_ok=True)
            logging.debug(f"Saving files to: {recording_folder}")

            # Save the audio file to the recording_folder
            audio_file_path = os.path.join(recording_folder, "audio.wav")
            with wave.open(audio_file_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(fs)
                wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

            # Save the session-specific parameters to params.json
            params_file_path = os.path.join(recording_folder, "params.json")

            if self.connected:
                # Copy the small_parameters_data.json to params.json only if it's not empty
                SMALL_JSON_FILE_PATH = 'small_parameters_data.json'
                if os.path.exists(SMALL_JSON_FILE_PATH):
                    with open(SMALL_JSON_FILE_PATH, 'r') as src:
                        try:
                            json_data = json.load(src)
                        except json.JSONDecodeError:
                            json_data = []
                        if json_data:  # Ensure it's not empty before copying
                            with open(params_file_path, 'w') as dst:
                                json.dump(json_data, dst, indent=4)
                            logging.info(f"Parameters file saved: {params_file_path}")

                            # Clear the temporary parameters file after copying (only after successful save)
                            with open(SMALL_JSON_FILE_PATH, 'w') as f:
                                json.dump([], f)
                            logging.debug("Temporary parameters file cleared.")
                else:
                    logging.warning(f"{SMALL_JSON_FILE_PATH} does not exist. Skipping parameter saving.")
            else:
                # If not connected, save an empty params.json
                with open(params_file_path, 'w') as dst:
                    json.dump([], dst, indent=4)
                logging.info(f"Saved empty parameters file: {params_file_path} (No server connection)")

            return audio_file_path

        except Exception as e:
            logging.error(f"Error saving files: {e}")
            self.show_message("Save Error", f"An error occurred while saving files: {e} ⚠️", "error")
            return None

    def send_gdp_command(self, command, name):
        logging.info(f"Sending GDP command '{command}' with name '{name}'.")
        client = GdpHttpClient(name=name, ip=self.IP, port_number=self.PORT, unique_key=self.UNIQUE_KEY)
        cmd = client.make_Command(command)
        try:
            response = cmd.Send()
            logging.debug(f"GDP Response for '{command}': {response.status_code} - {response.text}")

            if response.status_code == 200:
                if command == 'GetStimulationParameters':
                    try:
                        parameters = json.loads(response.text)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse JSON response: {e}")
                        parameters = {'error': f'Failed to parse response: {e}', 'raw_response': response.text}

                    timestamp = time.time()
                    new_data = {'timestamp': timestamp, 'parameters': parameters}

                    # Append new data to the full parameters file
                    JSON_FILE_PATH = 'full_parameters_data.json'
                    try:
                        with open(JSON_FILE_PATH, 'r') as f:
                            data = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        data = []

                    data.append(new_data)

                    # Write the updated data back to the full parameters file
                    with open(JSON_FILE_PATH, 'w') as f:
                        json.dump(data, f, indent=4)

                    logging.info(f'Updated full parameters saved to {JSON_FILE_PATH}')

                    # Also save this session's parameters to a smaller temporary file
                    SMALL_JSON_FILE_PATH = 'small_parameters_data.json'
                    try:
                        with open(SMALL_JSON_FILE_PATH, 'r') as f:
                            small_data = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        small_data = []

                    small_data.append(new_data)

                    with open(SMALL_JSON_FILE_PATH, 'w') as f:
                        json.dump(small_data, f, indent=4)

                    logging.info(f'Updated small parameters saved to {SMALL_JSON_FILE_PATH}')

                    # Update the Parameters tab progressively
                    self.after(0, lambda: self.append_parameters_to_textbox(new_data))
            else:
                logging.warning(f"GDP command '{command}' failed with status code: {response.status_code}")
                self.show_message("Command Failed", f"Command '{command}' failed with status code: {response.status_code} ⚠️", "warning")
        except Exception as e:
            logging.error(f"Failed to send command '{command}': {e}")
            self.show_message("Command Error", f"Failed to send command '{command}'. Error: {str(e)} ⚠️", "error")

    def append_parameters_to_textbox(self, new_data):
        """
        Append new parameters to the Collected Parameters textbox.
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_data['timestamp']))
        parameters = new_data['parameters']
        if parameters is not None:
            param_str = f"Timestamp: {timestamp}\n"
            param_str += f"State: {parameters.get('State')}\n"
            param_str += f"LoopMode: {parameters.get('LoopMode')}\n"
            param_str += f"StimColumn Duration: {parameters.get('StimColumns', [{}])[0].get('Duration')}\n"
            param_str += f"StimColumn RampingDuration: {parameters.get('StimColumns', [{}])[0].get('RampingDuration')}\n"
            param_str += f"Waveform Name: {parameters.get('Waveforms', [{}])[0].get('Name')}\n"
            param_str += f"Frequency: {parameters.get('StimColumns', [{}])[0].get('StimRows', [{}])[0].get('FrequencyPeriod')}\n"
            param_str += f"Amplitude: {parameters.get('StimColumns', [{}])[0].get('StimRows', [{}])[0].get('Amplitude')}\n"
            param_str += "-"*40 + "\n"

            self.parameters_text.insert(tk.END, param_str)
            self.parameters_text.see(tk.END)  # Scroll to the end
            logging.debug(f"Appended new parameters to the textbox:\n{param_str}")
        else:
            logging.warning('Parameters are None for one of the entries.')

    def periodic_request(self):
        logging.debug("Periodic request thread started.")
        while not self.stop_event.is_set():
            current_time = time.time()
            hhmmss = time.strftime("%H%M%S", time.localtime(current_time))
            name = f'duringRec{hhmmss}'
            self.send_gdp_command('GetStimulationParameters', name)
            for _ in range(30):
                if self.stop_event.is_set():
                    logging.debug("Stop event detected. Exiting periodic request thread.")
                    return
                time.sleep(1)

    def show_parameters(self):
        logging.info("Show Parameters button pressed.")
        # Since parameters are now displayed progressively, this can be used to refresh or handle any additional logic
        self.show_message("Parameters", "Parameters are being collected and displayed in real-time.", "info")
        logging.info("Parameters are being collected and displayed progressively.")

    def flatten_parameters(self, parameters_list):
        flattened_data = []
        for item in parameters_list:
            timestamp = item['timestamp']
            parameters = item['parameters']
            data = {'Timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}

            if parameters is not None:
                data.update({
                    'State': parameters.get('State'),
                    'LoopMode': parameters.get('LoopMode'),
                    'StimColumn_Duration': (parameters.get('StimColumns', [{}])[0].get('Duration')
                                            if parameters.get('StimColumns') else None),
                    'StimColumn_RampingDuration': (parameters.get('StimColumns', [{}])[0].get('RampingDuration')
                                                if parameters.get('StimColumns') else None),
                    'Waveform_Name': (parameters.get('Waveforms', [{}])[0].get('Name')
                                    if parameters.get('Waveforms') and len(parameters['Waveforms']) > 0 else None),
                    'Frequency': (parameters.get('StimColumns', [{}])[0].get('StimRows', [{}])[0].get('FrequencyPeriod')
                                if parameters.get('StimColumns') and len(parameters['StimColumns']) > 0
                                and len(parameters['StimColumns'][0].get('StimRows', [])) > 0 else None),
                    'Amplitude': (parameters.get('StimColumns', [{}])[0].get('StimRows', [{}])[0].get('Amplitude')
                                if parameters.get('StimColumns') and len(parameters['StimColumns']) > 0
                                and len(parameters['StimColumns'][0].get('StimRows', [])) > 0 else None),
                })

                flattened_data.append(data)
                logging.debug(f"Flattened parameters: {data}")
            else:
                logging.warning('Parameters are None for one of the entries.')

        return flattened_data

    def transcribe_and_analyze(self):
        logging.info("Transcribe and Diarize button pressed.")
        self.topics = [topic.strip() for topic in self.topics_input.get().split(',') if topic.strip()]
        self.selected_models = [model for var, model in self.model_vars if var.get() == 1]

        logging.debug(f"Entered topics: {self.topics}")
        logging.debug(f"Selected models: {self.selected_models}")

        if not hasattr(self, 'audio_file_path') or not self.audio_file_path:
            self.show_message("No Audio", "No audio recorded yet. 🎤", "warning")
            logging.warning("Transcribe and analyze attempted without audio recording.")
            return

        if not self.topics:
            self.show_message("No Topics", "Please enter at least one topic. 📝", "warning")
            logging.warning("Transcribe and analyze attempted without entering topics.")
            return

        self.transcribe_button.configure(state="disabled")
        logging.debug("Transcribe and analyze button disabled.")

        # Perform transcription and diarization in a separate thread
        threading.Thread(target=self.perform_transcription_and_analysis, daemon=True).start()

    def perform_transcription_and_analysis(self):
        logging.info("Starting transcription and diarization process.")
        # Perform transcription and diarization
        try:
            self.transcription, self.formatted_transcript = transcribe_and_diarize(
                self.audio_file_path,
                num_speakers=self.num_speakers.get(),
                recording_start_time=self.start_time,
                language='any',
                model_size='medium'
            )
            logging.info("Transcription and diarization completed successfully.")
            self.show_message("Transcription Started", "🔄 Transcription and diarization started...", "info")
        except Exception as e:
            logging.error(f"An error occurred during transcription: {e}")
            self.show_message("Transcription Error", f"An error occurred during transcription: {e} ⚠️", "error")
            self.transcribe_button.configure(state="normal")
            return

        if not self.transcription:
            self.show_message("No Speech Detected", "No speech detected in the audio. Please try again. 🗣️", "warning")
            logging.warning("No speech detected in the audio.")
            self.transcribe_button.configure(state="normal")
            return

        # Proceed with analysis for each selected model
        for model_name in self.selected_models:
            model_id = {
                'paraphrase-MiniLM-L12-v2': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'paraphrase-mpnet-base-v2': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
                'all-mpnet-base-v2': 'sentence-transformers/all-mpnet-base-v2',
                'LaBSE': 'sentence-transformers/LaBSE',
            }.get(model_name)

            if not model_id:
                self.show_message("Model Not Found", f"Model {model_name} not found. ❌", "warning")
                logging.warning(f"Model '{model_name}' not found in model_id mapping.")
                continue

            try:
                logging.info(f"Processing data with model: {model_name}")
                model_app = TopicRelevanceAndClusteringApp(model_name=model_id)

                # Process data
                data = model_app.process_data(self.transcription, self.topics)
                if data.empty:
                    self.show_message("No Data", f"No data to process for model {model_name}. ❌", "warning")
                    logging.warning(f"No data returned from process_data for model {model_name}.")
                    continue

                # Perform clustering
                clustered_data = model_app.perform_clustering(data, num_clusters=self.num_speakers.get())
                logging.debug(f"Clustering completed for model {model_name}.")

                # Format time for display
                if 'time' in clustered_data.columns:
                    clustered_data['formatted_time'] = clustered_data['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Create plots in the main thread
                self.after(0, lambda data=clustered_data, model=model_name: self.create_cluster_plot(data, model))
                self.after(0, lambda data=clustered_data, topics=self.topics, model=model_name: self.create_relevance_plot(data, topics, model))

                # Notify user of completion
                self.show_message("Transcription Completed", f"✅ Transcription and analysis completed for {model_name}.", "info")

            except Exception as e:
                self.show_message("Processing Error", f"An error occurred while processing model {model_name}: {e} ⚠️", "error")
                logging.error(f"An error occurred while processing model {model_name}: {e}")

        # Display transcription in the main thread
        self.after(0, self.update_transcription_text)

        self.transcribe_button.configure(state="normal")
        logging.debug("Transcribe and analyze button re-enabled.")

    def update_transcription_text(self):
        self.transcription_text.delete('0.0', tk.END)
        self.transcription_text.insert(tk.END, self.formatted_transcript)
        logging.info("Transcription text updated in the Transcription tab.")

    def create_cluster_plot(self, data, model_name):
        try:
            self.cluster_fig.clf()
            ax = self.cluster_fig.add_subplot(111)
            if 'Cluster' in data.columns and 'x' in data.columns and 'y' in data.columns:
                clusters = data['Cluster'].astype(str)
                scatter = ax.scatter(data['x'], data['y'], c=clusters, cmap='viridis', alpha=0.6)
                ax.set_title(f"Phrase Clusters - {model_name}")
                ax.set_xlabel("Component 1")
                ax.set_ylabel("Component 2")
                self.cluster_canvas.draw()
                logging.info(f"Cluster plot created for model {model_name}.")
            else:
                logging.warning(f"Data for clustering plot is incomplete for model {model_name}.")
                self.show_message("Plot Incomplete", f"Data for clustering plot is incomplete for model {model_name}. ⚠️", "warning")
        except Exception as e:
            self.show_message("Plot Error", f"Failed to create cluster plot for {model_name}: {e} ⚠️", "error")
            logging.error(f"Failed to create cluster plot for {model_name}: {e}")

    def create_relevance_plot(self, data, topics, model_name):
        try:
            self.relevance_fig.clf()
            ax = self.relevance_fig.add_subplot(111)
            for topic in topics:
                if topic in data.columns and 'time' in data.columns:
                    ax.plot(data['time'], data[topic], label=topic)
                    logging.debug(f"Relevance data plotted for topic '{topic}' in model {model_name}.")
            ax.set_title(f"Topic Relevance Over Time - {model_name}")
            ax.set_xlabel("Time")
            ax.set_ylabel("Relevance Score")
            ax.legend()
            self.relevance_canvas.draw()
            logging.info(f"Relevance plot created for model {model_name}.")
        except Exception as e:
            self.show_message("Plot Error", f"Failed to create relevance plot for {model_name}: {e} ⚠️", "error")
            logging.error(f"Failed to create relevance plot for {model_name}: {e}")

    def show_message(self, title, message, icon_type):
        """
        Display a message box using tkinter's messagebox.
        Also logs the message.
        """
        log_message = f"{title}: {message}"
        if icon_type == "info":
            logging.info(log_message)
            messagebox.showinfo(title, message)
        elif icon_type == "warning":
            logging.warning(log_message)
            messagebox.showwarning(title, message)
        elif icon_type == "error":
            logging.error(log_message)
            messagebox.showerror(title, message)
        else:
            logging.info(log_message)
            messagebox.showinfo(title, message)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
