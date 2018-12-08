// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

namespace NMib
{
	void fg_MalterlibFatalError(const ch8 *_pMessage)
	{
		fg_GetSys()->f_FatalError(_pMessage);
	}
}
