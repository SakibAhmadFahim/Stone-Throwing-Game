#import 
import sys
import math
import random

from PyQt5 import QtCore, QtGui, QtWidgets, QtTest
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.Qt import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPainter, QPen, QImage

import tensorflow as tf
import qimage2ndarray
import cv2
from playsound import playsound
import pickle

#Game Interface
class Game():      
    class GameState():
        INTRO = 0
        INSTRUCT = 1
        PAUSED = 2
        PLAY = 3
        GAMEOVER = 4

    class Type():
        P2C = 1
    
    class Turn():
        P1 = 0
        P2 = 1
        
    class Action():
        MOVE = 0
        SET_ANGLE_FORCE = 1
        THROW = 2
    
    #constants start
    screenWidth = 800
    screenHeight = 600
    
    fieldHeight = 50
    fieldColor = Qt.green
    barColor = Qt.blue
    barHeight = 160
    barWidth = 20
    barPosX = (screenWidth // 2) - (barWidth // 2)
    barPosY = screenHeight - fieldHeight - barHeight
    
    player1limitX = (0, barPosX - barWidth - 60 )     
    player2limitX = (barPosX + barWidth , screenWidth - barWidth)
    
    player1AngleLimit = (0, 84)
    player2AngleLimit = (96, 180)
    
    #player width == bar height // 3 * 2
    playerHeight = barHeight // 3 * 2

    #player width == bar width
    
    playerWidth = barWidth

    #player color is black
    playerColor = Qt.black
    playerMove = 5
    
    stoneHeight = 10
    stoneWidth = 10

    #stone color is red
    stoneColor = Qt.red
   
    Total_throw = 0
    
    minForceLen = 10
    maxForceLen = 100
    defaultForceLen = 30
    approximationLinePoints = 6
    angleLineColor = Qt.red
    angleChange = 5
    velocityChange = 5
    
    scoreText1PosX = 30
    scoreText1PosY = 50
    scoreText2PosX = screenWidth - 150
    scoreText2PosY = 50
    stateMessageBoxX = (screenWidth // 2) - 100
    stateMessageBoxY = 100
    
    #constants stop
    
    state = GameState.INTRO
    turn = Turn.P1
    action = Action.MOVE
    
    computer = tf.keras.models.load_model('model_imageToPrediction')    

    type = Type.P2C

class Player():
    #Initial position of player
    def __init__(self, initX):
        self.playerX = initX
        self.playerY = Game.screenHeight - Game.fieldHeight - Game.playerHeight
        self.angle = 0
        self.initForce = Game.minForceLen
        self.score = 0
        self.throw = 10
    
    def move(self, m):
        self.playerX += m * Game.playerMove

# the two players
player1 = Player((Game.player1limitX[0] + Game.player1limitX[1]) / 2) #User
player2 = Player((Game.player2limitX[0] + Game.player2limitX[1]) / 2) #AI

class Stone():
    def __init__(self):
        self.stoneX = -1
        self.stoneY = -1
    
    def gotoP(self):
        if Game.turn == Game.Turn.P1:
            self.stoneX = player1.playerX
            self.stoneY = player1.playerY - Game.stoneHeight
        else:
            self.stoneX = player2.playerX + Game.playerWidth - Game.stoneWidth #right side of AI
            self.stoneY = player2.playerY - Game.stoneHeight

# the stone to throw
stone = Stone()

class AngleLine():
    def __init__(self):
        self.lineX = -1
        self.lineY = -1
        self.current_angle = 0
        self.current_vel = Game.defaultForceLen
    
    def gotoStone(self):
        self.lineX = stone.stoneX + (Game.stoneWidth // 2)
        self.lineY = stone.stoneY
        
        # Setting Default angle
        if Game.turn == Game.Turn.P1:
            self.current_angle = 45
        else:
            self.current_angle = 135
        
    def setAngle(self, angle):
        self.current_angle = angle
        
    def getAngle(self):
        return self.current_angle
    
    def change(self, m):
        self.current_angle += m * Game.angleChange
        
    def changeVel(self, m):
        self.current_vel += m * Game.velocityChange
    
    def getVel(self):
        return self.current_vel
        
    def getLines(self):
        theta = self.current_angle * (math.pi / 180) #convert to radian 
        g = 9.8 #gravityw
        
        listPoints = []
        
        curPos = ( stone.stoneX + Game.stoneWidth // 2 , stone.stoneY + Game.stoneHeight // 2 )
        grain_factor = 50
        for t in range(Game.approximationLinePoints * grain_factor):
            t /= grain_factor
            
            x = curPos[0] + self.getVel() * t * math.cos(theta)
            y = curPos[1] + self.getVel() * t * math.sin(theta) - 0.5 * g * t * t
            
            listPoints.append([x, y])
        
        lines = []
        for i in range(0, Game.approximationLinePoints * grain_factor - 1, 10):
            lines.append(QtCore.QLineF(listPoints[i][0], listPoints[i][1] - 2 * (listPoints[i][1] - curPos[1]), listPoints[i + 1][0], listPoints[i + 1][1] - 2 * (listPoints[i + 1][1] - curPos[1])))
        
        return lines
        
angle_line = AngleLine()

class Ui_MainWindow(QMainWindow):
    def __init__(self):
        super(Ui_MainWindow, self).__init__()
        self.setObjectName("MainWindow")
        # setting screen size
        self.resize(Game.screenWidth, Game.screenHeight)
        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("res/Instructions-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.actionExit = QtWidgets.QAction(self)
        self.actionExit.setObjectName("actionExit")
        self.menuFile.addAction(self.actionExit)
        self.menubar.addAction(self.menuFile.menuAction())
        self.actionExit.triggered.connect(self.closeEvent)
        
        _translate = QtCore.QCoreApplication.translate
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionExit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        
        
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        
        pen = QPen()
        pen.setBrush(QtGui.QBrush(Game.angleLineColor))
        self.painter = QPainter(self.image)
        self.painter.setPen(pen)
        
        self.stateMessage = ''
        
        # calling method
        self.homeUi()
        
    def homeUi(self):
        Game.state = Game.GameState.INTRO
        self.removeAllPaint()
        
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setObjectName("centralwidget")
        
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 2, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 2, 1, 1)
        
        self.label = QtWidgets.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Orbitron")
        font.setPointSize(28)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setFrameShadow(QtWidgets.QFrame.Raised)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 1, 1, 1)
        
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 1, 0, 1, 1)
        
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setEnabled(True)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.pushButton.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("res/Instructions-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton.setIcon(icon)
        self.pushButton.setObjectName("pushButton")
        self.gridLayout.addWidget(self.pushButton, 4, 1, 1, 1)
        self.pushButton.pressed.connect(self.insUi)
        
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem3, 0, 1, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem4, 5, 1, 1, 1)
        
        self.playButton = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.playButton.setFont(font)
        self.playButton.setAutoFillBackground(False)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("res/Play-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.playButton.setIcon(icon1)
        self.playButton.setObjectName("playButton")
        self.gridLayout.addWidget(self.playButton, 3, 1, 1, 1)
        self.playButton.pressed.connect(self.gameTypeUi)
        
        self.setCentralWidget(self.centralwidget)
        
        self.retranslateHomeUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateHomeUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "Stone Hitter"))
        self.pushButton.setText(_translate("MainWindow", "Instruction"))
        self.playButton.setText(_translate("MainWindow", "Play Now"))
        
        self.show()
        
    def gameTypeUi(self):
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        
        self.p2c = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.p2c.setFont(font)
        self.p2c.setObjectName("p2c")
        self.gridLayout.addWidget(self.p2c, 5, 3, 1, 1)
        self.p2c.pressed.connect(self.p2cSelection)
        
        self.p2p = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.p2p.setFont(font)
        self.p2p.setObjectName("p2p")
        self.gridLayout.addWidget(self.p2p, 5, 1, 1, 1)
        self.p2p.pressed.connect(self.p2pSelection)
        
        spacerItem = QtWidgets.QSpacerItem(20, 100, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout.addItem(spacerItem, 6, 1, 1, 3)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.gridLayout.addItem(spacerItem1, 1, 1, 1, 3)
        
        self.gameType = QtWidgets.QLabel(self.centralwidget)
        self.gameType.setTextFormat(QtCore.Qt.RichText)
        self.gameType.setAlignment(QtCore.Qt.AlignCenter)
        self.gameType.setObjectName("gameType")
        
        self.gridLayout.addWidget(self.gameType, 0, 0, 1, 5)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 5, 2, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem3, 5, 0, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem4, 5, 4, 1, 1)
        
        self.setCentralWidget(self.centralwidget)

        self.retranslateGameTypeUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateGameTypeUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.p2c.setText(_translate("MainWindow", "AI"))
        self.p2p.setText(_translate("MainWindow", "User"))
        self.gameType.setText(_translate("MainWindow", "<b style=\'font-size:25px\' >Choose Who Throw First<b>"))
        
    def p2pSelection(self):
        Game.turn = Game.Turn.P1
        self.playUi()
        
    def p2cSelection(self):
        Game.turn = Game.Turn.P2
        self.playUi()
        
    def insUi(self):
        Game.state = Game.GameState.INSTRUCT
        
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        
        self.backButton = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.backButton.setFont(font)
        self.backButton.setObjectName("backButton")
        self.gridLayout.addWidget(self.backButton, 8, 1, 1, 1)
        self.backButton.pressed.connect(self.homeUi)
        
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 8, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 8, 2, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout.addItem(spacerItem2, 6, 0, 1, 3)
        
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.plainTextEdit.setFont(font)
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.gridLayout.addWidget(self.plainTextEdit, 3, 0, 1, 3)
        
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout.addItem(spacerItem3, 2, 0, 1, 3)
        
        self.label = QtWidgets.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)
        
        self.setCentralWidget(self.centralwidget)

        self.retranslateInsUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateInsUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.backButton.setText(_translate("MainWindow", "Back to Main"))
        
        ins = '''
        1. There are two players in the game: User and AI.
        2. Each of the players will have his turn.
        3. User can change angle by Key S and W and speed by Key A and D.
        4. User can use Key Left Arrow and Right Arrow to move left and right.
        5. Space Key is used to throw the stone.
        6. Player who can hit his opponent gains a point.
        7. Press P to pause the game and then Esc to get to the main or again P to resume.
        8. Each of the players have 10 stones.
        9. Player who can hit more, is the winner.
        '''
        
        self.plainTextEdit.setPlainText(_translate("MainWindow", ins))
        self.label.setText(_translate("MainWindow", "INSTRUCTION"))
        
        self.show()
    
    def playUi(self):
        Game.state = Game.GameState.PLAY
        Game.Total_throw = 0
        
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setObjectName("centralwidget")
        
        # self.painter.fillRect(0, Game.screenHeight - Game.fieldHeight,
        #                      Game.screenWidth, Game.fieldHeight, Game.fieldColor)
        # self.painter.fillRect(Game.barPosX, Game.barPosY, Game.barWidth,
        #                      Game.barHeight, Game.fieldColor)
        
        self.setCentralWidget(self.centralwidget)
        
        self.show()
        
        global player1
        global player2
        player1 = Player((Game.player1limitX[0] + Game.player1limitX[1]) / 2)
        player2 = Player((Game.player2limitX[0] + Game.player2limitX[1]) / 2) 
        
        # Main GameLoop Begins
        
        self.startToMove()
        
        # Main GameLoop Ends
        
    def startToMove(self):
        Game.action = Game.Action.MOVE
        stone.gotoP()
        
        self.stateMessage = 'Take your position'
        self.paintField()
        QTimer.singleShot(2000, self.switchMoveToThrow)
        
        
        if Game.type == Game.Type.P2C and Game.turn == Game.Turn.P1:
            player2.playerX = random.randint(Game.player2limitX[0], Game.player2limitX[1])
            self.paintField()
        
    
    def switchMoveToThrow(self):
        self.stateMessage = 'Aim and Throw'
        Game.action = Game.Action.SET_ANGLE_FORCE
        angle_line.gotoStone()
        
        self.paintField()
        
        if Game.type == Game.Type.P2C and Game.turn == Game.Turn.P2 :
            Game.action = Game.Action.THROW
            
            #to feed the model
            imageCrop = 300
            imageResize = (80,30)
            
            computer_input = qimage2ndarray.byte_view(self.image)[imageCrop:]
            computer_input = cv2.resize(computer_input, imageResize)

            computer_input = computer_input.reshape((1,) + computer_input.shape)
            computer_input = computer_input / 255
            
            computer_output = Game.computer.predict(computer_input)
            angle = computer_output[0][0]
            velocity = computer_output[0][1] # - 2
