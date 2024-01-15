# -*- coding: utf-8 -*-
"""
Created on Fri Jan 12 20:50:56 2024

@author: Antonio Muñoz Santiago, Luis Moreno Pernil, Enrique Martínez Calvo
"""
import numpy as np
import matplotlib.pyplot as plt
import wave
import tkinter as tk
import ctypes

# CONSTANTES
THRESHOLD = 0.75  # Umbral para la detección de picos (porcentaje respecto al máximo global)
DISCARTED_SAMPLES = 1000 # Número de muestras a descartar entre cada nota

# VARIABLES
audio_samples = []  # Muestras de audio
max_audio_value = 0  # Máximo valor de la señal de audio

# FUNCIONES
def getSamples(file_name, channels=1):
    """
    getSamples obtiene las muestras de audio de un archivo .wav

    Parameters
    ----------
    file_name : str
        Nombre del archivo .wav a leer.
    channels : int, optional
        Número de canales a leer. 1 = Mono, 2 = Stereo.
    """

    global max_audio_value

    # Se abre el archivo de audio
    audio = wave.open(file_name, "r")

    # Obtenemos los datos del audio, y lo convertimos a un array de numpy
    # de enteros de 16 bits
    frames = audio.readframes(-1)
    signal = np.frombuffer(frames, dtype="int16")

    if channels == 2:
        # Leemos las posiciones pares de signal (solo el canal 1)
        signal = signal[::2]

    # Obtenemos los parámetros del audio
    fs = audio.getframerate()
    time = np.linspace(0, len(signal)/fs, num=len(signal))

    # Cerramos el archivo de audio
    audio.close()

    # Almacenamos el máximo valor de la señal
    max_audio_value = max(signal)
    
    return [time, signal]

def loadFileButtonFunction():
    global audio_samples

    print(fileNameBox.get())
    audio_samples = getSamples(fileNameBox.get(), int(nChannelsBox.get()))

    # Se actualiza el texto de la etiqueta de estado
    statusLabel.config(text="Archivo " + fileNameBox.get() + " cargado correctamente.")

def identify_freq(magnitude_fft,Ts,threshold):
    """
    identify_frec identifica la frecuencia de la nota tocada.

    Parameters
    ----------
    magnitude_fft : array de numpy
        Array que contiene la magnitud de la respuesta en frecuencia.
    Ts : float
        Frecuencia de muestreo.
    threshold : float
        Porcentaje en tanto por 1 que multiplicado por el máximo global
        dará una medida del umbral.
    
    Returns: devuelve la frecuencia de la nota identificada.
    """ 
    
    # Se crea el eje de frecuencias
    freq = np.linspace(0,1/(Ts*2),len(magnitude_fft))
    
    # Lista para almacenar los máximos locales que superen el umbral
    max_frecs = []
    
    # Se determinan los índices de los máximos locales que superen el umbral
    for sampleIndex in range(1,len(magnitude_fft)-1):
        
        # Si una muestra es mayor que la anterior y la siguiente, es un máximo local
        if magnitude_fft[sampleIndex] > magnitude_fft[sampleIndex-1] \
           and magnitude_fft[sampleIndex] > magnitude_fft[sampleIndex+1]:
            
            # Se comprueba si el máximo supera el umbral
            if magnitude_fft[sampleIndex] > max_audio_value*threshold:
                max_frecs.append(freq[sampleIndex])
    
    if len(max_frecs) == 0:
        return 0 # Si no se ha detectado ningún máximo, es porque hay silencio en esa corchea
    else:
        return min(max_frecs)

def freq_to_note(freq):
    if freq == 0:
        return "SILENCIO"
    else:
        notes = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']

        note_index = 12*np.log2(freq/440)+49  
        note_index = round(note_index)
        
        note = (note_index - 1) % len(notes)
        note = notes[int(note)]
        
        # Como a la octava más baja se le asocian los índices de tecla -8, -7, ...
        # se le suma 8 para calcular la octava.
        octave = (note_index+8)//len(notes)
        
        return str(note)+str(int(octave))

def showWaveForm():
    if audio_samples == []:
        # Se actualiza el texto de la etiqueta de estado
        statusLabel.config(text="No se ha cargado ningún archivo de audio.")
        return
    else:
        # Cerrar la figura anterior antes de crear una nueva
        plt.close()
        # Graficamos la señal de audio en una nueva figura
        plt.figure()
        plt.title("Señal de audio")
        plt.xlabel("Tiempo [s]")
        plt.ylabel("Amplitud")
        plt.plot(audio_samples[0], audio_samples[1])
        plt.show()
        # Se actualiza el texto de la etiqueta de estado
        statusLabel.config(text="Se han representado las muestras de audio correctamente.")

