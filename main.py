#!/usr/bin/env python3
import sys
from PyQt4 import QtCore, QtGui
import time
import os
import struct
import numpy.core._methods
import numpy.lib.format
from matplotlib.lines import Line2D
# import matplotlib.backends.backend_qt4agg
import matplotlib
import io
matplotlib.use('QT4Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np
from random import shuffle
import copy
from umrrmessage import UMRRMessages

class MainWindow(QtGui.QWidget):
	def __init__(self):
		QtGui.QWidget.__init__(self)
		self.initUI()
		self.setAcceptDrops(True)


	def initUI(self):
		self.Q = 0.0 ## ковариация шума процесса,имеет прямую зависимость от дисперсии
		self.R = 0.0 ## (ковариация шума измерений) ошибка измерения может быть определена испытанием измерительных приборов и определением погрешности их измерения
		self.H = 0.0 ## матрица измерений, отображающая отношение измерений и состояний
		self.F = 1.0 ## матрица реакции на переход между системами, по умолчанию еденица

		self.state  = 0.0 ## предсказанное значание
		self.covariance = 0.0 ## предсказанная ошибка ковариация

		self.path = os.getcwd()
		self.minLevel = 30
		self.frameZone = 5
		self.speedDelta = 3
		self.minSize = 10
		self.quality = 30
		self.getPattern()
		colorTypes = ["Стандарт (X - FRAME ; Y - SPEED)", "Окрасить график по значению TYPE (X - FRAME ; Y - SPEED)", "Окрасить график по уровням LEVEL  (X - FRAME ; Y - SPEED)", "Фильтр (использовать настройки)", "Использование .trk файл"]
		self.indexArray = []
		self.grid = QtGui.QGridLayout()
		self.grid.setSpacing(10)

		self.infoChooseFile = QtGui.QLabel("Выберите файл обработки")
		self.infoType = QtGui.QLabel("Выберитe тип окраски графика")
		self.infoLevels = QtGui.QLabel("LEVELS")
		self.colorTypeList = QtGui.QComboBox()
		self.colorTypeList.addItems(colorTypes)
		self.colorTypeList.setMaximumWidth(350)

		self.graphByLevelLine = QtGui.QLineEdit()
		self.graphByLevelLine.setMaximumWidth(350)
		self.graphByLevelLine.setReadOnly(True)
		self.colorTypeList.currentIndexChanged.connect(self.changedColorType)

		self.selectFileButton = QtGui.QPushButton("...")
		self.selectFileButton.clicked.connect(self.selectFile)
		self.selectFileButton.setMaximumWidth(50)
		self.filePathLine = QtGui.QLineEdit()
		self.useNMEA = QtGui.QCheckBox("отобразить кривую движения из NMEA")
		self.useNMEA.setChecked(False)
		self.useNMEA.setTristate(False)
		self.gridFile = QtGui.QGridLayout()
		self.filePathLine.setMinimumWidth(500)
		self.gridFile.addWidget(self.infoChooseFile, 1, 0)
		self.gridFile.addWidget(self.filePathLine, 1, 1)
		self.gridFile.addWidget(self.selectFileButton, 1, 2)
		self.gridFile.addWidget(self.infoType, 2, 0)
		self.gridFile.addWidget(self.colorTypeList, 2, 1)
		self.gridFile.addWidget(self.infoLevels, 3, 0)
		self.gridFile.addWidget(self.graphByLevelLine, 3, 1)
		self.gridFile.addWidget(self.useNMEA, 4, 1)

		self.chooseFileGroup = QtGui.QGroupBox("Шаг №1")
		self.chooseFileGroup.setLayout(self.gridFile)
		self.chooseFileGroup.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))

		self.gridStart = QtGui.QGridLayout()
		self.gridStart.setSpacing(10)
		self.startButton = QtGui.QPushButton("Запустить обработку")
		self.startButton.setStyleSheet("font: bold 10px;padding: 10px;min-width: 10em;")
		self.startButton.clicked.connect(self.start)

		self.settingsButton = QtGui.QPushButton("Изменить настройки")
		self.settingsButton.setStyleSheet("font: bold 10px;padding: 10px;min-width: 10em;")
		self.settingsButton.clicked.connect(self.new_pattern)


		self.gridStart.addWidget(self.startButton, 1, 1, QtCore.Qt.AlignCenter)
		self.gridStart.addWidget(self.settingsButton, 2, 1, QtCore.Qt.AlignCenter)

		self.startGroup = QtGui.QGroupBox("Шаг №2")
		self.startGroup.setLayout(self.gridStart)
		self.startGroup.setSizePolicy(
			QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))


		self.grid.addWidget(self.chooseFileGroup, 1, 0)
		self.grid.addWidget(self.startGroup, 2, 0)

		self.setLayout(self.grid)

	def setKalmanFilterSimple(self, f, h, q, r):

		self.F = f
		self.H = h
		self.Q = q
		self.R = r

	def setState(self, state, cov):
		self.state = state
		self.covariance = cov

	def correct(self, data):
		x0 = self.F * self.state
		p0 = self.F * self.covariance * self.F + self.Q


		k = self.H * p0 / (self.H * p0 * self.H + self.R)
		self.state = x0 + k * (data - self.H * x0)
		self.covariance = (1 - k * self.H) * p0

	def getPattern(self):
		if os.path.isfile(self.path+"//pattern"):
			try:
				f = open(self.path+"//pattern")
				self.minLevel, self.frameZone, self.speedDelta, self.minSize, self.quality = [float(line.rstrip()) for line in f.readlines() ]
				f.close()
			except:
				pass

	def btnstate(self, b):
		if b.isChecked():
			return 1
		else:
			return 0

	def changedColorType(self):
		if self.colorTypeList.currentIndex()==2:
			self.graphByLevelLine.setReadOnly(False)
		else:
			self.graphByLevelLine.setReadOnly(True)

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		for url in event.mimeData().urls():
			path = url.toLocalFile()
			if os.path.isfile(path):
				self.selectFile(path)

	def selectFile(self, path=None):
		oldContent = self.filePathLine.text()
		if path is False:
			path = QtGui.QFileDialog.getOpenFileName()
		self.filePathLine.setText(path)

	def new_pattern(self):
		def update():
			self.minLevel = float(str(input1.text()).strip())
			self.frameZone = float(str(input2.text()).strip())
			self.speedDelta = float(str(input3.text()).strip())
			self.minSize = float(str(input4.text()).strip())
			self.quality = float(str(input5.text()).strip())
			try:
				self.deploy(self.prepareTest())
			except:
				# вставить ошибку об отсутвии созданого графика
				pass
			msg_box.show()
		def saveButton():
			self.minLevel = float(str(input1.text()).strip())
			self.frameZone = float(str(input2.text()).strip())
			self.speedDelta = float(str(input3.text()).strip())
			self.minSize = float(str(input4.text()).strip())
			self.quality = float(str(input5.text()).strip())
			lm = float(str(input1.text()).strip())
			fm = float(str(input2.text()).strip())
			sp = float(str(input3.text()).strip())
			ms = float(str(input4.text()).strip())
			q = float(str(input5.text()).strip())
			f = open(self.path + '\\pattern', "w")
			f.write(str(lm) + "\n")
			f.write(str(fm) + "\n")
			f.write(str(sp) + "\n")
			f.write(str(ms) + "\n")
			f.write(str(q) + "\n")
			f.close()
			# self.plt.cla()
			msg_box.close()
		msg_box = QtGui.QDialog()
		msg_box.setWindowTitle("Pattern")
		msg_box.setWindowModality(QtCore.Qt.NonModal)
		msg_box.setFixedSize(430, 260)
		l1 = QtGui.QLabel(msg_box)
		l1.move(30, 20)
		l1.setText("     Настройки параметров деления на группы")
		l2 = QtGui.QLabel(msg_box)
		l2.setText("Минимальное значение Level")
		l2.move(10, 45)
		l3 = QtGui.QLabel(msg_box)
		l3.setText("Максимальное расстояние между целями в Frame")
		l3.move(10, 70)
		l4 = QtGui.QLabel(msg_box)
		l4.setText("Максимальная разница в скорости (км/ч)")
		l4.move(10, 95)
		l5 = QtGui.QLabel(msg_box)
		l5.setText("     Настройки отбора групп")
		l5.move(30, 120)
		l6 = QtGui.QLabel(msg_box)
		l6.setText("Минимальный размер группы")
		l6.move(10, 145)
		l7 = QtGui.QLabel(msg_box)
		l7.setText("Минимальное среднее значение Level")
		l7.move(10, 170)

		input1 = QtGui.QLineEdit(str(self.minLevel), msg_box)
		input1.move(280, 45)
		input2 = QtGui.QLineEdit(str(self.frameZone), msg_box)
		input2.move(280, 70)
		input3 = QtGui.QLineEdit(str(self.speedDelta), msg_box)
		input3.move(280, 95)
		input4 = QtGui.QLineEdit(str(self.minSize), msg_box)
		input4.move(280, 145)
		input5 = QtGui.QLineEdit(str(self.quality), msg_box)
		input5.move(280, 170)

		b1 = QtGui.QPushButton("Save", msg_box)
		b1.move(280, 220)
		b2 = QtGui.QPushButton("Update graph", msg_box)
		b2.move(10, 220)
		msg_box.connect(b1, QtCore.SIGNAL("clicked()"), saveButton)
		msg_box.connect(b2, QtCore.SIGNAL("clicked()"), update)

		msg_box.show()

	def indexies(self, path):
		self.indexArray.clear()
		self.indexArray.append(0)
		file = io.FileIO(path)
		firstIndex = file.read(8)
		magic = firstIndex[:4]
		firstIndex = firstIndex[4:]

		firstIndex = struct.unpack('i', firstIndex)[0]
		lastIndexIntSum = firstIndex
		lastIndexint = firstIndex
		nextIndex = b''

		if magic == b'\x063"\x11' or magic == b'E3"\x11':
			file.close()
			file = io.FileIO(path)
			TotalSum = 0
			while True:
				nextIndex = file.read(16432)
				jpglen = nextIndex[16396:16400]
				if len(jpglen) != 4:
					break
				try:
					jpglen = int(struct.unpack('i', jpglen)[0])
				except:
					break
				nextIndexSum = jpglen + 16432
				TotalSum = TotalSum + nextIndexSum
				self.indexArray.append(TotalSum)
				toEnd = file.read(jpglen)

		if magic == b'\x073"\x11':
			while b'\xff\xd9' not in nextIndex:
				self.indexArray.append(lastIndexIntSum)
				nextIndex = file.read(lastIndexint)
				nextIndex = nextIndex[-4:]
				try:
					nextIndexint = struct.unpack('i', nextIndex)[0]
				except:
					break
				lastIndexIntSum = lastIndexIntSum + nextIndexint
				lastIndexint = nextIndexint
		file.close()


	def get_cmap(self, n, name='hsv'):
		return plt.cm.get_cmap(name, n)

	def parseLevels(self):
		text = self.graphByLevelLine.text()
		levels = text.split(",")
		return levels

	def appendLists(self,dict ,number):
		for i in range(0, number):
			dict.append([])
		return dict




	def prepareTypeFramexSpeed(self):
		eight = (0.1, 0.5, 0.1, 0.5)
		two = (0.7, 0.5, 0.7, 0.5)
		self.legend_elements = [
			Line2D([0], [0], marker='o', color=eight, label="8", markersize=5)]
		self.legend_elements.append(
			Line2D([0], [0], marker='o', color=two, label="2", markersize=5))

		delay = 0
		colorXY = defaultdict(list)
		colorXY[eight] = self.appendLists(colorXY[eight], 6)
		colorXY[two] = self.appendLists(colorXY[two], 6)
		for frame in self.graphlist.keys():
			for target in range(0, len(self.graphlist[frame][0])):
				if self.graphlist[frame][3][target] == 8:
					colorXY[eight][0].append(frame)
					colorXY[eight][1].append(self.graphlist[frame][1][target])
					colorXY[eight][2].append(frame)
					colorXY[eight][3].append(self.graphlist[frame][2][target])
					colorXY[eight][4].append(self.graphlist[frame][3][target])
					colorXY[eight][5].append(self.graphlist[frame][0][target])

				if self.graphlist[frame][3][target] == 2:
					colorXY[two][0].append(frame)
					colorXY[two][1].append(self.graphlist[frame][1][target])
					colorXY[two][2].append(frame)
					colorXY[two][3].append(self.graphlist[frame][2][target])
					colorXY[two][4].append(self.graphlist[frame][3][target])
					colorXY[two][5].append(self.graphlist[frame][0][target])
			delay += len(self.graphlist[frame][0])
		return colorXY


	def prepareStandartFramexSpeed(self):
		color = (0.1, 0.5, 0.1, 0.5)
		colorXY = defaultdict(list)
		colorXY[color] = self.appendLists(colorXY[color], 6)
		for frame in self.graphlist.keys():
			for target in range(0, len(self.graphlist[frame][0])):
				colorXY[color][0].append(frame)
				colorXY[color][1].append(self.graphlist[frame][1][target])
				colorXY[color][2].append(frame)
				colorXY[color][3].append(self.graphlist[frame][2][target])
				colorXY[color][4].append(self.graphlist[frame][3][target])
				colorXY[color][5].append(self.graphlist[frame][0][target])
		return colorXY


	# def prepareStandartFramexSpeedUseLess(self):
	# 	color = (0.1, 0.5, 0.1, 0.5)
	# 	delay = 0
	# 	colorXY = defaultdict(list)
	# 	colorXY[color] = self.appendLists(colorXY[color], 6)
	# 	for frame in self.graphlist.keys():
	# 		for target in range(0, len(self.graphlist[frame][0])):
	# 			colorXY[color][0].append(target + delay)
	# 			colorXY[color][1].append(self.graphlist[frame][1][target])
	# 			colorXY[color][2].append(frame)
	# 			colorXY[color][3].append(self.graphlist[frame][2][target])
	# 			colorXY[color][4].append(self.graphlist[frame][3][target])
	# 			colorXY[color][5].append(self.graphlist[frame][0][target])
	# 		delay += len(self.graphlist[frame][0])
	# 	return colorXY

	def prepareLevelFramexSpeed(self):
		levelsList = self.parseLevels()
		levelsList.sort(key=int)
		cmap = self.get_cmap(len(levelsList) + 2)
		delay = 0
		colorXY = defaultdict(list)
		color = (1, 1, 1, 1)
		color = color[:-1] + (color[-1] * 0.5,)
		color = color[:1] + (color[1] * 0.5,) + color[2:]
		self.legend_elements = [
			Line2D([0], [0], marker='o', color=color, label="<" + str(levelsList[0]), markersize=5)]
		for level in range(0, len(levelsList)):
			color = cmap(level)
			color = color[:-1] + (color[-1] * 0.5,)
			color = color[:1] + (color[1] * 0.5,) + color[2:]
			self.legend_elements.append(
				Line2D([0], [0], marker='o', color=color, label=">" + str(levelsList[level]), markersize=5))


		for frame in self.graphlist.keys():
			for target in range(0, len(self.graphlist[frame][0])):
				color = (1, 1, 1, 1)
				for level in range(0, len(levelsList)):
					if int(self.graphlist[frame][2][target]) >= int(levelsList[level]):
						color = cmap(level)
				color = color[:-1] + (color[-1] * 0.5,)
				color = color[:1] + (color[1] * 0.5,) + color[2:]
				colorXY[color] = self.appendLists(colorXY[color], 6)
				colorXY[color][0].append(frame)
				colorXY[color][1].append(self.graphlist[frame][1][target])
				colorXY[color][2].append(frame)
				colorXY[color][3].append(self.graphlist[frame][2][target])
				colorXY[color][4].append(self.graphlist[frame][3][target])
				colorXY[color][5].append(self.graphlist[frame][0][target])
			delay += len(self.graphlist[frame][0])
		return colorXY

	# def prepareStandartFramexLevel(self):
	# 	color = (0.1, 0.5, 0.1, 0.5)
	# 	delay = 0
	# 	colorXY = defaultdict(list)
	# 	colorXY[color] = self.appendLists(colorXY[color], 5)
	# 	for frame in self.graphlist.keys():
	# 		for target in range(0, len(self.graphlist[frame][0])):
	# 			colorXY[color][0].append(target + delay)
	# 			colorXY[color][1].append(self.graphlist[frame][2][target])
	# 			colorXY[color][2].append(frame)
	# 			colorXY[color][3].append(self.graphlist[frame][2][target])
	# 			colorXY[color][4].append(self.graphlist[frame][3][target])
	# 			delay += 1
	# 	return colorXY


	def prepareTest(self):
		def getQ(c):
			q = 0
			for lvl in colorXY[c][3]:
				q += lvl
			return (q/len(colorXY[c][3]))

		def deleteTrash():
			clone = copy.copy(colorXY)
			for c in clone.keys():
				# print("{}  {}  {}".format(getQ(c), len(clone[c][0]), colorXY[c][6][-1]))
				if getQ(c) < self.quality or len(clone[c][0]) < self.minSize:
					colorXY.pop(c)
			changeInter = 0
			cmap = self.get_cmap(len(list(colorXY.keys())))
			clone = copy.copy(colorXY)
			self.blackFilter = defaultdict(list)
			self.blackFilter["black"] = self.appendLists(self.blackFilter["black"], 2)
			for c in clone.keys():
				colorXY.pop(c)
				col = cmap(changeInter)
				col = col[:-1] + (col[-1] * 0.5,)
				col = col[:1] + (col[1] * 0.5,) + col[2:]
				self.setState(clone[c][1][0], 0.1)

				for iterat in range(0, len(clone[c][0])):
					self.correct(clone[c][1][iterat])
					self.blackFilter["black"][1].append(self.state)
					self.blackFilter["black"][0].append(clone[c][0][iterat])
					# print(clone[c][1][iterat])
					iterat += 1
				colorXY[col] = clone[c]
				changeInter += 1

		def searchInLists(f, t):
			ts = self.graphlist[f][1][t]
			corExist = False
			for c in colorXY.keys():
				for inListTar in colorXY[c][1][-3:]:
					if (abs(ts-inListTar) < self.speedDelta) and ((f - colorXY[c][2][-1]) < self.frameZone):
						corExist = True
						break
				if corExist:
					colorXY[c][0].append(f)
					# colorXY[c][1].append(float(self.graphlist[f][1][t])*0.7 + float(colorXY[c][1][-1:][0])*0.3)
					colorXY[c][1].append(self.graphlist[f][1][t])
					colorXY[c][2].append(f)
					colorXY[c][3].append(self.graphlist[f][2][t])
					colorXY[c][4].append(self.graphlist[f][3][t])
					colorXY[c][5].append(self.graphlist[f][0][t])
					colorXY[c][6].append(c)
					colorXY[c][7].append(self.graphlist[f][4][t])
					colorXY[c][8].append(self.graphlist[f][5][t])
					break
			if not corExist:
				color = cmap(self.listCount)
				colorXY[color] = self.appendLists(colorXY[color], 9)
				colorXY[color][0].append(f - trashCount)
				colorXY[color][1].append(self.graphlist[f][1][t])
				colorXY[color][2].append(f)
				colorXY[color][3].append(self.graphlist[f][2][t])
				colorXY[color][4].append(self.graphlist[f][3][t])
				colorXY[color][5].append(self.graphlist[f][0][t])
				colorXY[color][6].append(color)
				colorXY[color][7].append(self.graphlist[f][4][t])
				colorXY[color][8].append(self.graphlist[f][5][t])
				self.listCount += 1


		cmap = self.get_cmap(2000)
		colorXY = defaultdict(list)
		delay = 0
		self.listCount = 0
		self.setKalmanFilterSimple(1, 1, 2, 30)
		for frame in self.graphlist.keys():
			trashCount = 0
			for target in range(0, len(self.graphlist[frame][0])):
				if self.graphlist[frame][2][target] > self.minLevel:
					searchInLists(frame, target)
				else:
					trashCount += 1
		deleteTrash()

		return colorXY

	def prepareTrkTargets(self):
		targets = defaultdict(list)
		file = open(self.fileForProcessing + ".trk", "r")
		for line in file.readlines():
			values = line.split(";")
			if str.isdigit(values[0]):
				if values[2] in targets.keys():
					targets[values[2]][0].append(values[0])
					targets[values[2]][1].append(values[1])
				else:
					targets[values[2]] = self.appendLists(targets[values[2]], 2)
					targets[values[2]][0].append(values[0])
					targets[values[2]][1].append(values[1])
		return targets

	def addTrkTargets(self, preparedTargets, trkTargets):
		colorsNumber = len(trkTargets.keys())
		cmap = self.get_cmap(colorsNumber + 2)
		colorIndx = 0
		for trkT in trkTargets.keys():
			color = cmap(colorIndx)
			if int(trkT) == -1:
				color = "black"
				preparedTargets[color] = self.appendLists(preparedTargets[color], 2)
			preparedTargets[color] = self.appendLists(preparedTargets[color], 2)
			delay = 0
			for frameN in trkTargets[trkT][0]:
				if int(frameN) in preparedTargets[(0.1, 0.5, 0.1, 0.5)][2]:
					frameNumberPosInList = preparedTargets[(0.1, 0.5, 0.1, 0.5)][2].index(int(frameN))
					preparedTargets[color][0].append(int(preparedTargets[(0.1, 0.5, 0.1, 0.5)][0][frameNumberPosInList]))
					preparedTargets[color][1].append(float(trkTargets[trkT][1][delay]))
				else:
					preparedTargets[color][0].append(int(frameN))
					preparedTargets[color][1].append(float(trkTargets[trkT][1][delay]))
				delay += 1
			colorIndx += 1

		return preparedTargets

	def drawGraph(self):

		self.plt = plt
		
		self.fig = self.plt.figure()
		self.ax = self.fig.add_subplot(111)
		self.ax.clear()
		self.fig.tight_layout()

		self.colorType = self.colorTypeList.currentIndex()
		if self.colorType == 0:
			preparedTargets = self.prepareStandartFramexSpeed()

		elif self.colorType == 1:
			preparedTargets = self.prepareTypeFramexSpeed()
			self.plt.legend(handles=self.legend_elements, loc="upper right")

		elif self.colorType == 2:
			preparedTargets = self.prepareLevelFramexSpeed()
			self.plt.legend(handles=self.legend_elements, loc="upper right")

		# elif self.colorType == 3:
		# 	preparedTargets = self.prepareStandartFramexLevel()
		elif self.colorType == 3:
			preparedTargets = self.prepareTest()

		elif self.colorType == 4:
			self.originTargets = self.prepareStandartFramexSpeed()
			if os.path.isfile(self.fileForProcessing + ".trk"):
				trkTargets = self.prepareTrkTargets()
				preparedTargets = self.addTrkTargets(copy.copy(self.originTargets), trkTargets)
			else:
				preparedTargets = self.originTargets

		# RandomValue  = [i for i in range(len(list(result.keys())) + 1)]
		# shuffle(RandomValue)
		self.deploy(preparedTargets)

	def onclick(self, event):
		colorType = self.colorTypeList.currentIndex()
		ind = event.ind[0]
		data = event.artist.get_offsets()
		xdata, ydata = data[ind, :]
		xWithDelay = xdata
		speed = ydata
		frame = xWithDelay
		level = "-"
		type = "-"
		targetNum = "-"
		for color in self.preparedTargets.keys():
			listOFCond = [i for i in range(0, len(self.preparedTargets[color][0])) if str(self.preparedTargets[color][0][i]) == str(int(xWithDelay))]
			if len(listOFCond) != 0:
				for indx in listOFCond:
					if self.preparedTargets[color][1][indx] == ydata:
						try:
							level = self.preparedTargets[color][3][indx]
							type = self.preparedTargets[color][4][indx]
							targetNum = self.preparedTargets[color][5][indx]
						except:
							break
						break
			# ibd = self.preparedTargets[color][6][indexOfX]
			# if colorType == 3:
			# 	rangex = self.preparedTargets[color][7][indexOfX]
			# 	anglex = self.preparedTargets[color][8][indexOfX]

		# if colorType != 3:
		self.textBox.set_text(
			"FRAME: {}\nTARGET: {}\nSPEED: {}\nLEVEL: {}\nTYPE: {}".format(frame, targetNum, speed, level, type))
		# else:
		# 	self.textBox.set_text(
		# 		"FRAME: {}\nTARGET: {}\nSPEED: {}\nLEVEL: {}\nTYPE: {}\nCOLOR: {}\nRANGE: {}\nANGLE: {}".format(frame,
		# 																										targetNum,
		# 																										speed,
		# 																										level,
		# 																										type,
		# 																										ibd,
		# 																										rangex,
		# 																										anglex))
		self.plt.draw()

	def deploy(self, preparedTargets):
		self.preparedTargets = preparedTargets
		# self.plt.clf()

		self.plt.xlabel("frames")
		self.plt.ylabel("speed (km/h)")
		self.plt.title(self.fileForProcessing)
		self.fig.canvas.mpl_connect('pick_event', self.onclick)

		self.props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
		self.textBox = self.ax.text(0.01, 0.98, str("NONE"), transform=self.ax.transAxes, fontsize=14,
									verticalalignment = "top",
									bbox = self.props)

		for color in preparedTargets.keys():
			self.ax.scatter(preparedTargets[color][0], preparedTargets[color][1], color=color, picker=5)
		# if self.colorType == 3:
		# 	self.ax.scatter(self.blackFilter["black"][0], self.blackFilter["black"][1], color="black" , s=3)
		start, end = self.ax.get_xlim()
		step = ((end // 10) // 50) * 50
		# self.ax.xaxis.set_ticks(np.arange(0, end, step))

		if self.btnstate(self.useNMEA):
			if self.colorType == 4:
				x, y = self.connectRMCwithCT(self.captureTimeList, self.originTargets)

			else:
				x, y = self.connectRMCwithCT(self.captureTimeList, preparedTargets)
			self.ax.plot(x, y, color="black", linestyle='--', marker="o")
		self.ax.grid(True)
		# self.plt.legend(handles=self.legend_elements, loc="upper right")
		self.plt.draw()
		self.plt.show()

	def connectRMCwithCT(self, captureT, result):
		rmc = self.parseNMEA(self.fileForProcessing + ".nmea")
		x = []
		y = []
		for line in rmc.keys():
			for frame in captureT.keys():
				findTr = 0
				frameT, frameMills, data = captureT[frame].split(".")

				rmcTimeWithoutMS = rmc[line][0].split(".")[0]
				if (rmcTimeWithoutMS == frameT) and (rmc[line][8] == data):
					for color in result.keys():

						if frame in result[color][2]:
							indexOfX = result[color][2].index(frame)
							xWithDelay = result[color][0][indexOfX]
							x.append(xWithDelay)
							y.append(rmc[line][6])
							findTr = 1
							break
					if findTr == 1:
						break
		return x, y


	def parseNMEA(self, file):
		file = open(file)
		iter = 0
		parsedLines = defaultdict(list)
		for line in file.readlines():
			startMarker = line[1:6]
			if startMarker == "GNRMC":
				dataRaw = line[7:].split(",")
				time, timeStatus, latitude, latitudeDir, longitude, longitudeDir, speed, speedDir, date, declination, declinationDir, type = dataRaw
				# print(time," ", timeStatus," ", latitude," ", latitudeDir," ", longitude," ", longitudeDir," ", speed," ", speedDir," ", date," ", declination," ", declinationDir," ", type)
				if time != "":
					hh, mm, ss = [time[i:i+2] for i in range(0, len(time)-4, 2)]
					mills = time.split(".")[1]
				if speedDir != "":
					speed = float(speed) * 1.852
				parsedLines[iter] = time, timeStatus, latitude, latitudeDir, longitude, longitudeDir, speed, speedDir, date, declination, declinationDir, type
				iter += 1
		return parsedLines



	def rawSearch(self):
		self.csvText = []
		self.csvText.append("FRAME;TARGET;RANGE;ANGLE;SPEED;LEVEL;TYPE;SENSOR STATUS;TIME; ; ;id;x;y;x speed;y speed;length; ; ;FRAME TIME;NMEA TIME;NMEA SPEED\n\n")
		inputpath = self.fileForProcessing
		filerc = io.FileIO(inputpath)
		magic = filerc.read(4)
		filerc.close()
		self.graphlist = defaultdict(list)
		self.captureTimeList = defaultdict(list)
		delay = 0

		if magic == b'\x073"\x11':
			filerc = io.FileIO(inputpath)
			for ind in range(0, len(self.indexArray) - 2):
				##Открытие рс и чтение его через IO контейнер(начало и длина региона)
				frameLen = self.indexArray[ind + 1] - self.indexArray[ind]
				rcFrame = filerc.read(frameLen)
				startMarker = rcFrame.find(b'\xff\xd8')
				radarData = rcFrame[:startMarker]

				targetList, trackedTargetList, captureTime = UMRRMessages.getRawData(radarData, ind)
				self.captureTimeList[ind] = captureTime
				for target in targetList.keys():
					if (target >= hex(0x701)) and (target <= hex(0x7ff)):
						self.graphlist[ind] = self.appendLists(self.graphlist[ind], 6)

						self.graphlist[ind][0].append(target)
						self.graphlist[ind][1].append(targetList[target][2])
						self.graphlist[ind][2].append(targetList[target][3])
						self.graphlist[ind][3].append(targetList[target][4])
						self.graphlist[ind][4].append(targetList[target][0])
						self.graphlist[ind][5].append(targetList[target][1])

				file = open(os.path.basename(inputpath) + ".raw.csv", "a", newline='')
				trackedList = []
				trackedTrig = 0
				for tracked in trackedTargetList.keys():
					trackedRow = "{};{};{};{};{};{}".format(str(trackedTargetList[tracked][0]),
															  str(trackedTargetList[tracked][1]),
															  str(trackedTargetList[tracked][2]),
															  str(trackedTargetList[tracked][3]),
															  str(trackedTargetList[tracked][4]),
															  str(trackedTargetList[tracked][5]))
					trackedList.append(trackedRow)
				sensorStatus = ""
				tim = ""
				if "0x500" in list(targetList.keys()) and len(list(targetList.keys())) > 0:
					tim = targetList["0x500"][1]
					sensorStatus = targetList["0x500"][0]
				for ip in targetList.keys():
					if (ip >= hex(0x701)) and (ip <= hex(0x77f)):
						if len(trackedList) > trackedTrig:
							trackedInfo = trackedList[trackedTrig]
							trackedTrig += 1
						else:
							trackedInfo = " ; ; ; ; ; "
						self.csvText.append(
							"{};{};{};{};{};{};{};{};{}; ; ;{}; ; ;{}\n".format(ind, ip, str(targetList[ip][0]),
																				str(targetList[ip][1]),
																				str(targetList[ip][2]),
																				str(targetList[ip][3]),
																				str(targetList[ip][4]), sensorStatus,
																				tim, trackedInfo,
																				captureTime[0:captureTime.rfind(".")]))

				self.csvText.append("\n")
			if os.path.isfile(self.fileForProcessing + ".nmea"):
				self.addNmeaTimeToCSV()
			self.writeInCSV()
			self.drawGraph()

	def writeInCSV(self):
		file = open(os.path.basename(self.fileForProcessing) + ".raw.csv", "w", newline='')
		for line in self.csvText:
			file.write(line)
		file.close()

	def addNmeaTimeToCSV(self):
		rmc = self.parseNMEA(self.fileForProcessing + ".nmea")
		for timeNmea in rmc.keys():
			for frame in self.csvText:
				timeAndDate = frame.split(";")[-1]
				if len(timeAndDate.split(".")) != 2:
					continue
				frameT, frameMills = timeAndDate.split(".")
				rmcTimeWithoutMS = rmc[timeNmea][0].split(".")[0]

				if (rmcTimeWithoutMS == frameT):
					iter = 0
					for line in self.csvText:
						if timeAndDate in line:
							self.csvText[iter] = self.csvText[iter].rstrip() + ";{}.{};{}\n".format(rmc[timeNmea][0].split(".")[0], rmc[timeNmea][0].split(".")[1], rmc[timeNmea][6])
						iter += 1

	def start(self):
		self.fileForProcessing = self.filePathLine.text().replace("\\", "/")
		self.nameOfFileForProcessing = self.filePathLine.text().replace("\\", "/").rsplit(".", 1)[0]
		self.indexies(self.fileForProcessing)
		self.rawSearch()

def main():
	app = QtGui.QApplication(sys.argv)
	app.setWindowIcon(QtGui.QIcon('icon.png'))
	GUI = MainWindow()
	GUI.show()

	os._exit(app.exec_())

if __name__ == '__main__':
	main()