#            
            angle_line.current_angle = angle
            angle_line.current_vel = velocity
            
#           print(angle, velocity)
            
            self.throw()
            self.paintField()
            angle_line.current_vel = Game.defaultForceLen
            
    def throw(self):
        prevX = stone.stoneX
        prevY = stone.stoneY
        v0 = angle_line.getVel()
        theta = angle_line.current_angle * math.pi / 180
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        g = 9.8
        ground = Game.screenHeight - Game.fieldHeight - Game.stoneWidth
        
        t = 0
        
        if Game.turn == Game.Turn.P1:
            player = player1
            opponent = player2
        else:
            player = player2
            opponent = player1
        
        while stone.stoneY < ground:
            if Game.state == Game.GameState.PAUSED:
                QtTest.QTest.qWait(1000)
                continue
            

            x_ = v0 * t * cos_theta
            y_ = v0 * t * sin_theta - 0.5 * g * t * t
            
#            if stone.stoneY >= opponent.playerY: 
#                print('distance travelled = ', x_)
            
            stone.stoneX = prevX + x_
            stone.stoneY = prevY - y_
            
            if stone.stoneY > ground:
                stone.stoneY = ground
                # unsuccessful
                self.stateMessage = 'Missed...'
                
                break
            
            if stone.stoneX > Game.barPosX - 60 - Game.stoneWidth  and stone.stoneX < Game.barPosX  + Game.barWidth:
                if stone.stoneY > Game.barPosY - Game.stoneHeight:
                    # unsuccessful
                    self.stateMessage = 'Missed...'
                   
                    break
                
            if stone.stoneX > opponent.playerX - Game.stoneWidth and stone.stoneX < opponent.playerX + Game.playerWidth:
                if stone.stoneY > opponent.playerY - Game.stoneHeight:
                    # successful
                    self.stateMessage = 'Hit!!'
            
                    player.score += 1
                    break
                
            self.paintField()
            QtTest.QTest.qWait(50)
            
            t += 0.3
        
        if Game.turn == Game.Turn.P1:
            player1.throw -= 1
            Game.turn = Game.Turn.P2
        else:
            player2.throw -= 1
            Game.turn = Game.Turn.P1

        if player1.throw == 0 and player2.throw == 0:
            if player1.score == player2.score:
                self.stateMessage = 'Draw..! <br> Press any key to continue'
                #thread.start_new_thread(self.playMusic, ('res\\Applauding-and-cheering.mp3', 'ignore it'))
                Game.state = Game.GameState.GAMEOVER

            elif player1.score > player2.score:
                self.stateMessage = 'You Win..! <br> Press any key to continue'
               # thread.start_new_thread(self.playMusic, ('res\\Applauding-and-cheering.mp3', 'ignore it'))
                Game.state = Game.GameState.GAMEOVER
        
            elif player2.score > player1.score:
                self.stateMessage = 'You lose..! <br> Press any key to continue'
               # thread.start_new_thread(self.playMusic, ('res\\fail-trombone-01.mp3', 'ignore it'))
                Game.state = Game.GameState.GAMEOVER 
        else:
            QTimer.singleShot(500, self.startToMove)
                
        
    def keyPressEvent(self, event):
