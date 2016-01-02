# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb

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
			return 'a8   "' + Ret.decode('cp1252').encode('utf-8') + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u8   "' + Ret.encode('utf-8') + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf8   "' + Ret.decode('utf-8').encode('utf-8') + '"'
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
			return 'ansi(INVALID for ch16)   "' + Ret.decode('utf-16').encode('utf-8') + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u16   "' + Ret.encode('utf-8') + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf16   "' + Ret.encode('utf-8') + '"'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return 'ansi(invalid)   "' + Ret + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u16(invalid)   "' + Ret + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf16(invalid)   "' + Ret + '"'

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
			return 'ansi(INVALID for ch32)   "' + Ret.encode('utf-8') + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u32   "' + Ret.encode('utf-8') + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf32   "' + Ret.encode('utf-8') + '"'
	except Exception as error:
		if _Type == 0:		# EStrType_Ansi
			return 'ansi(invalid)   "' + Ret + '"'
		elif _Type == 1:	# EStrType_Unicode
			return 'u32(invalid)   "' + Ret + '"'
		elif _Type == 2:	# EStrType_UTF
			return 'utf32(invalid)   "' + Ret + '"'

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
