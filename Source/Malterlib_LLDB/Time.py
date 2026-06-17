# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from decimal import Decimal, ROUND_HALF_UP
from .Common import *
from .StringHelpers import *


gc_TimeFractionDividend = 9223372031757829470
gc_TimeInvalidSeconds = 0xffffffffffffffff
gc_TimeEndSeconds = 0xfffffffffffffffe
gc_TimeSpanInvalidSeconds = 0x7fffffffffffffff
gc_TimeSecondsInWeek = 604800
gc_TimeSecondsInMinute = 60
gc_TimeSecondsInHour = 3600
gc_TimeSecondsInDay = 86400
gc_TimeDaysInMedianYear = 365
gc_TimeDaysInLeapYear = 366
gc_TimeAverageSecondsInYear = 31556952
gc_TimeSecondsInLeapYear = gc_TimeSecondsInDay * gc_TimeDaysInLeapYear
gc_TimeYearZeroPlus1DaySeconds = 237148560000000000
gc_TimeYearOneBcSeconds = gc_TimeYearZeroPlus1DaySeconds - gc_TimeSecondsInDay
gc_TimeYearOneAdSeconds = gc_TimeYearOneBcSeconds + gc_TimeSecondsInDay * gc_TimeDaysInLeapYear
gc_TimeYearTwoAdSeconds = gc_TimeYearOneAdSeconds + gc_TimeSecondsInDay * gc_TimeDaysInMedianYear
gc_TimeYearOffset = 7514938800
gc_TimeYearOffsetSeconds = (gc_TimeYearOffset * gc_TimeAverageSecondsInYear) - gc_TimeYearZeroPlus1DaySeconds
gc_TimeMonthDayOfYear = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

def fg_GetDisplayValue(_Value, _ValueType):
	if _Value.GetType().IsReferenceType() or _ValueType.IsPointerType():
		return _Value.Dereference()
	return _Value

def fg_GetChildUnsigned(_Value, _Name):
	Child = _Value.GetChildMemberWithName(_Name)
	if not fg_IsValidSBValue(Child):
		return None
	Value = Child.GetValueAsUnsigned()
	if type(Value) is int:
		return Value
	return None

def fg_GetChildSigned(_Value, _Name):
	Child = _Value.GetChildMemberWithName(_Name)
	if not fg_IsValidSBValue(Child):
		return None
	Value = Child.GetValueAsSigned()
	if type(Value) is int:
		return Value
	return None

def fg_TimeIsLeapYear(_Year):
	return (_Year & 0x3) == 0 and ((_Year % 100) != 0 or (_Year % 400) == 0)

