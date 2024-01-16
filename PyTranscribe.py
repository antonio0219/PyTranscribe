# -*- coding: utf-8 -*-
"""
Created on Fri Jan 12 20:50:56 2024

@author: Antonio Muñoz Santiago, Luis Moreno Pernil, Enrique Martínez Calvo
"""
import numpy as np
import matplotlib.pyplot as plt
import wave
import tkinter as tk
from tkinter import filedialog
import ctypes
import lilypond
import subprocess

# VARIABLES
audio_samples = []  # Muestras de audio
max_audio_value = 0  # Máximo valor de la señal de audio
fs = 0 # Frecuencia de muestreo
fileDir = "" #Ruta al archivo

# FUNCIONES
def getSamples(file_name):
    """
    getSamples obtiene las muestras de audio de un archivo .wav

    Parameters
    ----------
    file_name : str
        Nombre del archivo .wav a leer.
    channels : int, optional
        Número de canales a leer. 1 = Mono, 2 = Stereo.
    """

    global fs

    # Se abre el archivo de audio
    audio = wave.open(file_name, "r")

    # Obtenemos los datos del audio, y lo convertimos a un array de numpy
    # de enteros de 16 bits
    frames = audio.readframes(-1)
    signal = np.frombuffer(frames, dtype="int16")

    if audio.getnchannels() == 2:
        # Leemos las posiciones pares de signal (solo el canal 1)
        signal = signal[::2]

    # Obtenemos los parámetros del audio
    fs = audio.getframerate()
    time = np.linspace(0, len(signal)/fs, num=len(signal))

    # Cerramos el archivo de audio
    audio.close()
    
    return [time, signal]

def getFileDirection():
    global fileDir
    fileDir = filedialog.askopenfilename(title="Seleccionar archivo")

    rutaSimple = fileDir.split("/")

    nuevaRuta = "/".join(rutaSimple[-2:])

    print(nuevaRuta)
    fileNameBox.delete(0, tk.END)
    fileNameBox.insert(0, nuevaRuta)  # Establecer el texto inicial

def loadFileButtonFunction():
    global audio_samples

    print(fileNameBox.get())
    audio_samples = getSamples(fileDir)

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
    
    # Se identifica el máximo global
    max_value = np.max(magnitude_fft)

    # Lista para almacenar los máximos locales que superen el umbral
    max_frecs = []
    
    # Se determinan los índices de los máximos locales que superen el umbral
    for sampleIndex in range(1,len(magnitude_fft)-1):
        
        # Si una muestra es mayor que la anterior y la siguiente, es un máximo local
        if magnitude_fft[sampleIndex] > magnitude_fft[sampleIndex-1] \
           and magnitude_fft[sampleIndex] > magnitude_fft[sampleIndex+1]:
            
            # Se comprueba si el máximo supera el umbral
            if magnitude_fft[sampleIndex] > max_value*threshold:
                max_frecs.append(freq[sampleIndex])
    
    return min(max_frecs)

def freq_to_note(freq):
    notes = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']

    note_index = 12*np.log2(freq/440)+49
    note_index = round(note_index)
    if TranspositionBox.get() == "Bb":
        note_index += 2
    elif TranspositionBox.get() == "Eb":
        note_index -= 3
    
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

def get_notes():

    global audio_samples

    # Se debe encontrar el número de muestras correspondientes a la mínima figura rítmica (una corchea).
    bpm = int(bpmBox.get()) # Beats per minute
    muestras_corchea = (1/(2*bpm))*60*fs # Muestras/corchea
    
    corcheas = []
    corcheas_time = []

    while len(audio_samples[1]) > muestras_corchea:
        corcheas.append(audio_samples[1][:int(muestras_corchea)].astype(np.int64))
        corcheas_time.append(audio_samples[0][:int(muestras_corchea)])
        audio_samples[1] = audio_samples[1][int(muestras_corchea):]
        audio_samples[0] = audio_samples[0][int(muestras_corchea):]
        
    # Si aún quedan muestras en el audio, se añaden como un último elmento al final
    if len(audio_samples[1]):
        corcheas.append(audio_samples[1].astype(np.int64))
        corcheas_time.append(audio_samples[0])
    
    notasIdentificadas = []

    for corchea in corcheas:
        # Se lleva a cabo el cálculo de la energía de cada corchea, y vemos
        # si supera el umbral del silencio
        if np.sum(np.power(np.abs(corchea[int(DiscartedBox.get()):]), 2)) > int(SilenceBox.get()):
            corchea_fft = np.fft.fft(corchea[int(DiscartedBox.get()):])
            magnitud_corchea_fft = np.abs(corchea_fft)
        
            
            # Se obtiene el eje de frecuencias
            Ts = 1/fs # Siendo la frecuencia de muestreo 44.1 kHz
            magnitud_corchea_fft = magnitud_corchea_fft[:int(np.round(len(magnitud_corchea_fft)/2))]
            corchea_freq = np.linspace(0,1/(Ts*2),len(magnitud_corchea_fft))
        
            notasIdentificadas.append(freq_to_note(identify_freq(magnitud_corchea_fft,Ts,float(THBox.get()))))
        else:
            notasIdentificadas.append("Silencio")

    return notasIdentificadas

