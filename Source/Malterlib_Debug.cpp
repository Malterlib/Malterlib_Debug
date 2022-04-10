// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/CommandLine/AnsiEncoding>

namespace NMib
{
	void fg_MalterlibFatalError(const ch8 *_pMessage)
	{
		fg_GetSys()->f_FatalError(_pMessage);
	}

	NStr::CStr fg_DebugColor(NStr::CStr const &_Data)
	{
		NCommandLine::CAnsiEncoding AnsiEncoding(NCommandLine::EAnsiEncodingFlag_Color | NCommandLine::EAnsiEncodingFlag_Color24Bit);

		return AnsiEncoding.f_ColorSemiUnique(_Data);
	}
}
