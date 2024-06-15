from collections import deque
#import sys
import threading
#import time
import socket
import traceback
import cv2
import numpy as np
from Juego import Juego
import json

class Servidor():
    ip = "ip del servidor" 
    port = 8080
    def __init__(self, min_players=1):
        self.min_players = min_players
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((Servidor.ip, Servidor.port))
        self.server_socket.listen(2) # pone al cliente en modo "escucha"
        self.clients = []
        self.contador_id = 0
        self.partida = None
        self.game_active = False
        self.lock_clientes = threading.Lock() 
        self.lock_contador_id = threading.Lock()
        self.buffer = deque() #
        self.game_start_event = threading.Event()  # Event para manejar el inicio del juego
        self.buffer_condition = threading.Condition()
        print(f"Server listening on {Servidor.ip}:{Servidor.port}")
    
    def broadcast(self, message):
        for cliente in self.clients:
            try:
                cliente.sendall(message)
            except ConnectionResetError:
                print(f"Connection reset by peer {cliente.getpeername()}, removing client.")
                self.clients.remove(cliente)
                cliente.close()
            except OSError as e:
                if e.errno == 10038:  # WinError 10038: Se intentó realizar una operación en un elemento que no es un socket
                    print(f"Error sending message to {cliente.getpeername()}: {e}")
                    self.clients.remove(cliente)
                    cliente.close()
                else:
                    raise

    def obtener_id_cliente(self):
        with self.lock_contador_id:
            client_id = self.contador_id
            self.contador_id += 1
        return client_id
    
    def handle_conexion_cliente(self, client_socket, addr):
        print(f"New client connected: {addr}")
        self.clients.append(client_socket)
        # Enviar ID único al cliente
        client_socket.sendall(json.dumps({"client_id": self.obtener_id_cliente()}).encode("utf-8"))
        self.check_start_game()

        buffer = ""
        # Esperar a que el juego esté activo
        self.game_start_event.wait()
        print("longitud de clientes del lado del servidor: " + str(len(self.clients)))
        # Recibir datos del cliente
        while self.game_active:
            try:
                buffer += client_socket.recv(1024).decode("utf-8")
                if not buffer:
                    print("no hay datos")
                    break
                while "\n" in buffer:
                    data, buffer = buffer.split("\n", 1)
                    if data:
                        infoMano = json.loads(data)
                        with self.lock_clientes:
                            self.partida.actualizarEstado(infoMano)
                        with self.buffer_condition:
                            self.buffer.append(self.partida.devolver_estado_del_juego())
                            self.buffer_condition.notify_all()
                    else:
                        print("no hay datos")
                        break
            except ConnectionResetError as e:
                self.handle_cliente_exception(client_socket, addr, e)
                break
            except OSError as e:
                if e.errno == 10038:
                    self.handle_cliente_exception(client_socket, addr, e)
                else:
                    raise
                break


    
    def check_start_game(self):
        if len(self.clients) >= self.min_players and not self.game_active:
            print("\nSe va a crear la instancia juego")
            self.partida = Juego(len(self.clients))
            self.iniciar_juego()

    def iniciar_buffer(self):
        thread_buffer = threading.Thread(target=self.procesar_buffer)
        thread_buffer.start()
    
    def actualizar_partida(self):
        print("Se va a iniciar el hilo de la partida")
        while self.game_active:
            with self.lock_clientes:
                self.partida.actualizarEstado()
            with self.buffer_condition:
                self.buffer.append(self.partida.devolver_estado_del_juego())
                self.buffer_condition.notify_all()
            cv2.waitKey(33)

    def iniciar_hilo_juego(self):
        thread_partida = threading.Thread(target=self.actualizar_partida)
        thread_partida.start()

    def iniciar_juego(self):
        self.game_active = True
        print("\nvoy a cambiar el estado del juego a activo para que los clientes puedan empezar a jugar")
        self.game_start_event.set()  # Señal para empezar a jugar
        start_signal = json.dumps({"start": True}) + "\n"
        self.broadcast(start_signal.encode("utf-8"))
        print("\nGame started!")
        self.iniciar_hilo_juego()


    def run(self):
        print("Server is ready to accept clients...")
        self.iniciar_buffer()
        while True:
            socket_cliente, addr = self.server_socket.accept()
            thread_cliente = threading.Thread(target=self.handle_conexion_cliente, args=(socket_cliente, addr)) # se crea un hilo para cada cliente	
            thread_cliente.start() # se inicia el hilo
            
    def procesar_buffer(self):
        while True:
            with self.buffer_condition:
                while not self.buffer:
                    self.buffer_condition.wait()
                estado_del_juego = self.buffer.popleft()
            try:
                estado_del_juego_a_enviar = json.dumps(estado_del_juego) + "\n"
                self.broadcast(estado_del_juego_a_enviar.encode("utf-8"))
            except Exception as e:
                print(f"Error processing buffer: {e}")
            cv2.waitKey(33)

    def desconectar_cliente(self, client_socket, addr):
        # Desconectar al cliente y cerrar el socket
        if client_socket in self.clients:
            self.clients.remove(client_socket)
            client_socket.close()
            print(f"Client {addr} disconnected.")

    def handle_cliente_exception(self, client_socket, addr, exception):
        print("Cliente desconectado")
        self.desconectar_cliente(client_socket, addr)
    

if __name__ == "__main__":
    server = Servidor(min_players= 2)
    server.run()
