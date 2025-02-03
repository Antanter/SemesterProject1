import sys
import os
import pygame
import time
import threading
import random
import socket
import pickle
import math

pygame.init()
pygame.mixer.init()
pygame.display.set_caption("Tic-Tac-Toe")

class Cell:

    """
    The class which is responsible for the cells for X/O in the game session.
    Each cell in the game is a object of this class
    """

    def __init__(self, position, id):
        """
        state - state of the cell at the moment. It can be x, o, or None
        id - id of the cell. Derrives from 1 to 9
        width, height - parameters for sizes of cells
        posX, posY - padding of cell fom the 0, 0, more precisely, left top corner
        self.rect - defines the rectangle of given size, color and offtop. It's a cell in the render itself
        color - standart color of cell.
        """
        self.state = None
        self.id = id
        self.width = 100
        self.height = 100
        self.posX = position[0]
        self.posY = position[1]
        self.rect = pygame.Rect(self.posX, self.posY, self.width, self.height)
        self.color = player.colors["grey"]

    def Reload(self):
        """ Reloads the cells, setting state to None for each """
        self.state = None
    
    def Render(self):
        """ Renders the cells themselves, and also their state (X if state == x and O if state == o)"""
        pygame.draw.rect(player.screen, self.color, self.rect)
        if self.state == "o":
            pygame.draw.circle(player.screen, player.colors["blue"], (self.posX + self.width / 2, self.posY + self.height / 2), 40)
            pygame.draw.circle(player.screen, player.colors["grey"], (self.posX + self.width / 2, self.posY + self.height / 2), 35)
        if self.state == "x":
            pygame.draw.line(player.screen, player.colors["red"], (self.posX + self.width / 2 - 37.5, self.posY + self.height / 2 - 37.5), (self.posX + self.width / 2 + 37.5, self.posY + self.height / 2 + 37.5), 5)
            pygame.draw.line(player.screen, player.colors["red"], (self.posX + self.width / 2 + 37.5, self.posY + self.height / 2 - 37.5), (self.posX + self.width / 2 - 37.5, self.posY + self.height / 2 + 37.5), 5)

    def ChangeState(self):
        """
        Function created to change the state of some cell.
        Main if-clauses properties:

        1. not isPressingBlocked - parameter, needed to prevent multi-pressing of cells and buttons in one frame
        2. itsTurn - used to check whether this is this player's turn.
        3. sceneId - checks whether there is game scene right now
        4. state - if state is not None, there are no any sense to change the cell's state
        5. isMousePressed - will only proceed if mouse button is pressed

        After these, it also produces the sound, and changes isPressingBlocked to False. 
        After that, depending on whether the mode of game is multiplayer or not, changes the state of cell or asks the server to change it.
        """
        if not gameManager.isPressingBlocked and gameManager.itsTurn and gameManager.sceneID == 3 and self.state == None and gameManager.isMousePressed and (self.posX) <= pygame.mouse.get_pos()[0] <= (self.posX + self.width) and (self.posY) <= pygame.mouse.get_pos()[1] <= (self.posY + self.height):
            gameManager.ButtonSound()
            gameManager.isPressingBlocked = True
            if player.client:
                if gameManager.move % 2 == 1:
                    player.client.RPC_SendDataToServer((self.id,"o"))
                else:
                    player.client.RPC_SendDataToServer((self.id,"x"))
                gameManager.itsTurn = False
            else:
                if gameManager.move % 2 == 0:
                    self.state = "o"
                    gameManager.move += 1
                    gameManager.isMousePressed = True

