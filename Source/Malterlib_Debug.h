// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#pragma once

#include <Mib/Core/Core>
#include "../../Core/Source/Malterlib_Core_PlatformInterface.h"

namespace NMib
{
	void fg_MalterlibFatalError(const ch8 *_pMessage);
	void fg_MalterlibConOut(const NStr::CStrNonTracked &_Str);
	void fg_MalterlibConOut(NSys::EColor _Foreground,const NStr::CStrNonTracked &_Str);
	void fg_MalterlibConErrOut(const NStr::CStrNonTracked &_Str);
	void fg_MalterlibConErrOut(NSys::EColor _Foreground,const NStr::CStrNonTracked &_Str);

	namespace NDebug
	{
		
		// If dtrace enable has not been specifically set, enable it incase we are in debug mode
#		ifndef DMibEnableDTrace
#			ifdef DMibDebug
#				define DMibEnableDTrace 1
#			else
#				define DMibEnableDTrace 0
#			endif
#		endif
				
#		if DMibEnableDTrace > 0
#			define DMibDTrace(_Format, _Args)  NMib::NSys::fg_DebugOutput(NMib::NStr::fg_GetStringFormat(_Format) << _Args)
#			define DMibDTraceRaw(_Args) NMib::NSys::fg_DebugOutput(_Args)
#			define DMibDTraceSafe(_Format, _Args) NMib::NSys::fg_DebugOutput((NMib::NStr::CFStr512::CFormat(_Format) << _Args).f_GetStr().f_GetStr())
#			define DMibDTraceTimed(_Format, _Args)  NMib::NSys::fg_DebugOutput(NMib::NStr::fg_GetStringFormat("{}: " _Format) << NMib::NTime::CTime::fs_NowLocal() << _Args)

#			define DMibDTrace2(...)  NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__))
#			define DMibDTraceSafe2(...) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CFStr512>(__VA_ARGS__).f_GetStr())
#			define DMibDTraceTimed2(d_Format, ...)  NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>("{}" d_Format, NMib::NTime::CTime::fs_NowLocal(), __VA_ARGS__))
#		else
#			define DMibDTraceRaw(_Args) (void)0
#			define DMibDTrace(_Format, _Args) (void)0
#			define DMibDTraceSafe(_Format, _Args) (void)0
#			define DMibDTraceTimed(_Format, _Args) (void)0
#		endif
				
#		ifndef DMibPNoShortCuts
#			define DDTrace DMibDTrace
#			define DDTraceRaw DMibDTraceRaw
#			define DDTraceSafe DMibDTraceSafe
#			define DDTraceTimed DMibDTraceTimed
#		endif


		// If trace enable has not been specifically set, enable it
#		ifndef DMibEnableTrace
#			ifdef DConfig_Release
#				define DMibEnableTrace 0
#			else
#				define DMibEnableTrace 1
#			endif
#		endif

#		if DMibEnableTrace > 0
#			define DMibTrace(_Format, _Args) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_GetStringFormat(_Format) << _Args)
#			define DMibTraceRaw(_Args) NMib::NSys::fg_DebugOutput(_Args)
#			define DMibTraceSafe(_Format, _Args) NMib::NSys::fg_DebugOutput((NMib::NStr::CFStr512::CFormat(_Format) << _Args).f_GetStr().f_GetStr())
#			define DMibTraceTimed(_Format, _Args) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_GetStringFormat("{}: " _Format) << NMib::NTime::CTime::fs_NowLocal() << _Args)

#			define DMibTrace2(...) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__))
#			define DMibTraceSafe2(...) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CFStr512>(__VA_ARGS__).f_GetStr())
#			define DMibTraceTimed2(d_Format, ...) NMib::NSys::fg_DebugOutput(NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>("{}: " d_Format, NMib::NTime::CTime::fs_NowLocal(), __VA_ARGS__))
#		else
#			define DMibTrace(_Format, _Args) (void)0
#			define DMibTraceRaw(_Args) (void)0
#			define DMibTraceSafe(_Format, _Args) (void)0
#			define DMibTraceTimed(_Format, _Args) (void)0

#			define DMibTrace2(_Format, _Args) (void)0
#			define DMibTraceSafe2(_Format, _Args) (void)0
#			define DMibTraceTimed2(_Format, _Args) (void)0
#		endif
				
#		ifndef DMibPNoShortCuts
#			define DTrace DMibTrace
#			define DTraceRaw DMibTraceRaw
#			define DTraceSafe DMibTraceSafe
#			define DTraceTimed DMibTraceTimed
		
#			define DTrace2 DMibTrace2
#			define DTraceSafe2 DMibTraceSafe2
#			define DTraceTimed2 DMibTraceTimed2
#		endif

#		ifndef DMibEnableConsole
#			define DMibEnableConsole 1
#		endif

#		if DMibEnableConsole > 0
#			define DMibConOutRaw NMib::fg_MalterlibConOut
#			define DMibConOut(_Format, _Args) NMib::fg_MalterlibConOut((NMib::NStr::fg_GetStringFormat(_Format) << _Args).f_GetStr())
#			define DMibColorConOut(_Color, _Format, _Args) NMib::fg_MalterlibConOut(_Color, (NMib::NStr::fg_GetStringFormat(_Format) << _Args).f_GetStr())
#			define DMibConErrOut(_Format, _Args) NMib::fg_MalterlibConErrOut((NMib::NStr::fg_GetStringFormat(_Format) << _Args).f_GetStr())
#			define DMibConErrOutRaw NMib::fg_MalterlibConErrOut
#			define DMibColorConErrOut(_Color, _Format, _Args) NMib::fg_MalterlibConErrOut(_Color, (NMib::NStr::fg_GetStringFormat(_Format) << _Args).f_GetStr())

#			define DMibConOut2(...) NMib::fg_MalterlibConOut((NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__)).f_GetStr())
#			define DMibColorConOut2(_Color, ...) NMib::fg_MalterlibConOut(_Color, (NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__)).f_GetStr())
#			define DMibConErrOut2(...) NMib::fg_MalterlibConErrOut((NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__)).f_GetStr())
#			define DMibColorConErrOut2(_Color, ...) NMib::fg_MalterlibConErrOut(_Color, (NMib::NStr::fg_Format<NMib::NStr::CStrNonTracked>(__VA_ARGS__)).f_GetStr())
#		else
#			define DMibConOutRaw 1 ? (void)0 : NMib::fg_MalterlibConOut
#			define DMibConErrOutRaw 1 ? (void)0 : NMib::fg_MalterlibConErrOut
#			define DMibConOut(_Format, _Args) (void)0
#			define DMibColorConOut(_Color, _Format, _Args) (void)0
#			define DMibConErrOut(_Format, _Args) (void)0
#			define DMibColorConErrOut(_Color, _Format, _Args) (void)0
#		endif
				
#		ifndef DMibPNoShortCuts
#			define DConOut DMibConOut
#			define DColorConOut DMibConOut
#			define DConOutRaw DMibConOutRaw
#			define DConErrOut DMibConErrOut
#			define DColorConErrOut DMibConErrOut
#			define DConErrOutRaw DMibConErrOutRaw

#			define DConOut2 DMibConOut2
#			define DColorConOut2 DMibConOut2
#			define DConErrOut2 DMibConErrOut2
#			define DColorConErrOut2 DMibConErrOut2
#		endif

	}

