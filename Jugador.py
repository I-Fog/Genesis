import os
import sys
import threading
import cv2
from com.josue.Camara import Camara
import socket
from com.josue.Mano import Mano
import json
from com.josue.ElementosJugador import *
from com.util.Util import ProcesarImagen
import cvzone

class JugadorCliente:
    id = -1
    def __init__(self, ipServidor, puertoServidor):
        self.IPservidor = ipServidor
        self.puertoServidor = puertoServidor
        # el primer argumento indica que es un socket de tipo IPv4
        # el segundo argumento indica que es un socket de tipo TCP
        self.clienteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.id_cliente = 0
        self.camara = Camara(0, 777, 353, 30)
        self.mano = Mano([0,0], 2)
        self.campoDeJuego = CampoDeJuego()
        self.imgJugadores = ImagenesJugadores()
        self.imgPelota = ImagenPelota()
        self.iniciar_envio_de_datos = threading.Event()
        self.hilo_activo = True
        print("Jugador creado")
        self.conectar_servidor()

    def recibir_id_cliente(self):
            try:
                data = self.clienteSocket.recv(1024).decode("utf-8")
                self.id_cliente = json.loads(data)["client_id"]
                #print(f"ID del cliente recibido: {self.id_cliente}")
            except socket.error as e:
                print(f"Error al recibir ID del cliente: {e}")

    def conectar_servidor(self):
        print("Conectando al servidor")
        self.clienteSocket.connect((self.IPservidor, self.puertoServidor))
        self.recibir_id_cliente()
        thread_mostrar_estado_juego = threading.Thread(target=self.mostrar_estado_del_juego)
        thread_mostrar_estado_juego.start()
        thread_enviar = threading.Thread(target=self.enviar_informacion_mano)
        thread_enviar.start()
    
    def enviar_informacion_mano(self):
        while self.hilo_activo:
            infoMano = self.mano.devolverInformacionManoDetectada(self.camara.obtenerFrame())
            infoMano["client_id"] = self.id_cliente
            #print("infoMano del lado del cliente antes de enviar: " + str(infoMano))
            try:
                self.clienteSocket.send((json.dumps(infoMano) + "\n").encode("utf-8"))
            except socket.error as e:
                print("error al enviar la informacion de la mano")
                print(e.with_traceback())
                self.hilo_activo = False
            cv2.waitKey(33)
    
    def recibir_estado_del_juego(self):
        #print("Recibiendo estado del juego")
        buffer = ""
        while self.hilo_activo:
            try:
                buffer += self.clienteSocket.recv(1024).decode("utf-8")
                #print("buffer del lado del cliente: " + str(buffer))
                while "\n" in buffer:
                    data, buffer = buffer.split("\n", 1)
                    if data:
                        estado = json.loads(data)
                        if "start" in estado and estado["start"]:
                            Sonido.reproducir_musica_fondo()
                            self.iniciar_envio_de_datos.set()  # Señal para empezar a enviar datos
                            continue
                        #print(f"Estado del juego recibido: {estado}")
                        return estado
            except socket.error as e:
                print("Error al recibir el estado del juego")
                print("buffer es de tipo: " + str(type(buffer)))
                print("Contenido del buffer: " + buffer)
                print(f"Error: {e}")
                self.hilo_activo = False
                break
            except json.JSONDecodeError as e:
                print(f"Error decodificando el mensaje {e}")
                self.hilo_activo = False
                break
            cv2.waitKey(33)
        return None
        

    def mostrar_estado_del_juego(self):
        while self.hilo_activo:
            estado_del_juego = self.recibir_estado_del_juego()
            if estado_del_juego is not None:
                self.camara.mostrarFrame(
                    self.procesar_estado_del_juego(estado_del_juego)
                )
                cv2.waitKey(33)

    def procesar_estado_del_juego(self, estadoDelJuegoDict):
        self.campoDeJuego.resetearImagenUtilizable()
        estadoDelJuego = self.campoDeJuego.devolverImgUtilizable()
        self.procesar_jugadores(estadoDelJuegoDict, estadoDelJuego)
        self.procesar_balones(estadoDelJuegoDict, estadoDelJuego)
        hay_ganador, equipo_ganador = self.hay_equipo_ganador(estadoDelJuegoDict)
        if(hay_ganador):
            self.mostrar_ganador(equipo_ganador, estadoDelJuego)
        self.procesar_sonidos(estadoDelJuegoDict)
        return estadoDelJuego
    
    def procesar_sonidos(self, estadoDelJuegoDict):
        if(estadoDelJuegoDict["sonidos"][0]):
            Sonido.reproducir_sonido_lanzamiento()
        if(estadoDelJuegoDict["sonidos"][1]):
            Sonido.reproducir_sonido_choque()

    def mostrar_ganador(self, equipo_ganador, estadoDelJuego):
        if(equipo_ganador == 0):
            cvzone.putTextRect(estadoDelJuego, 'GANADOR: EQUIPO AZUL', [200, 176],
                                scale=3, thickness=3, offset=10, colorT=(0, 0, 255))
        else:
            cvzone.putTextRect(estadoDelJuego, 'GANADOR: EQUIPO ROJO', [200, 176],
                                scale=3, thickness=3, offset=10, colorT=(255, 0, 0))

    
    def hay_equipo_ganador(self, estadoDelJuegoDict):
        if(estadoDelJuegoDict["equipoGanador"] is not None):
            if(estadoDelJuegoDict["equipoGanador"] == 0):
                return True, 0
            else:
                return True, 1
        return False, None
        
                
    def procesar_balones(self, estadoDelJuegoDict, estadoDelJuego):
        for coordenadas in estadoDelJuegoDict["posicionBalones"]:
            ProcesarImagen.overlayElementos(
                estadoDelJuego,
                self.imgPelota.devolverImgPelota(),
                coordenadas
            )
    
    def procesar_jugadores(self, estadoDelJuegoDict, estadoDelJuego):
        #print("estadoDelJuegoDict del lado del cliente: " + str(estadoDelJuegoDict))
        for indice, coordenadas in enumerate(estadoDelJuegoDict["posicionJugadores"]):
            ProcesarImagen.overlayElementos(
                estadoDelJuego,
                self.imgJugadores.devolverImgJugador(
                    estadoDelJuegoDict["tipoDeJugadores"][indice]
                ),
                coordenadas
            )
    
    def desconectar(self):
        self.clienteSocket.close()

if __name__ == "__main__":
    jugadorTest = JugadorCliente("ip del servidor", 8080)