#        print(event)
        if event.key() == Qt.Key_P and Game.state == Game.GameState.PLAY:
            Game.state = Game.GameState.PAUSED
            self.prevMessage = self.stateMessage
            self.stateMessage = 'Paused'
            self.paintField()
            
        elif Game.state == Game.GameState.PAUSED:
            if event.key() == Qt.Key_P:
                Game.state = Game.GameState.PLAY
                self.stateMessage = self.prevMessage
                self.paintField()
            elif event.key() == Qt.Key_Escape:
                QTimer.singleShot(50, self.homeUi)
                
        elif Game.state == Game.GameState.PLAY and Game.action != Game.Action.THROW:
            if Game.turn == Game.Turn.P1:
                
                if Game.action == Game.Action.SET_ANGLE_FORCE:
                    if event.key() == Qt.Key_W and angle_line.getAngle() < Game.player1AngleLimit[1]:
                        angle_line.change(1)
                    elif event.key() == Qt.Key_S and Game.player1AngleLimit[0] < angle_line.getAngle() :
                        angle_line.change(-1)
                    elif event.key() == Qt.Key_A and angle_line.getVel() > Game.minForceLen:
                        angle_line.changeVel(-1)
                    elif event.key() == Qt.Key_D and Game.maxForceLen > angle_line.getVel():
                        angle_line.changeVel(1)
                    elif event.key() == Qt.Key_Space:
                        Game.action = Game.Action.THROW
                        self.throw()
                        angle_line.current_vel = Game.defaultForceLen
                        
                else:
                    return
            else:
                if Game.action == Game.Action.MOVE:
                    if event.key() == Qt.Key_Left and Game.player1limitX[0] < player1.playerX:
                        player1.move(-1)
                    elif event.key() == Qt.Key_Right and player1.playerX < Game.player1limitX[1]:
                        player1.move(1)
                 
                else:
                    return
           
            self.paintField()
            
        elif Game.state == Game.GameState.GAMEOVER:
            QTimer.singleShot(50, self.homeUi)
        