	/***************************************************************************************************\
	|¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯|
	| Tests																						|
	|___________________________________________________________________________________________________|
	\***************************************************************************************************/

#ifndef DMibConfig_Tests_Enable
#	if defined(DMibDebug) || defined(DConfig_ReleaseTesting)
#		define DMibConfig_Tests_Enable 1
	DMibCompilerMessage("-- Tests automatically enabled")
#	else
#		define DMibConfig_Tests_Enable 0
	DMibCompilerMessage("-- Tests automatically disabled")
#	endif
#else
#	if DMibConfig_Tests_Enable
	DMibCompilerMessage("-- Tests forcefully enabled")
#	else
	DMibCompilerMessage("-- Tests forcefully disabled")
#	endif
#endif

	/***************************************************************************************************\
	|¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯|
	| Contracts																							|
	|___________________________________________________________________________________________________|
	\***************************************************************************************************/

#ifndef DMibConfig_Contracts_Enable
#	if defined(DMibDebug) || defined(DConfig_ReleaseTesting) || (DMibConfig_Tests_Enable && !defined(DConfig_Release) && !defined(DConfig_Optimized) && !defined(DConfig_Profile))
#		define DMibContractConfigure_AllEnabled
		DMibCompilerMessage("-- Contracts automatically enabled")
#	else
#		define DMibContractConfigure_DontExpectAny
		DMibCompilerMessage("-- Contracts automatically disabled")
#	endif
#else
#	if DMibConfig_Contracts_Enable
#		define DMibContractConfigure_AllEnabled
	DMibCompilerMessage("-- Contracts forcefully enabled")
#	else
#		define DMibContractConfigure_DontExpectAny
#		undef DMibContractConfigure_AllEnabled
#		undef DMibContractConfigure_RequireEnabled
#		undef DMibContractConfigure_EnsureEnabled
#		undef DMibContractConfigure_InvariantEnabled
#		undef DMibContractConfigure_CheckEnabled
#		undef DMibContractConfigure_NeverGetHereEnabled
		DMibCompilerMessage("-- Contracts forcefully disabled")
#	endif
#endif



#ifdef DMibContractConfigure_AllEnabled
# define DMibContractConfigure_RequireEnabled
# define DMibContractConfigure_EnsureEnabled
# define DMibContractConfigure_InvariantEnabled
# define DMibContractConfigure_CheckEnabled
# define DMibContractConfigure_NeverGetHereEnabled
#endif

#ifdef DMibContractConfigure_InvariantEnabled_Strong
# define DMibContractConfigure_InvariantEnabled
#endif

#if defined DMibContractConfigure_RequireEnabled || defined DMibContractConfigure_EnsureEnabled || defined DMibContractConfigure_CheckEnabled || defined DMibContractConfigure_InvariantEnabled || defined DMibContractConfigure_NeverGetHereEnabled
#define DMibContract_AnyEnabled
#endif

#ifndef DMibContractConfigure_AllEnabled 
#	ifdef DMibContract_AnyEnabled
		DMibCompilerMessage("-- Contracts enabled")
#	else
#		ifndef DMibContractConfigure_DontExpectAny
			DMibCompilerMessage("-- Contracts disabled")
#		endif
#	endif
#endif
#undef DMibContractConfigure_DontExpectAny

	/***************************************************************************************************\
	|¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯|
	| Memory debugging																					|
	|___________________________________________________________________________________________________|
	\***************************************************************************************************/


#ifndef DMibConfig_Memory_Shims_Enable
#	if DMibConfig_Tests_Enable || defined(DMibDebug)
#		define DMibConfig_Memory_Shims_Enable 1
		DMibCompilerMessage("-- Memory shims automatically enabled")
#	else
#		define DMibConfig_Memory_Shims_Enable 0
		DMibCompilerMessage("-- Memory shims automatically disabled")
#	endif
#else
#	if DMibConfig_Memory_Shims_Enable
		DMibCompilerMessage("-- Memory shims forcefully enabled")
#	else
		DMibCompilerMessage("-- Memory shims forcefully disabled")
#	endif
#endif
	
}

