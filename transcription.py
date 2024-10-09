# transcription.py

import torch
import numpy as np
import wave
import contextlib
from datetime import datetime, timedelta
from sklearn.cluster import AgglomerativeClustering
from speechbrain.inference import EncoderClassifier
from pyannote.audio import Audio
from pyannote.core import Segment
import whisper
import logging

def transcribe_and_diarize(audio_path, num_speakers, recording_start_time, language='any', model_size='medium'):
    # Load Whisper model
    model_name = model_size
    if language == 'English' and model_size != 'large':
        model_name += '.en'
    model = whisper.load_model(model_name)

    # Transcribe audio
    result = model.transcribe(audio_path)
    segments = result.get("segments", [])

    if not segments:
        return None, None  # No speech detected

    # Get audio duration
    with contextlib.closing(wave.open(audio_path, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)

    # Initialize pyannote audio
    audio = Audio()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    embedding_model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": device}
    )

    # Define function to extract segment embeddings
    def segment_embedding(segment):
        start = segment["start"]
        end = min(duration, segment["end"])
        clip = Segment(start, end)
        waveform, sample_rate = audio.crop(audio_path, clip)
        waveform = waveform.squeeze(0)  # Remove channel dimension if present
        with torch.no_grad():
            embeddings = embedding_model.encode_batch(waveform.to(device))
        return embeddings.squeeze(0).cpu().numpy()

    # Extract embeddings
    embeddings = np.zeros(shape=(len(segments), 192))
    for i, segment in enumerate(segments):
        embeddings[i] = segment_embedding(segment)

    embeddings = np.nan_to_num(embeddings)

    # Perform clustering
    clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
    labels = clustering.labels_
    for i in range(len(segments)):
        segments[i]["speaker"] = 'SPEAKER ' + str(labels[i] + 1)

    # Prepare transcription data
    transcription = []
    for (i, segment) in enumerate(segments):
        segment_time = recording_start_time + timedelta(seconds=segment["start"])
        speaker = segment["speaker"]
        text = segment["text"].strip()
        transcription.append({
            'time': segment_time,
            'speaker': speaker,
            'text': text
        })

    # Prepare formatted transcription for display
    formatted_transcript = ""
    previous_speaker = None
    for i, segment in enumerate(segments):
        current_speaker = segment["speaker"]
        segment_time = recording_start_time + timedelta(seconds=segment["start"])
        current_time = segment_time.strftime('%H:%M:%S')
        if i == 0 or current_speaker != previous_speaker:
            formatted_transcript += f"\n{current_speaker} {current_time}\n"
        formatted_transcript += segment["text"][1:] + ' '
        previous_speaker = current_speaker

    return transcription, formatted_transcript