def musicToTxt():

    global audio_samples

    # Se debe encontrar el número de muestras correspondientes a la mínima figura rítmica (una corchea).
    fs = int(fsBox.get()) # Hz
    bpm = int(bpmBox.get()) # Beats per minute
    muestras_corchea = (1/(2*bpm))*60*fs # Muestras/corchea
    
    corcheas = []
    corcheas_time = []

    while len(audio_samples[1]) > muestras_corchea:
        corcheas.append(audio_samples[1][:int(muestras_corchea)])
        corcheas_time.append(audio_samples[0][:int(muestras_corchea)])
        audio_samples[1] = audio_samples[1][int(muestras_corchea):]
        audio_samples[0] = audio_samples[0][int(muestras_corchea):]
        
    # Si aún quedan muestras en el audio, se añaden como un último elmento al final
    if len(audio_samples[1]):
        corcheas.append(audio_samples[1])
        corcheas_time.append(audio_samples[0])
    
    notasIdentificadas = []

    for corchea in corcheas:
        corchea_fft = np.fft.fft(corchea[DISCARTED_SAMPLES:])
        magnitud_corchea_fft = np.abs(corchea_fft)

        # Se obtiene el eje de frecuencias
        Ts = 1/fs # Siendo la frecuencia de muestreo 44.1 kHz
        magnitud_corchea_fft = magnitud_corchea_fft[:int(np.round(len(magnitud_corchea_fft)/2))]
        corchea_freq = np.linspace(0,1/(Ts*2),len(magnitud_corchea_fft))

        notasIdentificadas.append(freq_to_note(identify_freq(magnitud_corchea_fft,Ts,THRESHOLD)))
    
    # Se crea el archivo de texto
    file = open("notas.txt", "w")
    file.write("Notas identificadas:\n")
    for nota in notasIdentificadas:
        file.write(nota + "\n")
    file.close()

# Se inicia la interfaz de usuario
window = tk.Tk() # Contenedor donde se añaden los elementos gráficos
window.title("PyTranscribe")
window.geometry("800x600")
window.resizable(True, True)
ctypes.windll.shcore.SetProcessDpiAwareness(1)

# Se añaden los elementos a la interfaz
titulo = tk.Label(window, text="PyTranscribe", bg="gray")
titulo.config(font=("Arial", 50))  # Increase the font size to 20
titulo.pack(fill=tk.X) # Para posicionar la etiqueta en la ventana

fileNameBox = tk.Entry(window, font=("Arial", 22))
fileNameBox.place(x=30, y=150, width=410, height=50)
fileNameBox.insert(0, "audios/")  # Establecer el texto inicial

nChannelsValues = ["1", "2"]
nChannelsBox = tk.StringVar(window)
nChannelsBox.set(nChannelsValues[0])
nChannelsDropdown = tk.OptionMenu(window, nChannelsBox, *nChannelsValues)
nChannelsDropdown.place(x=460, y=150, width=80, height=50)
nChannelsDropdown.config(font=("Arial", 18))
window.nametowidget(nChannelsDropdown.menuname).config(font=("Arial", 18))  # Set the dropdown menu's font

loadFileButton = tk.Button(window, text="Cargar archivo", font=("Arial", 18), command = loadFileButtonFunction)
loadFileButton.place(x=550, y=150, width=200, height=50)

bpmLabel = tk.Label(window, text="BPM:", font=("Arial", 18))
bpmLabel.place(x=130, y=220, width=200, height=50)
bpmBox = tk.Entry(window, font=("Arial", 18))
bpmBox.place(x=280, y=220, width=75, height=50)
bpmBox.insert(0, "60")  # Establecer el texto inicial

fsLabel = tk.Label(window, text="fs:", font=("Arial", 18))
fsLabel.place(x=380, y=220, width=50, height=50)
fsBox = tk.Entry(window, font=("Arial", 18))
fsBox.place(x=460, y=220, width=110, height=50)
fsBox.insert(0, "44100")  # Establecer el texto inicial

generateWaveForm = tk.Button(window, text="Mostrar forma de onda", font=("Arial", 18), command = showWaveForm)
generateWaveForm.place(x=220, y=300, width=300, height=50)

musicToTxtButton = tk.Button(window, text="Exportar notas a txt", font=("Arial",18), command = musicToTxt)
musicToTxtButton.place(x=220, y=390, width=300, height=50)

musicToPdfButton = tk.Button(window, text="Exportar a partitura", font=("Arial",18), command = musicToTxt)
musicToPdfButton.place(x=220, y=480, width=300, height=50)

statusLabel = tk.Label(window, text="Rellenar parámetros del archivo .wav", font=("Arial", 18))
statusLabel.pack()

# Bucle principal (lleva el registro de lo que sucede en la ventana)
window.mainloop()