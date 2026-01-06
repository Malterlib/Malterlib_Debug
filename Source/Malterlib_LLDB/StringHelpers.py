# Copyright (C) 2015 Hansoft AB
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys

def fg_MakeStringFromData_ch8(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096
	try:
		StringArray = _Value.uint8
		Length = min(len(_Value.uint8), _Length)
		if _Type == 1:
			Ret = ''
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)
			return '"' + Ret + '" u8'
		else:
			Ret = b''
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + bytes([Char])

		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret.decode('cp1252') + '" a8'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret.decode('utf-8') + '"'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return 'a8(invalid)   "' + str(Ret) + '" ' + str(error)
		elif _Type == 1:	# EStrType_Unicode
			return 'u8(invalid)   "' + str(Ret) + '" ' + str(error)
		elif _Type == 2:	# EStrType_UTF
			return 'utf8(invalid)   "' + str(Ret) + '" ' + str(error)


	return "Internal error"

def fg_MakeStringFromData_ch8_Raw(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096
	try:
		StringArray = _Value.uint8
		Length = min(len(_Value.uint8), _Length)
		if _Type == 1:
			Ret = ''
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)
			return Ret
		else:
			Ret = b''
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + bytes([Char])

		if _Type == 0:		# EStrType_Ansi
			return Ret.decode('cp1252')
		elif _Type == 2:	# EStrType_UTF
			return Ret.decode('utf-8')
	except Exception as error:
		return str(Ret) + ' ' + str(error)

	return "Internal error"


def fg_MakeStringFromData_ch16(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	try:
		StringArray = _Value.uint16
		if _Type == 1:
			Ret = ''
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)
			return '"' + Ret + '" u16'
		else:
			Ret = b''
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + bytes([Char & 0xff, Char >> 8])

		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret.decode('utf-16') + '" ansi(INVALID for ch16)'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret.decode('utf-16') + '" utf16'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return '"' + str(Ret) + '" ansi(invalid) ' + str(error)
		elif _Type == 1:	# EStrType_Unicode
			return '"' + str(Ret) + '" u16(invalid) ' + str(error)
		elif _Type == 2:	# EStrType_UTF
			return '"' + str(Ret) + '" utf16(invalid) ' + str(error)

	return "Internal error"

def fg_MakeStringFromData_ch16_Raw(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	try:
		StringArray = _Value.uint16
		if _Type == 1:
			Ret = ''
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)
			return Ret
		else:
			Ret = b''
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + bytes([Char & 0xff, Char >> 8])

		if _Type == 0:		# EStrType_Ansi
			return Ret.decode('utf-16')
		elif _Type == 2:	# EStrType_UTF
			return Ret.decode('utf-16')
	except Exception as error:
		return str(Ret) + ' ' + str(error)

	return "Internal error"

def fg_MakeStringFromData_ch32(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	try:
		Ret = ''
		StringArray = _Value.uint32
		for iStr in range(_Length):
			Char = StringArray[iStr]
			if Char == 0:
				break
			Ret = Ret + chr(Char)

		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret + '" ansi(INVALID for ch32)'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret + '" u32'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret + '" utf32'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return '"' + str(Ret) + '" ansi(invalid) ' + str(error)
		elif _Type == 1:	# EStrType_Unicode
			return '"' + str(Ret) + '" u32(invalid) ' + str(error)
		elif _Type == 2:	# EStrType_UTF
			return '"' + str(Ret) + '" utf32(invalid) ' + str(error)

	return "Internal error"

def fg_MakeStringFromData_ch32_Raw(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	try:
		Ret = ''
		StringArray = _Value.uint32
		for iStr in range(_Length):
			Char = StringArray[iStr]
			if Char == 0:
				break
			Ret = Ret + chr(Char)

		if _Type == 0:		# EStrType_Ansi
			return Ret
		elif _Type == 1:	# EStrType_Unicode
			return Ret
		elif _Type == 2:	# EStrType_UTF
			return Ret
	except Exception as error:
		return str(Ret) + ' ' + str(error)

	return "Internal error"

def fg_MibLLDBInit_StringHelpers(_Debugger):
	return