class Client:
    """
    This class is used for client connection and responses duting multiplayer
    """
    def __init__(self):
        """
        givenPort - port, which is dedicated to the current client on the server side. Used for correct data transfer
        peer - IPv4 and port for connection. If no other ip is provided during pre-connection phase, alochost will be used ("127.0.0.1")
        client - object of socket, therefore client itself
        client.setblocking(False) - used to prevent blocking the I/O stream during connection
        isConnected - parameter which defines whether client is connected right now
        """
        self.givenPort = None
        self.peer = ("127.0.0.1", 5555)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.setblocking(False)
        self.isConnected = False

    def searchForServer(self):
        """
        Activates after player tries to connect to server. Intially, asks whether there is any other IP address provided, if not, uses "127.0.0.1"
        After that tries to connect to the server while the succefsull connection or exception thrown.
        """
        while not self.isConnected and self.peer is not None:
            if player.server is not None:
                self.peer = ("127.0.0.1", 5555)
            else:
                self.peer = (input("Address: "), 5555)
                
            try:
                self.client.connect_ex(self.peer)
                print(f"Connected to {self.peer} successfully")
                self.isConnected = True
            except Exception as e:
                print(f"Client's problem: {e}")
                return
    
    def RPC_GetDataFromServer(self):
        """
        Function, which is used for data receiving from the server
        data - is a buffer of size 1024, which will contain bytes sended by server
        The protocol I use have a structure of [(Command), data]
        Commands are chosen by the server. There is their explanatio:
        ParseConnection - confirms the connection and sets the givenPort to the port sent by server
        ChangePlayer - in the game cycle, changes itsTurn, more precisely, giving this player a right for the turn
        StartNewRound - reloads the game, wtarting new multiplayer game round.
        ChangeCellState - sends a data about changes cells, to players to synchronize the game field
        """
        try:
            data = self.client.recv(1024)
            if not data:
                raise ValueError("No new data from server yet")
            print(f"New data from server: {pickle.loads(data)}")
            data = tuple(pickle.loads(data))
            purpose = data[0]
            data = data[1]

            if purpose == "ParseConnection":
                if self.givenPort == None:
                    self.givenPort = data[1]
            
            if purpose == "ChangePlayer":
                if data[1] == self.givenPort:
                    print("Turn of this player")
                    gameManager.itsTurn = True
                else:
                    print("Not a turn of this player")
                    gameManager.itsTurn = False
            
            if purpose == "StartNewRound":
                gameManager.stopThread = True
                gameManager.restartGame()

            if purpose == "ChangeCellsState":
                gameManager.ButtonSound()
                for line in gameField:
                    for cell in line:
                        if cell.id == data[0]:
                            cell.state = data[1]
                            gameManager.move += 1
                            gameManager.gameCycle()
        except:
            return
    
    def RPC_SendDataToServer(self, data):
        """ Sends a data to server, wher parameter is a data to send """
        gameManager.itsTurn = False
        self.client.send(pickle.dumps(data))

class Server:
    """ This class is used for server connection and responses duting multiplayer """
    def __init__(self):
        """
        lastTurn - defines the player which has a right to make a turn. Initially set to -1
        clientsList - dictionary, which contains the info about clients connected to the server
        server - server socket object, more precisely the server itself
        server.bind(("0.0.0.0", 5555)) - defines the addres for connection to the server. Set to the standart addres for connections
        server.listen(2) - defines, how much players could connect to the server
        """
        self.lastTurn = -1
        self.clientsList = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("0.0.0.0", 5555))
        self.server.setblocking(False)
        self.server.listen(2)

    def acceptPeers(self):
        """ While number of clients connected is less than 2, searches for new connections, accepts them and save info in the clientsList """
        try:
            clientAddr, addr = self.server.accept()
            self.clientsList[addr[0]] = (addr[1], clientAddr) # save a client in the dictionary in the form {ipv4: port, clientObj}
            self.RPC_SendDataToClient(clientAddr, (addr[0], addr[1]), "ParseConnection")
            player.client.searchForServer()
        except:
            return
    
    def restartGame(self):
        """ Sends a restart command to every client connected to tthe server """
        self.lastTurn = random.randint(0, 1)
        for client in self.clientsList.keys():
            self.RPC_SendDataToClient(self.clientsList[client][1], None, "StartNewRound")
            if self.server:
                player.client.RPC_GetDataFromServer()
            time.sleep(0.1)
            self.RPC_SendDataToClient(self.clientsList[client][1], (client, self.clientsList[list(self.clientsList.keys())[self.lastTurn]][0]), "ChangePlayer")
    
    def RPC_GetDataFromClient(self):
        """ Receives data from each client each tick. If no new data, just throws exception and returns """
        self.server.setblocking(True)

        for client in self.clientsList.keys():
            try:
                data = self.clientsList[client][1].recv(1024)
                tempData = pickle.loads(data)
                print(f"New data from client: {tempData}")
                self.lastTurn = (self.lastTurn + 1) % 2
                self.RPC_SendDataToClients(tempData, "ChangeCellsState")
                if self.server:
                    player.client.RPC_GetDataFromServer()
                time.sleep(0.1)
                self.RPC_SendDataToClients((client, self.clientsList[list(self.clientsList.keys())[self.lastTurn]][0]), "ChangePlayer")
            except:
                continue

        self.server.setblocking(False)
        return

    def RPC_SendDataToClients(self, data, purpose):
        """ Sends data to all connected clients """
        for client in self.clientsList.keys():
            self.RPC_SendDataToClient(self.clientsList[client][1], data, purpose)
    
    def RPC_SendDataToClient(self, client, data, purpose):
        """ Sends data to the mentioned client """
        client.sendall(pickle.dumps((purpose, data)))
    
    def reachedCapacity(self):
        """ Function to check whether the server reached its capacity """
        return len(self.clientsList) == 2