def musicToTxt():

    notasIdentificadas = get_notes()    

    # Se crea el archivo de texto
    file = open("notas.txt", "w")
    file.write("Notas identificadas:\n")
    for nota in notasIdentificadas:
        file.write(nota + "\n")
    file.close()

def musicToPdf():

    notasIdentificadas = get_notes()
    
    notasFormatoPond = []
    
    for nota in notasIdentificadas:
        notaLily = ''
        if len(nota) == 3:
            notaLily = nota[0].lower() + "is" 
        else:
            notaLily = nota[0].lower()
    
        numcomillas = int(nota[-1]) -3
        notaLily+= numcomillas*"'"
        notasFormatoPond.append(notaLily)
    
    resultado = []
    i = 0
    while i < len(notasFormatoPond):
        if i < len(notasFormatoPond) - 3 and notasFormatoPond[i] == notasFormatoPond[i+1] == notasFormatoPond[i+2] == notasFormatoPond[i+3]:
            resultado.append(notasFormatoPond[i] +"2")
            resultado.append(2)
            i += 4
        elif i < len(notasFormatoPond) - 1 and notasFormatoPond[i] == notasFormatoPond[i+1]:
            resultado.append(notasFormatoPond[i] +"4")
            i += 2
        else:
            resultado.append(notasFormatoPond[i] + "8")
            i += 1
    
    # Se crea el archivo de texto
 
    file = open("partitura.ly.", "w")
    file.write("\\version \"2.24.3\"\n")
    file.write("{\n")
    file.write("\override Score.TimeSignature.transparent = ##t\n")
    file.write("\cadenzaOn\n")
    while len(resultado) > 20:
        file.write(" ".join(resultado[:20]) + "\\break" +"\n")
        resultado = resultado[20:]
    file.write(" ".join(resultado) + "\n")
    file.write("\cadenzaOff\n")
    file.write("}\n")
    file.close()
    
    subprocess.run([lilypond.executable(),"partitura.ly"])

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
fileNameBox.place(x=30, y=150, width=500, height=50)
fileNameBox.insert(0, "audios/")  # Establecer el texto inicial

loadFileButton = tk.Button(window, text="Cargar", font=("Arial", 18), command = loadFileButtonFunction)
loadFileButton.place(x=550, y=150, width=100, height=50)

boton_examinar = tk.Button(window, text="Buscar", font=("Arial", 18), command=getFileDirection)
boton_examinar.place(x=655, y=150, width=100, height=50)

transpositorLabel = tk.Label(window, text="Transposición:", font=("Arial", 18))
transpositorLabel.place(x=380, y=220, width=200, height=50)
TranspositionValues = ["C", "Bb", "Eb"]
TranspositionBox = tk.StringVar(window)
TranspositionBox.set(TranspositionValues[0])
TranspositionDropdown = tk.OptionMenu(window, TranspositionBox, *TranspositionValues)
TranspositionDropdown.place(x=580, y=220, width=110, height=50)
TranspositionDropdown.config(font=("Arial", 18))
window.nametowidget(TranspositionDropdown.menuname).config(font=("Arial", 18))  # Set the dropdown menu's font

bpmLabel = tk.Label(window, text="BPM:", font=("Arial", 18))
bpmLabel.place(x=70, y=220, width=200, height=50)
bpmBox = tk.Entry(window, font=("Arial", 18))
bpmBox.place(x=220, y=220, width=75, height=50)
bpmBox.insert(0, "60")  # Establecer el texto inicial

generateWaveForm = tk.Button(window, text="Mostrar forma de onda", font=("Arial", 18), command = showWaveForm)
generateWaveForm.place(x=50, y=300, width=300, height=50)

THLabel = tk.Label(window, text="Umbral detección:", font=("Arial", 18))
THLabel.place(x=390, y=300, width=200, height=50)
THBox = tk.Entry(window, font=("Arial", 18))
THBox.place(x=650, y=300, width=75, height=50)
THBox.insert(0, "0.75")  # Establecer el texto inicial

musicToTxtButton = tk.Button(window, text="Exportar notas a txt", font=("Arial",18), command = musicToTxt)
musicToTxtButton.place(x=50, y=390, width=300, height=50)

DiscartedLabel = tk.Label(window, text="Muestras descartadas:", font=("Arial", 18))
DiscartedLabel.place(x=350, y=390, width=300, height=50)
DiscartedBox = tk.Entry(window, font=("Arial", 18))
DiscartedBox.place(x=645, y=390, width=90, height=50)
DiscartedBox.insert(0, "1000")  # Establecer el texto inicial

musicToPdfButton = tk.Button(window, text="Exportar a partitura", font=("Arial",18), command = musicToPdf)
musicToPdfButton.place(x=50, y=480, width=300, height=50)

SilenceLabel = tk.Label(window, text="Umbral del silencio:", font=("Arial", 18))
SilenceLabel.place(x=340, y=480, width=300, height=50)
SilenceBox = tk.Entry(window, font=("Arial", 18))
SilenceBox.place(x=610, y=480, width=150, height=50)
SilenceBox.insert(0, "1000000000")  # Establecer el texto inicial

statusLabel = tk.Label(window, text="Rellenar parámetros del archivo .wav", font=("Arial", 18))
statusLabel.pack()

# Bucle principal (lleva el registro de lo que sucede en la ventana)
window.mainloop()