#        print(self.position)
    
    def removeAllPaint(self):
        self.painter.fillRect(self.image.rect(), Qt.white)
        self.update()
    
    def paintField(self):
        # remove all paint
        self.removeAllPaint()
        # paint field
        self.painter.fillRect(0, int(Game.screenHeight - Game.fieldHeight),
                          int(Game.screenWidth), int(Game.fieldHeight), Game.fieldColor)
        # paint bar1
        self.painter.fillRect(int(Game.barPosX), int(Game.barPosY), int(Game.barWidth),
                          int(Game.barHeight), Game.barColor)
        # paint bar2
        self.painter.fillRect(int(Game.barPosX-60), int(Game.barPosY), int(Game.barWidth),
                          int(Game.barHeight), Game.barColor)
        # paint User
        self.painter.fillRect(int(player1.playerX), int(player1.playerY), int(Game.playerWidth),
                              int(Game.playerHeight), Game.playerColor)
        # paint AI
        self.painter.fillRect(int(player2.playerX), int(player2.playerY), int(Game.playerWidth),
                              int(Game.playerHeight), Game.playerColor)
        # paint stone
        self.painter.fillRect(int(stone.stoneX), int(stone.stoneY), int(Game.stoneWidth),
                              int(Game.stoneWidth), Game.stoneColor)
        
        self.scoreText1 = '<b style="font-size:16px;">User : ' + str(player1.score) + " Remaining : " + str(player1.throw) + '<\b>'
        
        self.scoreText2 = '<b style="font-size:16px;">AI : ' + str(player2.score) +  " Remaining : " + str(player2.throw) + '<\b>'
            
        self.message = '<b style="font-size:40px;">' + self.stateMessage + '<\b>'
        
        text1 = QtGui.QStaticText(self.scoreText1)
        text1.setTextFormat(Qt.RichText)
        text2 = QtGui.QStaticText(self.scoreText2)
        text2.setTextFormat(Qt.RichText) 
        message = QtGui.QStaticText(self.message)
        message.setTextFormat(Qt.RichText)
        self.painter.drawStaticText(Game.scoreText1PosX, Game.scoreText1PosY, text1)
        self.painter.drawStaticText(Game.scoreText2PosX, Game.scoreText2PosY, text2)
        self.painter.drawStaticText(Game.stateMessageBoxX, Game.stateMessageBoxY, message)
        
        if Game.action == Game.Action.SET_ANGLE_FORCE:
            self.painter.drawLines(angle_line.getLines()) 
        
        self.update()
    
    def paintEvent(self, event):
        canvas = QPainter(self)
        if Game.state == Game.GameState.PLAY or Game.state == Game.GameState.GAMEOVER:
            canvas.drawImage(self.rect(), self.image, self.image.rect())
        elif Game.state == Game.GameState.PAUSED:
            message = '<b style="font-size:40px;">PAUSED<br> Press P to play or Esc to exit<\b>'
            message = QtGui.QStaticText(message)
            message.setTextFormat(Qt.RichText)
            canvas.drawStaticText(Game.stateMessageBoxX, Game.stateMessageBoxY, message)
        
    def playMusic(self, file, ignored):
        playsound(file)
        
    def closeEvent(self, event):
#        QCoreApplication.quit()
            
        sys.exit()
        

App = QApplication(sys.argv)
 
# create the instance of our Window
window = Ui_MainWindow()
 
# start the app
sys.exit(App.exec())