class Button:
    """
    buttonColor - color dedicated to the button.
    posX, posY, width, height, text - the same a in the cell 
    """
    def __init__(self, font, posX, posY, width, height, text, color):
        self.buttonColor = player.colors["grey"]
        self.posX = posX
        self.posY = posY
        self.width = width
        self.height = height
        self.text = Text(text, font, color, posX, posY)

    def renderButton(self):
        """ Function responsidble for rendering the button"""
        pygame.draw.rect(player.screen, self.buttonColor, pygame.Rect(self.posX, self.posY, self.width, self.height))
        self.text.renderText()
    
    def isInShape(self):
        """ This function, pretty similarly to cell, looks whether player cliecked on the button"""
        if not gameManager.isPressingBlocked and gameManager.isMousePressed and (self.posX) <= pygame.mouse.get_pos()[0] <= (self.posX + self.width) and (self.posY) <= pygame.mouse.get_pos()[1] <= (self.posY + self.height):
            gameManager.ButtonSound()
            gameManager.isPressingBlocked = True
            return True

class Text:
    """ Small class I use to standartize the text in the game """
    def __init__(self, text, font, color, posX, posY):
        """
        text - the text to be written on the text field
        font - font to be used
        color - color of the text
        posX, posY - the same as in other demonstations 
        """
        self.font = font
        self.text = text
        self.color = color
        self.posX = posX
        self.posY = posY
    
    def renderText(self):
        """ Functrion used to render the text """
        font = pygame.font.Font(None, self.font)
        text = font.render(self.text, True, self.color)
        player.screen.blit(text, (self.posX + 10, self.posY + 10))

class Player:
    """
    The class dedicated to the player. There is only 1 object of this class in the game
    """
    def __init__(self):
        """
        server, client - if player decided to start multiplayer game session, it will create or client, or either client and server. 
        They are a objects of the referenced classes theirselves.
        screen - pygame screen, used to render the elements of the game
        colors - predefined colors required for the game
        sounds - sounds in the game. Downloaded initially from the given directory
        """
        self.server = None
        self.client = None

        self.screen = pygame.display.set_mode((640, 640))
        self.colors = {"red" : (255,0,0), "green":(0,255,0),"blue":(0,0,255), "grey":(128, 128, 128)}
        self.sounds = ["gameAssets/snd.mp3", "gameAssets/mnd.mp3", "gameAssets/tnt.mp3"]

    def resource_path(self, relPath):
        """ Function, which loads sound files """
        try:
            path = sys._MEIPASS
        except Exception:
            path = os.path.abspath(".")

        return os.path.join(path, relPath)

