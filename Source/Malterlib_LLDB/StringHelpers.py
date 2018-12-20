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
	Ret = ''
	try:
		StringArray = _Value.uint8
		Length = min(len(_Value.uint8), _Length)
		if _Type == 1:
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + unichr(Char)
		else:
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)

		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret.decode('cp1252').encode('utf-8') + '" a8'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret.encode('utf-8') + '" u8'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret.decode('utf-8').encode('utf-8') + '"'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return 'a8(invalid)   "' + Ret + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u8(invalid)   "' + Ret + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf8(invalid)   "' + Ret + '"'
		

	return "Internal error"

def fg_MakeStringFromData_ch8_Raw(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'
		
	if _Length > 4096:
		_Length = 4096
	Ret = ''
	try:
		StringArray = _Value.uint8
		Length = min(len(_Value.uint8), _Length)
		if _Type == 1:
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + unichr(Char)
		else:
			for iStr in range(Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + chr(Char)

		if _Type == 0:		# EStrType_Ansi
			return Ret.decode('cp1252').encode('utf-8')
		elif _Type == 1:	# EStrType_Unicode
			return Ret.encode('utf-8')
		elif _Type == 2:	# EStrType_UTF
			return Ret.decode('utf-8').encode('utf-8')
	except Exception as error:
		return Ret

	return "Internal error"


def fg_MakeStringFromData_ch16(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	Ret = ''
	try:
		StringArray = _Value.uint16
		if _Type == 1:
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + (r'\U' + format(Char, '08x')).decode('unicode-escape')
		else:
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + unichr(Char)

	#>>> c = (r'\U' + '000ee816').decode('unicode-escape')
	#>>> c
		#u'\U000ee816'
		
		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret.decode('utf-16').encode('utf-8') + '" ansi(INVALID for ch16)'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret.encode('utf-8') + '" u16'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret.encode('utf-8') + '" utf16'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret + '" ansi(invalid)'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret + '" u16(invalid)'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret + '" utf16(invalid)'

	return "Internal error"

def fg_MakeStringFromData_ch16_Raw(_Value, _Length, _Type):

	if _Type == 3:
		return 'Invalid'
	elif _Type > 3:
		return 'Corrupt'

	if _Length > 4096:
		_Length = 4096

	try:
		Ret = ''
		StringArray = _Value.uint16
		if _Type == 1:
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + (r'\U' + format(Char, '08x')).decode('unicode-escape')
		else:
			for iStr in range(_Length):
				Char = StringArray[iStr]
				if Char == 0:
					break
				Ret = Ret + unichr(Char)

	#>>> c = (r'\U' + '000ee816').decode('unicode-escape')
	#>>> c
		#u'\U000ee816'
		
		if _Type == 0:		# EStrType_Ansi
			return Ret.decode('utf-16').encode('utf-8')
		elif _Type == 1:	# EStrType_Unicode
			return Ret.encode('utf-8')
		elif _Type == 2:	# EStrType_UTF
			return Ret.encode('utf-8')
	except Exception as error:
		return Ret

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
			Ret = Ret + (r'\U' + format(Char, '08x')).decode('unicode-escape')

		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret.encode('utf-8') + '" ansi(INVALID for ch32)'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret.encode('utf-8') + '" u32'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret.encode('utf-8') + '" utf32'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return '"' + Ret + '" ansi(invalid)'
		elif _Type == 1:	# EStrType_Unicode
			return '"' + Ret + '" u32(invalid)'
		elif _Type == 2:	# EStrType_UTF
			return '"' + Ret + '" utf32(invalid)'

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
			Ret = Ret + (r'\U' + format(Char, '08x')).decode('unicode-escape')

		if _Type == 0:		# EStrType_Ansi
			return Ret.encode('utf-8')
		elif _Type == 1:	# EStrType_Unicode
			return Ret.encode('utf-8')
		elif _Type == 2:	# EStrType_UTF
			return Ret.encode('utf-8')
	except Exception as error:
		return Ret

	return "Internal error"

def fg_MibLLDBInit_StringHelpers(_Debugger):
	return
