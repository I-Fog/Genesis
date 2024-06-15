from com.josue.ElementosServidor import *
from random import random
from com.util.Util import *
import threading
import math

class Juego():
    
    def __init__(self, numJugadores = 1):
        # se incializan los componentes del juego
        self.jugadoresTotales = numJugadores
        print("\nlongitud jugadores en Juego: " + str(self.jugadoresTotales))
        self.balones = []
        self.jugadores = []
        self.jugadores_azules_totales_iniciales = 0
        self.jugadores_rojos_totales_iniciales = 0
        self.jugadores_azules_totales = 0
        self.jugadores_rojos_totales = 0
        self.tiempo_celebracion = 3
        self.tiempo_inicio_celebracion = 0
        self.celebrando = False
        self.estado_inicial_balones = []
        #self.jugadoresSockets = {}
        self.estadoDelJuego = {}
        #self.jugadoresID = {}
        self.__inicializarJuego()
        #print("\njugadores despues de inicializarJuego: " + str(self.jugadores))
        


    def actualizarEstado(self, infoMano = None):
        #print("estadoDelJuego antes de actulizar: " + str(self.estadoDelJuego))
        #print("estoy en actualizarEstado")
        if(self.alguno_verdadero(self.estadoDelJuego["sonidos"])):
            self.estadoDelJuego["sonidos"] = [False, False]
        if(infoMano is not None):
            self.actualizarPosicionJugador(infoMano)
        #print("\nestadoDelJuego: " + str(self.estadoDelJuego))
        self.comprobarColisiones()
        #return self.estadoDelJuego # se devuelve el estado del juego
        hay_ganador, equipo_ganador = self.comprobar_equipo_ganador()          
        if(hay_ganador):
            if(self.celebrando):
                #print("tiempo de celebracion: " + str(time.time() - self.tiempo_inicio_celebracion))
                if((time.time() - self.tiempo_inicio_celebracion) > self.tiempo_celebracion):
                    print("fin de la celebracion")
                    self.fin_celebracion()
            else:
                self.celebrando = True    
                self.estadoDelJuego["equipoGanador"] = equipo_ganador
                self.tiempo_inicio_celebracion = time.time()
                self.celebracion()
    
    def alguno_verdadero(self, lista_sonidos):
        return any(lista_sonidos)
    
    def actualizarPosicionJugador(self, infoMano):
        #print("id" + str(infoMano["id"]))
        jugador = self.jugadores[infoMano["client_id"]]
        if(jugador.esta_vivo()):
            self.estadoDelJuego["posicionJugadores"][infoMano["client_id"]] = jugador.devolverCoordenadas(infoMano)
    
    def comprobarColisiones(self):
        self.comprobarColisionesBalones()

    def comprobarColisionLimiteBalon(self, balon):
        #print("estoy en comprobarColisionLimiteBalon")
        #print(str(balon.esta_en_movimiento()) + " " + str(balon.devolver_y()) + " " + str(Gestor.devolverLimitesBalon()[2]) + " " + str(balon.devolver_y() < Gestor.devolverLimitesBalon()[2]) + " " + str(balon.devolver_y() > Gestor.devolverLimitesBalon()[3]))
        return (balon.devolver_y() < Gestor.devolverLimitesBalon()[2]) or (balon.devolver_y() > Gestor.devolverLimitesBalon()[3])

    def comprobarColisionesBalones(self):
        for indiceBalon, balon in enumerate(self.balones):
            if(balon.esta_en_movimiento()):
                # en el caso de que haya pasado el tiempo de efecto
                if((time.time() - balon.devolver_tiempo_inicio_efecto()) > balon.devolver_tiempo_en_hacer_efecto()):
                    # comprobar si colisiona con un jugador
                    colisionaConJugador, indiceJugadorEliminado = self.balonColisionaConJugador(balon, indiceBalon)
                    if(colisionaConJugador):
                        # eliminar jugador
                        print("se ha eliminado al jugador " + str(indiceJugadorEliminado))
                        self.eliminarJugador(indiceJugadorEliminado)
                        balon.resetear()
                    elif(self.comprobarColisionLimiteBalon(balon)):
                        #print(self.comprobarColisionLimiteBalon(balon))
                        balon.colocar_en_limite()
            else:
                if(balon.esta_libre()):
                    #print("el balon numero " + str(indiceBalon) + " esta libre: " + str(balon.esta_libre()))
                    colisionaConJugador, indiceJugadorColisionado = self.balonColisionaConJugador(balon, indiceBalon)
                    if(colisionaConJugador and not self.jugadores[indiceJugadorColisionado].devolver_si_con_balon()):
                        balon.balon_ocupado(indiceJugadorColisionado)
                        self.jugadores[indiceJugadorColisionado].set_con_balon(True)
                else:
                    if(self.balonLanzado(balon)):
                        #print("devolver_dedo_indice_ha_bajado: " + str(self.jugadores[balon.devolver_jugador_enlazado()].devolver_dedo_indice_ha_bajado()))
                        if(self.jugadores[balon.devolver_jugador_enlazado()].devolver_dedo_corazon_ha_bajado()):
                            self.jugadores[balon.devolver_jugador_enlazado()].set_dedo_corazon_ha_bajado(False)
                            self.jugadores[balon.devolver_jugador_enlazado()].set_con_balon(False) # desenlazar jugador
                            balon.set_esta_en_movimiento(True, self.jugadores[balon.devolver_jugador_enlazado()].devolverTipoJugador())
                            self.estadoDelJuego["sonidos"] = [True, False]
            self.actualizarPosicionBalon(balon, indiceBalon)
            #self.actualizarPosicionEnemigo()
    
    def actualizarPosicionEnemigo(self):
        if(self.jugadores[1].vivo):
            self.jugadores[1].seguir_trayectoria()

    def eliminarJugador(self, indiceJugador):
        self.estadoDelJuego["posicionJugadores"][indiceJugador] = self.jugadores[indiceJugador].eliminar_jugador()
        self.actualizar_numero_jugadores_por_equipo(indiceJugador)
        self.estadoDelJuego["sonidos"] = [False, True]
        #self.estadoDelJuego["posicionJugadores"][indiceJugador] = self.jugadores[1].eliminar_enemigo()
    
    def celebracion(self):
        for jugador in self.jugadores:
            jugador.set_vivo(False)

    def fin_celebracion(self):
        self.celebrando = False
        self.tiempo_inicio_celebracion = 0
        self.estadoDelJuego["equipoGanador"] = None
        self.estadoDelJuego["posicionBalones"] = self.estado_inicial_balones
        self.jugadores_azules_totales = self.jugadores_azules_totales_iniciales
        self.jugadores_rojos_totales = self.jugadores_rojos_totales_iniciales
        for jugador in self.jugadores:
            jugador.set_vivo(True)

    def actualizar_numero_jugadores_por_equipo(self, indiceJugador):
        if(self.jugadores[indiceJugador].devolverTipoJugador() == 0):
            self.jugadores_azules_totales -= 1
        else:
            self.jugadores_rojos_totales -= 1
    
    def comprobar_equipo_ganador(self):
        if(self.jugadores_azules_totales == 0):
            return True, 1
            
        if (self.jugadores_rojos_totales == 0):
            return True, 0
    
        return False, None
        
        

    def balonLanzado(self, balon):
        return self.jugadores[balon.devolver_jugador_enlazado()].devolver_si_corazon_levantado() 

    def actualizarPosicionBalon(self, balon, indiceBalon):
        if(balon.esta_en_movimiento()):
            balon.seguir_trayectoria()
            self.estadoDelJuego["posicionBalones"][indiceBalon] = balon.devolverCoordenadas()
            #print("coordenadasBalon: " + str(balon.devolverCoordenadas()))
        else:
            if(not balon.esta_libre()):
                balon.set_coordenadas(self.estadoDelJuego["posicionJugadores"][balon.devolver_jugador_enlazado()]) 
                self.estadoDelJuego["posicionBalones"][indiceBalon] = balon.devolverCoordenadas()
        

    def balonColisionaConJugador(self, balon, indiceBalon):
        for indiceJugador, coordenadasJugador in enumerate(self.estadoDelJuego["posicionJugadores"]):
            #print("coordenadasJugador: " + str(coordenadasJugador))
            if(self.jugadores[indiceJugador].devolverTipoJugador() == 0):
                if(balon.devolver_y() < coordenadasJugador[1]):
                    distancia = math.hypot(
                        (balon.devolver_x()+15) - (coordenadasJugador[0]+30),
                        (balon.devolver_y()+11) - coordenadasJugador[1]
                    )
                else:
                    distancia = math.hypot(
                        (balon.devolver_x()+15) - (coordenadasJugador[0]+30),
                        balon.devolver_y() - (coordenadasJugador[1] + 42)
                    )
            else:
                if(balon.devolver_y() > coordenadasJugador[1]):
                    distancia = math.hypot(
                    (balon.devolver_x()+15) - (coordenadasJugador[0]+30),
                    balon.devolver_y() - (coordenadasJugador[1] + 42)
                )
                else:
                    distancia = math.hypot(
                        (balon.devolver_x()+15) - (coordenadasJugador[0]+30),
                        (balon.devolver_y()+11) - coordenadasJugador[1]
                    )
            #print("\n"+"coordenadasJugador: " + str(coordenadasJugador))
            ## el devolver coordenadas nos está mintiendo por que no esta revisada la implementacion de los limites del balon
            #print("coordenada X del balon " + str(indiceBalon) + ": " + str(balon.devolver_x()))
            #print("coordenada Y del balon " + str(indiceBalon) + ": " + str(balon.devolver_y()))
            #print("distancia con el balon " + str(indiceBalon) + ": " + str(distancia))
            if(distancia < 17):
                return True, indiceJugador
        return False, None
        
    
    def inicializarDatosDelJuego(self):
        self.estadoDelJuego = {
            "posicionJugadores": [],
            "posicionBalones": [],
            "tipoDeJugadores": [],
            "equipoGanador": None,
            "sonidos": [False, False]
        }
        #print("\nlongitud clientes enlazarJugadoresSocket: " + str(len(self.sockets)))
        #print("\nlongitud jugadores enlazarJugadoresSocket: " + str(len(self.jugadores)))
        for i in range(len(self.jugadores)):
            self.estadoDelJuego["posicionJugadores"].append(self.jugadores[i].posicionElemento.coordenadas)
            self.estadoDelJuego["tipoDeJugadores"].append(self.jugadores[i].devolverTipoJugador())
        for i in range(len(self.balones)):
            self.estadoDelJuego["posicionBalones"].append(self.balones[i].posicionElemento.coordenadas)
        self.estado_inicial_balones = self.estadoDelJuego["posicionBalones"]

    def inicializarBalones(self):
        numDePelotas = self.calcularNumeroDePelotasTest()
        print("numero de pelotas: " + str(numDePelotas))
        for i in range(numDePelotas):
            self.balones.append(self.inicializarBalon(i))
        #print("coordenadasBalon final inicializarPelotas(): " + str(self.estadoDelJuego["posicionBalones"]))
        

    def inicializarBalon(self, indicePelota):
        return Balon(
            [
                Gestor.coordenasInicioPelota[0] * (indicePelota+1),
                Gestor.coordenasInicioPelota[1]
            ],
            Gestor.devolverLimitesBalon(),
            9
        )


    def calcularNumeroDePelotasTest(self):
        return 6
    
    def calcularNumeroDePelotas(self):
        if(self.jugadoresTotales % 2 == 0):
            return self.jugadoresTotales // 2
        else:
            return ((self.jugadoresTotales // 2) - 1)
    
    def __inicializarJuego(self):
        #self.testIniciarJugador()
        #self.inicializarEnemigo()
        self.__inicializarJugadores()
        self.inicializarBalones()
        self.inicializarDatosDelJuego()
        print("coordenadasJugadores final inicializarJuego(): " + str(self.estadoDelJuego["posicionJugadores"]))

    def inicializarEnemigo(self):
        print("tipo de jugador: " + str(self.jugadores[0].devolverTipoJugador()))
        if(self.jugadores[0].devolverTipoJugador() == 0):
            self.jugadores.append(
                Enemigo(Gestor.coordenadasInicioEnemigoJugadorAzul,
                        Gestor.devolver_limites_enemigo(),
                        1,
                        1
                )
            )
        else:
            self.jugadores.append(
                Enemigo(Gestor.coordenadasInicioEnemigoJugadorRojo,
                        Gestor.devolver_limites_enemigo(),
                        5,
                        0
                )
            )

    def testIniciarJugador(self):
        #print("\nlongitud jugadores antes testIniciarJugador: " + str(len(self.jugadores)))
        self.jugadores.append(
            self.__inicializarJugadorAzul(1)
        )
        #print("\nlongitud jugadores despues testIniciarJugador: " + str(len(self.jugadores)))
        for jugador in self.jugadores:
            print(jugador)

    def __inicializarJugadores(self):
        if(self.jugadoresTotales % 2 == 0):
            self.jugadores_azules_totales = self.jugadoresTotales // 2
            self.jugadores_azules_totales_iniciales = self.jugadores_azules_totales

            self.jugadores_rojos_totales = self.jugadoresTotales // 2
            self.jugadores_rojos_totales_iniciales = self.jugadores_rojos_totales
        else:
            self.jugadores_azules_totales = self.jugadoresTotales // 2
            self.jugadores_rojos_totales = self.jugadoresTotales // 2 + 1
        contadorAzul = 1
        contadorRojo = 1
        # se procede a crear los jugadores
        for _ in range (self.jugadores_azules_totales):
            self.jugadores.append(
                self.__inicializarJugadorAzul(contadorAzul)
            )
            contadorAzul += 1
        for _ in range (self.jugadores_rojos_totales):
            self.jugadores.append(
                self.__inicializarJugadorRojo(contadorRojo)
            )
            contadorRojo += 1
        print("\nlongitud jugadores despues de inicializarJugadores: " + str(len(self.jugadores)))


    def __inicializarJugadorAzul(self, contadorAzul):
        return JugadorAzul(
            [
            Gestor.coordenadasInicioJugador[0] * contadorAzul,  # Coordenada X (va variando)
            Gestor.coordenadasInicioJugador[1]                  # Coordenada Y
            ],
            Gestor.devolverLimitesJugador(0),                   # Limites del jugador
            0                                                   # Tipo de jugador
            )

    def __inicializarJugadorRojo(self, contadorRojo):
        return JugadorRojo(
            [
            Gestor.coordenadasInicioJugador[0] * contadorRojo,  # Coordenada X (va variando)
            Gestor.coordenadasInicioJugador[1]                  # Coordenada Y
            ],
            Gestor.devolverLimitesJugador(1),                   # Limites del jugador
            1,                                                  # Tipo de jugador
        )

    def devolverJugadores(self):
        return self.jugadores
    
    def devolver_estado_del_juego(self):
        return self.estadoDelJuego