class GameEngine(Player):
    """
    The main class of the game. Used for game process, rendering the elements of UI, computer moves etc. Is a child of Player class
    """
    def __init__(self):
        """
        super().__init__() - initializes the parent class
        isMousePressed - event, which looks whether mouse is pressed
        isPressingBlocked - determines, whether the following frame
        itsTurn - determines, whether it's this player's turn
        move - parameter, which used in the game cycle logic. Shows, how much cells are already painted in the game
        sceneID - parameter, which shows the level of the menu right now.
        values - a list, which is used in processing of game turns. Saves the values od the game board, such as "x", "o" or None
        stopThread - used in multiplayer mode. Dfines, when to start the game
        """
        super().__init__()

        self.isPressingBlocked = False
        self.isMousePressed = True
        self.itsTurn = False

        self.move = 0
        self.sceneID = 0

        self.values = []

        self.stopThread = False
    
    def gameCycle(self):
        """
        The cycle dedicated for checking whether some player has won
        Firstly, erases the values list, and fills the screen with white color
        After that for each cell changes its state if someone has clicked on the cell, and appends it to the values
        After that, defines whether someone has wone (the fate variable)
        Nextly, renders the cells, and counts the number of cells with state None
        Finally, if someone has fate True, or there are no free cells, ends the game with endSchpiele functions, or contra, continues the game
        """
        self.values = []

        self.screen.fill((255, 255, 255))

        for line in gameField:
            l = []
            for cell in line:
                cell.ChangeState()
                l.append(cell.state)
            self.values.append(l)
    
        fate = self.checkSquare()

        for line in gameField:
            for cell in line:
                cell.Render()
        
        count = 0
        for i in self.values:
            for j in i:
                if j == None:
                    count += 1
    
        if fate:
            self.endSchpiele(fate, self.colors["red"] if fate == "x" else self.colors["blue"], False if fate == "x" else True)
            self.RenderMenuPage()
        elif count != 0:
            font = pygame.font.Font(None, 50)
            text = font.render(f"Turn of {"computer" if gameManager.move % 2 == 1 else "player"}", True, self.colors["red"] if gameManager.move % 2 == 1 else self.colors["blue"])
            self.screen.blit(text, (175, 25))

    def restartGame(self):
        """ Small function to reload all the cells (set their state to None) """
        self.move = 0
        for line in gameField:
                for cell in line:
                    cell.Reload()
        self.sceneID = 3
    
    def RenderMenuPage(self):
        """
        Function, used to render the menu. Depending on the sceneId param, dedcides which part of menu should be rendered.
        0 = start menu, 
        1 = menu of chosing the game mode, 
        2 = used in multiplayer, for screen where player waits for another player to connect
        3 = level of the game cycle
        """
        self.screen.fill((255, 255, 255))

        if self.sceneID == 0:
            newGame.renderButton()

            if newGame.isInShape():
                self.sceneID = 1
                self.RenderMenuPage()
        
        elif self.sceneID == 1:
            newLocal.renderButton()

            if newLocal.isInShape():
                player.server, player.client, self.itsTurn = None, None, True
                self.restartGame()

            if player.client == None and player.server == None:
                newLANS.renderButton()
                newLANC.renderButton()

                if newLANS.isInShape():
                    self.sceneID = 2
                    player.server, player.client = Server(), Client()
                    self.RenderMenuPage()

                if newLANC.isInShape():
                    self.sceneID = 2
                    player.client = Client()
                    self.RenderMenuPage()

            elif player.server != None:
                newRound.renderButton()

                if newRound.isInShape():
                    if player.server.reachedCapacity():
                        player.server.restartGame()

        elif self.sceneID == 2:
            self.screen.blit(pygame.font.Font(None, 35).render(f"Please, wait till another player will join your game", True, (0, 0, 0)) 
                                                               if player.server else pygame.font.Font(None, 35).render(f"Please, input servers' IPv4 address to the console", True, (0, 0, 0)), (30, 250))
            if self.stopThread == True:
                self.sceneID = 3
                self.stopThread = False

        elif self.sceneID == 3:
            self.gameCycle()

    def checkSquare(self):
        """ Function, which checkes whether someone has won the game """
        for i in range(3):
            if all(gameField[i][col].state == "x" for col in range(3)) or all(gameField[i][col].state == "o" for col in range(3)):
                return self.values[i][0]
            if all(gameField[row][i].state == "x" for row in range(3)) or all(gameField[row][i].state == "o" for row in range(3)):
                return self.values[0][i]
        if self.values[0][0] == self.values[1][1] == self.values[2][2] != None or self.values[0][2] == self.values[1][1] == self.values[2][0] != None:
            return self.values[1][1]
        if self.move % 9 == 0 and self.move > 0:
            self.endSchpiele(None, (15, 15, 15), self.colors["grey"])
            self.RenderMenuPage()
    
    def computerTurn(self):
        """
        The mini-max algorithm used by computer player. Has 3 internal functions:
        checkSquareMiniMax - pretty much the same as checkSquare, but used for minimax algorithm. Return True or False depending on the game situation
        isDrawMiniMax - function, which checks whether there are no more free space on the game board
        minimax - the recursive algorithm, used to count in which combinations computer won and in which lost
        """
        def checkSquareMiniMax(player):
            for row in range(3):
                if all(gameField[row][col].state == player for col in range(3)):
                    return True
            for col in range(3):
                if all(gameField[row][col].state == player for row in range(3)):
                    return True
            if all(gameField[i][i].state == player for i in range(3)):
                return True
            if all(gameField[i][2 - i].state == player for i in range(3)):
                return True
            return False

        def isDrawMiniMax():
            for row in range(3):
                for col in range(3):
                    if gameField[row][col].state is None:
                        return False
            return True
        
        def minimax(botCase):
            if checkSquareMiniMax("x"):
                return 1
            if checkSquareMiniMax("o"):
                return -1
            if isDrawMiniMax():
                return 0
            
            if botCase:
                bestScore = -float('inf')
                for i in range(9):
                    cell = gameField[i // 3][i % 3]
                    if cell.state is None:
                        cell.state = "x"
                        score = minimax(False)
                        cell.state = None
                        bestScore = max(bestScore, score)
                return bestScore

            else:
                bestScore = float('inf')
                for i in range(9):
                    cell = gameField[i // 3][i % 3]
                    if cell.state is None:
                        cell.state = "o"
                        score = minimax(True)
                        cell.state = None
                        bestScore = min(bestScore, score)
                return bestScore

        bestScore = -float('inf')
        bestMove = None
        guarantor = True

        for i in range(9):
            cell = gameField[i // 3][i % 3]
            if cell.state is None:
                cell.state = "x"
                score = minimax(False)
                cell.state = None

                if guarantor == True:
                    bestScore = score
                    bestMove = i
                    guarantor = False

                if score > bestScore and random.randint(1, 10000) < 9200:
                    bestScore = score
                    bestMove = i

        if bestMove is not None:
            cell = gameField[bestMove // 3][bestMove % 3]
            cell.state = "x"
            self.move += 1
            self.isMousePressed = True

    def endSchpiele(self, winner, color, win):
        """ Function, which is used to show the player who won, and restart the game"""
        self.FateMusic(win)
        self.screen.blit(pygame.font.Font(None, 50).render(f"Player {winner} won!", True, color) if winner != None else pygame.font.Font(None, 50).render(f"Draw", True, color), (225, 25))
        pygame.display.flip()
        time.sleep(2.5)
        self.sceneID = 0
        self.itsTurn = False
        return True

    def ButtonSound(self):
        """ Function, which is used in Button class. Playes the music"""
        pygame.mixer.music.load(player.resource_path(random.choice(player.sounds)))
        pygame.mixer.music.play(loops=1)
        time.sleep(0.05)

    def FateMusic(self, win):
        """ Function, which is used in EndSchliele. Playes the music"""
        pygame.mixer.music.load(self.resource_path("gameAssets/win.mp3")) if win == True else pygame.mixer.music.load(self.resource_path("gameAssets/fil.mp3"))
        pygame.mixer.music.play(loops=1)
        time.sleep(0.05)
    
    def play(self):
        """
        The main cycle function of the game. Executes every tick
        Defined whether player pressed the button or leaved the game
        If it's local game, playes the computer move
        if it's multiplayer, executeds sending and receiving on the socket I/O functions
        Renders the menu in the end of the function
        """
        self.isPressingBlocked = False
        self.isMousePressed = False
        set = pygame.event.get()

        if self.move % 2 == 1 and player.client == None and self.itsTurn:
            self.computerTurn()
            time.sleep(0.16)
        
        if player.client:
            player.client.searchForServer()
            player.client.RPC_GetDataFromServer()

            if player.server:
                player.server.RPC_GetDataFromClient()
                if not player.server.reachedCapacity():
                    player.server.acceptPeers()
                    time.sleep(0.25)
                    if player.server.reachedCapacity():
                        player.server.restartGame()

        for event in set:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.isMousePressed = True

        self.RenderMenuPage()
    
        pygame.display.flip()

        for event in set:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

""" Initializing of the player, gameManager, buttons and gameField """

player = Player()
gameManager = GameEngine()

newGame = Button(50, 125, 550, 400, 75, "Start new game", (0,0,0)) 
newLocal = Button(50, 125, 100, 400, 75, "Start new local game", (0,0,0))
newLANS = Button(50, 125, 250, 400, 75, "Start new game a host", (0,0,0))
newLANC = Button(50, 125, 400, 400, 75, "Start new game as a client", (0,0,0))
newRound = Button(50, 125, 250, 400, 75, "Start new round", (0,0,0))

gameField = [[Cell((100, 100), 1), Cell((250, 100), 2), Cell((400, 100), 3)],
             [Cell((100, 250), 4), Cell((250, 250), 5), Cell((400, 250), 6)],
             [Cell((100, 400), 7), Cell((250, 400), 8), Cell((400, 400), 9)]]

while True:
    gameManager.play()