def fg_ExtractDateTimeAD(_Seconds):
	OriginalSeconds = _Seconds
	Year = _Seconds // gc_TimeAverageSecondsInYear
	Seconds = _Seconds

	for i in range(2):
		YearSub = Year
		if YearSub > 0:
			YearSub -= 1

		Seconds = OriginalSeconds
		Seconds -= Year * (gc_TimeDaysInMedianYear * gc_TimeSecondsInDay)
		Seconds -= (YearSub // 4) * gc_TimeSecondsInDay
		Seconds += (YearSub // 100) * gc_TimeSecondsInDay
		Seconds -= (YearSub // 400) * gc_TimeSecondsInDay

		if Seconds < 0:
			Year -= 1
		elif Seconds <= gc_TimeSecondsInLeapYear:
			break
		elif Seconds <= gc_TimeSecondsInLeapYear * 2:
			Year += 1
		else:
			Year -= 1

	bIsLeapYear = fg_TimeIsLeapYear(Year)
	if bIsLeapYear:
		if Seconds >= gc_TimeDaysInLeapYear * gc_TimeSecondsInDay:
			Year += 1
			Seconds -= gc_TimeDaysInLeapYear * gc_TimeSecondsInDay
			bIsLeapYear = False
	else:
		if Seconds >= gc_TimeDaysInMedianYear * gc_TimeSecondsInDay:
			Year += 1
			Seconds -= gc_TimeDaysInMedianYear * gc_TimeSecondsInDay
			bIsLeapYear = fg_TimeIsLeapYear(Year) if (Year & 3) == 0 else False

	DayOfYear = Seconds // gc_TimeSecondsInDay
	Seconds -= DayOfYear * gc_TimeSecondsInDay

	PassedLeapDay = 0
	DayOfYearMonth = DayOfYear
	if bIsLeapYear and DayOfYear >= 59:
		DayOfYearMonth -= 1
		PassedLeapDay = 1

	Month = 11
	for i in range(1, 12):
		if DayOfYearMonth < gc_TimeMonthDayOfYear[i]:
			Month = i - 1
			break
	Month += 1

	if PassedLeapDay and Month == 2:
		DayOfMonth = DayOfYearMonth - gc_TimeMonthDayOfYear[Month - 1] + 2
	else:
		DayOfMonth = DayOfYearMonth - gc_TimeMonthDayOfYear[Month - 1] + 1

	Hour = Seconds // gc_TimeSecondsInHour
	Seconds -= Hour * gc_TimeSecondsInHour
	Minute = Seconds // gc_TimeSecondsInMinute
	Seconds -= Minute * gc_TimeSecondsInMinute

	return (Year, Month, DayOfMonth, Hour, Minute, Seconds)

def fg_ExtractDateTime(_Seconds):
	if _Seconds <= gc_TimeYearTwoAdSeconds:
		DateTime = fg_ExtractDateTimeAD(_Seconds + gc_TimeYearOffsetSeconds)
		return (DateTime[0] - gc_TimeYearOffset,) + DateTime[1:]
	return fg_ExtractDateTimeAD(_Seconds - gc_TimeYearZeroPlus1DaySeconds)

def fg_FormatMilliseconds(_Fraction):
	Milliseconds = (_Fraction * 1000 + gc_TimeFractionDividend // 2) // gc_TimeFractionDividend
	if Milliseconds >= 1000:
		Milliseconds = 999
	return Milliseconds

def fg_TruncTowardZero(_Value, _Divisor):
	if _Value < 0:
		return -((-_Value) // _Divisor)
	return _Value // _Divisor

def fg_FormatFloatFixed(_Value, _MaxDecimals, _MinDecimals):
	Sign = ""
	if _Value.is_signed():
		Sign = "-"
		_Value = -_Value

	Quant = Decimal(1).scaleb(-_MaxDecimals)
	Rounded = _Value.quantize(Quant, rounding=ROUND_HALF_UP)
	Return = format(Rounded, "f")

	if _MaxDecimals > _MinDecimals:
		Return = Return.rstrip("0")
		if _MinDecimals == 0:
			Return = Return.rstrip(".")
		else:
			DotIndex = Return.find(".")
			nDecimals = 0 if DotIndex < 0 else len(Return) - DotIndex - 1
			if nDecimals < _MinDecimals:
				if DotIndex < 0:
					Return += "."
				Return += "0" * (_MinDecimals - nDecimals)

	if "." not in Return:
		if _MinDecimals > 0:
			Return += "." + "0" * _MinDecimals
	return Sign + Return

def fg_FormatFloatDefault(_Value):
	return fg_FormatFloatFixed(_Value, 15, 1)

def fg_FormatTime(_Value):
	Seconds = fg_GetChildUnsigned(_Value, "mp_Seconds")
	Fraction = fg_GetChildUnsigned(_Value, "mp_Fraction")
	if Seconds is None or Fraction is None:
		return None
	if Seconds == gc_TimeInvalidSeconds:
		return "Invalid"
	if Seconds == 0 and Fraction == 0:
		return "Start of time"
	if Seconds == gc_TimeEndSeconds and Fraction == gc_TimeFractionDividend - 1:
		return "End of time"

	(Year, Month, DayOfMonth, Hour, Minute, Second) = fg_ExtractDateTime(Seconds)
	return (
		str(Year)
		+ "-" + str(Month).rjust(2, "0")
		+ "-" + str(DayOfMonth).rjust(2, "0")
		+ " " + str(Hour).rjust(2, "0")
		+ ":" + str(Minute).rjust(2, "0")
		+ ":" + str(Second).rjust(2, "0")
		+ "." + str(fg_FormatMilliseconds(Fraction)).rjust(3, "0")
	)

def fg_FormatTimeSpan(_Value):
	Seconds = fg_GetChildSigned(_Value, "mp_Seconds")
	Fraction = fg_GetChildUnsigned(_Value, "mp_Fraction")
	if Seconds is None or Fraction is None:
		return None
	if Seconds == gc_TimeSpanInvalidSeconds:
		return "Invalid"

	AdjustedSeconds = Seconds
	if AdjustedSeconds < 0 and Fraction != 0:
		AdjustedSeconds += 1

	SpanFraction = Decimal(Fraction) / Decimal(gc_TimeFractionDividend)
	if Seconds < 0:
		SpanFraction = Decimal(gc_TimeFractionDividend - Fraction) / Decimal(gc_TimeFractionDividend)

	AbsSeconds = abs(AdjustedSeconds)
	Days = fg_TruncTowardZero(AdjustedSeconds, gc_TimeSecondsInDay)
	SecondsOfDay = AbsSeconds - (AbsSeconds // gc_TimeSecondsInDay) * gc_TimeSecondsInDay
	Hours = SecondsOfDay // gc_TimeSecondsInHour
	SecondsOfDay -= Hours * gc_TimeSecondsInHour
	Minutes = SecondsOfDay // gc_TimeSecondsInMinute
	SecondOfMinute = SecondsOfDay - Minutes * gc_TimeSecondsInMinute

	SecondsFraction = Decimal(Seconds) + Decimal(Fraction) / Decimal(gc_TimeFractionDividend)
	SecondText = fg_FormatFloatDefault(Decimal(SecondOfMinute) + SpanFraction)

	return (
		str(Days)
		+ " d " + str(Hours)
		+ " h " + str(Minutes)
		+ " m " + SecondText
		+ " s   " + fg_FormatFloatFixed(SecondsFraction / Decimal(gc_TimeSecondsInWeek), 3, 0) + "w"
		+ "  " + fg_FormatFloatFixed(SecondsFraction / Decimal(gc_TimeSecondsInDay), 3, 0) + "d"
		+ "  " + fg_FormatFloatFixed(SecondsFraction / Decimal(gc_TimeSecondsInHour), 3, 0) + "h"
		+ "  " + fg_FormatFloatFixed(SecondsFraction / Decimal(gc_TimeSecondsInMinute), 3, 0) + "m"
		+ "  " + fg_FormatFloatFixed(SecondsFraction, 3, 0) + "s"
	)

def fg_AddPointerPrefix(_Value, _ValueType, _Summary):
	if _Summary is None:
		return None
	if _ValueType.IsPointerType():
		return hex(_Value.GetValueAsUnsigned()) + "   " + _Summary
	return _Summary


def fg_SummaryProvider_CTime(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		return fg_AddPointerPrefix(_Value, ValueType, fg_FormatTime(fg_GetDisplayValue(_Value, ValueType)))
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CTime) error: ', error, ' path: ', _Value.get_expr_path())
		return


def fg_SummaryProvider_CTimeSpan(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		return fg_AddPointerPrefix(_Value, ValueType, fg_FormatTimeSpan(fg_GetDisplayValue(_Value, ValueType)))
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CTimeSpan) error: ', error, ' path: ', _Value.get_expr_path())
		return


def fg_MibLLDBInit_Time(_Debugger):

	fg_AddSummary(_Debugger, fg_SummaryProvider_CTime, "(^|^const )NMib::NTime::CTime$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CTimeSpan, "(^|^const )NMib::NTime::CTimeSpan$", True)

	return
