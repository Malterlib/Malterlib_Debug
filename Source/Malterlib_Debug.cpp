// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

namespace NMib
{
	void fg_MalterlibFatalError(const ch8 *_pMessage)
	{
		fg_GetSys()->f_FatalError(_pMessage);
	}

	void fg_MalterlibConOut(const NStr::CStrNonTracked &_Str)
	{
		NSys::fg_ConsoleOutput(_Str);
	}
	void fg_MalterlibConOut(NSys::EColor _Foreground, const NStr::CStrNonTracked &_Str)
	{
		NSys::fg_ConsoleOutput(_Foreground, _Str);
	}

	void fg_MalterlibConErrOut(const NStr::CStrNonTracked &_Str)
	{
		NSys::fg_ConsoleErrorOutput(_Str);
	}
	void fg_MalterlibConErrOut(NSys::EColor _Foreground, const NStr::CStrNonTracked &_Str)
	{
		NSys::fg_ConsoleErrorOutput(_Foreground, _Str);
	}

	namespace NMisc
	{
				
		CClassContainerList *fg_GetClassContainerListArgList(CClassContainerList &_List, CMibArgList &_Args)
		{
			void *CurrentPtr = DMibPArgListNextArg(_Args, void *);
			
			while(CurrentPtr)
			{
//#ifdef DDebug
				// TODO: Add dynamic cast fix
//				DSafeCheck(dynamic_cast<CClassContainer *>((CClassContainer *) CurrentPtr), "Not a class container");
//#endif
				_List.m_List.f_Insert((CClassContainer *) CurrentPtr);
				
				CurrentPtr = DMibPArgListNextArg(_Args, void *);			
			}	
			
			return &_List;
		}
		
		CClassContainerList *fg_GetClassContainerList(CClassContainerList *_pList, ...)
		{
			CMibArgList Args;
			DMibPArgListStart(Args, _pList);
			
			return fg_GetClassContainerListArgList(*_pList, Args);
		}
	}
}

