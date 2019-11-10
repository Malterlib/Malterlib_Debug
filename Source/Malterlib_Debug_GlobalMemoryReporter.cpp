// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Concurrency/ConcurrencyManager>
#include <Mib/Debug/RemoteDebugger>

#if DMibConfig_MemoryManager_Stats_Enable
#	include "../../Memory/Source/Malterlib_Memory_Reporter_Stats.hpp"
DMibCompilerMessage("---- Stats memory reporter enabled");
#endif

#if DMibConfig_MemoryManager_Stats_EnableCallstack
#	include "../../Memory/Source/Malterlib_Memory_Reporter_Callstack.hpp"
DMibCompilerMessage("---- Callstack memory reporter enabled");
#endif

#if DMibConfig_MemoryManager_Stats_EnableCategories
#	include "../../Memory/Source/Malterlib_Memory_Reporter_Categories.hpp"
DMibCompilerMessage("---- Categories memory reporter enabled");
#endif

namespace NMib
{
#if (DMibConfig_MemoryManager_Stats_Enable + DMibConfig_MemoryManager_Stats_EnableCallstack + DMibConfig_MemoryManager_Stats_EnableCategories) > 1
#error "Can only use one memory reporter at a time"
#endif
#if DMibConfig_MemoryManager_Stats_Enable
	constinit NMib::NStorage::TCAggregateSimple<NMemory::CStatsMemoryReporter> g_MainReporter = {DAggregateInit};
#elif DMibConfig_MemoryManager_Stats_EnableCallstack
	constinit NMib::NStorage::TCAggregateSimple<NMemory::CCallstackMemoryReporter> g_MainReporter = {DAggregateInit};
#elif DMibConfig_MemoryManager_Stats_EnableCategories
	constinit NMib::NStorage::TCAggregateSimple<NMemory::CCategoriesMemoryReporter> g_MainReporter = {DAggregateInit};
#endif

#if DMibConfig_Memory_Shims_EnableGlobal
	void CSystem::fp_CreateGlobalMemoryReporter()
	{
#if DMibConfig_MemoryManager_Stats_Enable || DMibConfig_MemoryManager_Stats_EnableCallstack || DMibConfig_MemoryManager_Stats_EnableCategories
		g_MainReporter.f_Construct();
#endif
	}
	void CSystem::fp_DestroyGlobalMemoryReporter()
	{
#if DMibConfig_MemoryManager_Stats_Enable || DMibConfig_MemoryManager_Stats_EnableCallstack || DMibConfig_MemoryManager_Stats_EnableCategories
		g_MainReporter.f_Destruct();
#endif
	}
#endif

} // Namespace NMib
