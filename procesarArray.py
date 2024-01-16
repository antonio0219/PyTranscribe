# -*- coding: utf-8 -*-
"""
Created on Mon Jan 15 11:03:09 2024

@author: Luis Moreno
"""


def procesar_array(array):
    resultado = []
    i = 0
    while i < len(array):
        if i < len(array) - 3 and array[i] == array[i+1] == array[i+2] == array[i+3]:
            resultado.append(array[i] +"2")
            resultado.append(2)
            i += 4
        elif i < len(array) - 1 and array[i] == array[i+1]:
            resultado.append(array[i] +"4")
            i += 2
        else:
            resultado.append(array[i] + "8")
            i += 1
    return resultado

