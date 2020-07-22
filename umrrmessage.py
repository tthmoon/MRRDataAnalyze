from collections import defaultdict
import struct
import datetime
import numpy as np

class UMRRMessages:

	@classmethod
	def getBitesR(cls, num, step, size):
		num = num >> np.uint64(step)
		num = num & np.uint64(int(size))
		return num

	@classmethod
	def getBitesL(cls, num, step, size):
		num = num << np.uint64(step)
		num = num & np.uint64(int(size))
		return num

	@classmethod
	def getRawData(cls, s, id):
		x = 0
		rawTargetsList = defaultdict(list)
		trackedTargetsList = defaultdict(list)

		while x < len(s) - 8:
			curId = int(struct.unpack('h', s[x:x + 2])[0])
			curlen = int(struct.unpack('i', s[x + 2:x + 6])[0])
			if curId == 0 and curlen == 2048:
				timeS = struct.unpack('i', s[x + 7:x + 11])[0]
				timeUS = struct.unpack('i', s[x + 11:x + 15])[0]
				if timeS <= 0 or len(str(timeUS)) == 10:
					x += 1
					continue
				hour = str(int(datetime.datetime.fromtimestamp(timeS).strftime('%H')) - 3).zfill(2)
				minuteAndSecond = datetime.datetime.fromtimestamp(timeS).strftime('%M%S')
				captureTime = "{}{}.{}.{}".format(hour, minuteAndSecond, timeUS,
												  datetime.datetime.fromtimestamp(timeS).strftime('%d%m%y'))
				x += 14
				continue
			if curId == 18 and curlen > 0:
				num_elem = int(round(curlen / (4096 * 4)))
				if num_elem == 0:
					num_elem = curlen
				rawdataInLine = s[x + 7:x + 7 + num_elem]
				x += 7 + num_elem
				forbList = ["0x7", "0x72", "0x74", "0x76"]
				i = 0
				while i < len(rawdataInLine) - 3:

					result = hex(struct.unpack('>h', rawdataInLine[i:i + 2])[0])
					num = struct.unpack('<b', rawdataInLine[i + 1:i + 2])[0]
					lenOf = struct.unpack('<b', rawdataInLine[i + 2:i + 3])[0]
					if (result >= hex(0x701)) and (result <= hex(0x77f)) and (result not in forbList) and (
							(lenOf == 8) or (lenOf == 6)):
						if num == 1:
							try:
								data = struct.unpack('>q', rawdataInLine[i - 8:i])[0]
							except:
								i += 1
								continue
							f_cycle_duration = np.uint64(data)
							f_cycle_duration = cls.getBitesR(f_cycle_duration, 0, 0xfff)
							f_cycle_duration = f_cycle_duration * 0.064
							f_number_of_objects = np.uint64(data)
							f_number_of_objects = cls.getBitesR(f_number_of_objects, 18, 0x1f)
							f_sensor_mode = np.uint64(data)
							f_sensor_mode = cls.getBitesR(f_sensor_mode, 18, 0xf)
						try:
							data = struct.unpack('>q', rawdataInLine[i + 3:i + 3 + lenOf])[0]
						except:
							i += 1
							continue
						angle = np.uint64(data)
						angle = cls.getBitesR(angle, 22, 0x3ff)
						angle = (angle - 511) * 0.16
						rangee = np.uint64(data)
						rangee = cls.getBitesR(rangee, 1, 0x1fff)
						rangee = (rangee - 0) * 0.08
						speed = np.uint64(data)
						speed = cls.getBitesR(speed, 39, 0xfff)
						speed = (speed - 2047) * 0.05 * 3.6

						# print("_____________________")
						# print(str(result) + " " + " " + str(num) + " " + str(i))
						# print("range " + str(rangee))
						# print("angle " + str(angle))
						# print("speed " + str(speed))
						try:
							dataPlus = struct.unpack('>q', rawdataInLine[i + 3 + lenOf:i + 3 + lenOf + lenOf])[0]
						except:
							i += 1
							continue
						level = np.uint64(dataPlus)
						level = cls.getBitesR(level, 9, 0xff)
						level = (level - 0) * 0.5
						type = np.uint64(dataPlus)
						type = cls.getBitesR(type, 32, 0x1f)
						# print("level " + str(level))
						# print("type " + str(type))
						# print("_____________________")
						rawTargetsList[result] = float(round(rangee, 2)), \
												 float(round(angle, 2)), \
												 float(round(speed, 2)), \
												 level, \
												 type
						i += lenOf + lenOf + 3
					# print("{} END OF INFO ABOUT TARGET NUMBER {}\n".format(i-1, num))
					else:
						if (lenOf == 8) and result >= hex(0x51) and result <= hex(0x5ff):
							try:
								data = struct.unpack('>q', rawdataInLine[i + 3:i + 3 + 8])[0]
							except:
								i += 1
								continue
							y_pos = np.uint64(data)
							y_pos = cls.getBitesR(y_pos, 32 - 4 - 14, 0x3fff)
							y_pos = (y_pos - 8192) * 64 / 1000

							y_speed = np.uint64(data)
							y_speed = cls.getBitesR(y_speed, 64 - 6 - 8 - 11, 0x7ff)
							y_speed = (y_speed - 1024) * 100 / 1000

							x_pos = np.uint64(data)
							x_pos = cls.getBitesR(x_pos, 0, 0x3fff)
							x_pos = (x_pos - 8192) * 64 / 1000

							x_speed1 = np.uint64(data)
							x_speed1 = cls.getBitesR(x_speed1, 32, 0x7f)

							x_speed2 = np.uint64(data)
							x_speed2 = cls.getBitesR(x_speed2, 64 - 4, 0xf)

							x_speed = x_speed1 << np.uint64(4)
							x_speed = x_speed | x_speed2
							x_speed = (x_speed - 1024) * 100 / 1000

							f_objid = np.uint64(data)
							f_objid = cls.getBitesR(f_objid, 64 - 6, 0x3f)

							f_len = np.uint64(data)
							f_len = cls.getBitesR(f_len, 64 - 6 - 8, 0xff)
							f_len = f_len * 0.2

							trackedTargetsList[result] = f_objid, float(round(x_pos, 3)), float(round(y_pos, 3)), float(
								round(x_speed, 3)), float(round(y_speed, 3)), f_len
							i += lenOf + 3
						else:
							if (lenOf == 8) and result == hex(0x500):

								try:
									data = struct.unpack('>q', rawdataInLine[i + 3:i + 3 + 8])[0]

								except:
									i += 1
									continue
								millis = struct.unpack('>l', rawdataInLine[i + 3:i + 3 + 4])[0]
								seconds = (millis / 1000) % 60
								seconds = int(seconds)
								minutes = (millis / (1000 * 60)) % 60
								minutes = int(minutes)
								hours = (millis / (1000 * 60 * 60)) % 24
								hours = round(hours)
								mil = str((millis / 1000) % 1).replace(".", "")[1:]
								t = "{}:{}:{}.{}".format(hours, minutes, seconds, mil)
								diagnostic = np.uint64(data)

								hh = cls.getBitesR(diagnostic, 64 - 8, 0xff)
								mm = cls.getBitesR(diagnostic, 64 - 16, 0xff)
								ss = cls.getBitesR(diagnostic, 64 - 24, 0xff)
								ms = cls.getBitesR(diagnostic, 64 - 32, 0xff)
								diagnostic = diagnostic & np.uint64(int(0xff))
								rawTargetsList[result] = bin(diagnostic), t
								i += lenOf + 3
							else:
								i += 1
			x += 1
		return rawTargetsList, trackedTargetsList, captureTime
