# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
import threading

g_MaxSynthChildren = 1024
g_bRawSummary = threading.local()

g_ModuleName = ""

def fg_SetModuleName(_Name):
	global g_ModuleName
	g_ModuleName = _Name


def fg_AddSummary(_Debugger, _Function, _Type, _Regex = False, _Priority = 0):
	global g_ModuleName
	if _Regex:
		if _Priority == 0:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
	else:
		if _Priority == 0:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))

def fg_AddSynth(_Debugger, _Class, _Type, _Regex = False, _Priority = 0):
	global g_ModuleName
	if _Regex:
		if _Priority == 0:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
	else:
		if _Priority == 0:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))

def fg_RawSummary():
	global g_bRawSummary
	bRawSummary = getattr(g_bRawSummary, 'm_bRawSummary', None)
	if bRawSummary == None:
		return False
	return bRawSummary

def fg_SetRawSummary(_bRaw):
	bOld = fg_RawSummary()
	g_bRawSummary.m_bRawSummary = _bRaw
	return bOld


def fg_GetValueAddress(_Value):
	Type = _Value.GetType()
	if Type.IsReferenceType() or Type.IsPointerType():
		return _Value.GetValueAsUnsigned()
	return _Value.AddressOf().GetValueAsUnsigned()

def fg_GetPointerAddress(_Value):
	Type = _Value.GetType()
	if Type.IsReferenceType():
		return _Value.GetChildAtIndex(0).GetValueAsUnsigned()
	return _Value.GetValueAsUnsigned()

def fg_PrecacheType(_Type):
	# This seems to workaround bugs in llvm that prevents the type from working properly
	str(_Type)
	return


def fg_GetInheritedType(_Type, _TypeName):
	Type = _Type.GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	while Type != None and Type.IsValid() and not Type.GetName().startswith(_TypeName):
		Type = Type.GetDirectBaseClassAtIndex(0).GetType().GetUnqualifiedType()
	return Type

def fg_GetValueType(_Value):
	Type = _Value.GetType().GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	return Type

def fg_GetPointerValueType(_Value):
	Type = _Value.GetType().GetPointeeType().GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	return Type



def fg_GetStaticFromSBValueGlobals(_Value, _Name, _Type, _NameForType):
	# This fails if _Value is a synthetic value
	if _NameForType == None:
		_NameForType = _Name

	FullName = _Type.GetName() + "::" + _NameForType

	# This fails if the static is not in the compilation unit
	ObjectFrame = _Value.GetFrame()
	GlobalVars = ObjectFrame.GetVariables(False, False, True, False);
	for iVar in GlobalVars:
		if iVar.GetType().GetName() == FullName:
			return iVar

	# This fail because not all statics in the target are returned
	ObjectTarget = _Value.GetTarget()
	GlobalVars = ObjectTarget.FindGlobalVariables(_NameForType, 1024);
	for iVar in GlobalVars:
		if iVar.GetType().GetName() == FullName:
			return iVar

	return None

def fg_IsValidSBValue(_Value):
	if _Value != None and _Value.IsValid() and _Value.GetError().Success():
		return True
	return False

def fg_GetStaticFromSBValue(_Value, _Name, _Type, _NameForType = None, _bTrace = False):
	# This fails if _Value is a synthetic value
	if _NameForType == None:
		_NameForType = _Name

	Accessor = '.'
	if _Value.GetType().IsPointerType():
		Accessor = '->'

	ExpressionPath = _Value.get_expr_path()
	bIsTemplate = ExpressionPath.find('<') >= 0
		
	if not bIsTemplate:
		ExpressionPath = "(" + ExpressionPath + ")"
		if _bTrace == True:
			print 'expr: ', ExpressionPath + Accessor + _Name
		Variable = _Value.CreateValueFromExpression("[TempData]", ExpressionPath + Accessor + _Name)
		if fg_IsValidSBValue(Variable):
			if _bTrace == True:
				print 'Return by expr\n'
			return Variable
		if _bTrace == True:
			print 'Variable: ', Variable

		if _Type.IsPointerType():
			if _bTrace == True:
				print 'Return None for pointer type\n'
			return None

	# This fails if the type is a template type
	if not bIsTemplate:
		if _bTrace == True:
			print 'type expr: ', _Type.GetName() + "::" + _NameForType
		Variable = _Value.CreateValueFromExpression("[TempData]", _Type.GetName() + "::" + _NameForType)
		if fg_IsValidSBValue(Variable):
			if _bTrace == True:
				print 'Return by static expr: ', Variable, '\n'
			return Variable

	FullName = _Type.GetName() + "::" + _NameForType
	if _bTrace == True:
		print 'FullName: ', FullName

	# This fails if the static is not in the compilation unit
	ObjectFrame = _Value.GetFrame()
	GlobalVars = ObjectFrame.GetVariables(False, False, True, False);
	#print 'FrameVars: ', GlobalVars
	for iVar in GlobalVars:
		if iVar.GetName() == FullName:
			if _bTrace == True:
				print 'RETURN FrameVar: ', iVar.GetName(), '\n'
			return iVar
		if _bTrace == True:
			print 'FrameVar: ', iVar.GetName()

	# This fails if the static is not in the compilation unit
	ObjectFrame = _Value.GetTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
	GlobalVars = ObjectFrame.GetVariables(False, False, True, False);
	#print 'FrameVars: ', GlobalVars
	for iVar in GlobalVars:
		if iVar.GetName() == FullName:
			if _bTrace == True:
				print 'RETURN FrameVar: ', iVar.GetName(), '\n'
			return iVar
		if _bTrace == True:
			print 'FrameVar: ', iVar.GetName()


	# This fail because not all statics in the target are returned
	ObjectTarget = _Value.GetTarget()
	GlobalVars = ObjectTarget.FindGlobalVariables(_NameForType, 1024);
	#print 'GlobalVars: ', GlobalVars
	for iVar in GlobalVars:
		if iVar.GetName() == FullName:
			if _bTrace == True:
				print 'RETURN GlobalVar: ', iVar.GetName(), '\n'
			return iVar
		if _bTrace == True:
			print 'GlobalVar: ', iVar.GetName()
	if _bTrace == True:
		print 'Return None at end\n'
	return None


def fg_SummaryProvider_Container(_Value, dict):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return None # Pointer to pointer we don't want to provide summary for
		
		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
			return None
		Value = str(Len.GetValueAsUnsigned()) + ' elements'
		if Type.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		print '(fg_SummaryProvider_Container) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_ContainerLimited(_Value, dict):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return None # Pointer to pointer we don't want to provide summary for
		
		global g_MaxSynthChildren
		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
			return None
		LenValue = Len.GetValueAsUnsigned()
		if LenValue >= g_MaxSynthChildren:
			Value = 'At least ' + str(LenValue) + ' elements'
		else:
			Value = str(LenValue) + ' elements'

		if Type.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value

	except Exception as error:
		print '(fg_SummaryProvider_ContainerLimited) error: ', error, ' path: ', _Value.get_expr_path()
		return


def fg_ChildPath(_Value, _Path):
	if _Value.GetType().IsPointerType():
		return _Value.GetValueForExpressionPath("->" + _Path)
	else:
		return _Value.GetValueForExpressionPath("." + _Path)

def fg_SummaryProvider_IteratorCommon(_Value, dict):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return None # Pointer to pointer we don't want to provide summary for
		
		Current = _Value.GetChildMemberWithName('[Current]')
		if not fg_IsValidSBValue(Current):
			Current = _Value.GetChildMemberWithName('[Invalid]')
			if fg_IsValidSBValue(Current):
				Value = "Invalid or uninitialized"
			else:
				return None
		else:
			if Current.GetType().IsPointerType():
				PointerValue = Current.GetValueAsUnsigned()
				if PointerValue == 0:
					Value = "nullptr";
				else:
					CurrentDeref = Current.Dereference();
					Summary = CurrentDeref.GetSummary()
					if Summary != None:
						Value = hex(PointerValue) + "   " + Summary
					else:
						Value = CurrentDeref.GetValue()
						if Value != None:
							Value = hex(PointerValue) + "   " + str(Value)
			else:
				Summary = Current.GetSummary()
				if Summary != None:
					Value = Summary
				else:
					Value = Current.GetValue()
					if Value != None:
						Value = str(Value)
					
		if Value != None:
			if Type.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Value
			return Value

		return None
	except Exception as error:
		print 'common summary error: ', error
		return None


class CSynthProvider_Common:
	def __init__(self, _ValueObject, _Dictionary):
		self.m_ValueObject = _ValueObject
		self.m_ValueObjectType = _ValueObject.GetType()
		
		if self.m_ValueObjectType.IsPointerType():
			self.m_ValueObjectDeref = _ValueObject.Dereference()
		else:
			self.m_ValueObjectDeref = _ValueObject
		self.m_Count = None
		self.m_bValid = False
		self.m_OriginalNameMap = None

	def update(self):
		self.m_Count = None
		self.m_bValid = False
		try:
			self.m_nOriginalChildren = self.m_ValueObject.GetNumChildren()
			self.m_OriginalNameMap = {};
			
			for iOriginalChild in range(0, self.m_nOriginalChildren):
				Child = self.m_ValueObject.GetChildAtIndex(iOriginalChild)
				if not Child.IsValid():
					self.m_nOriginalChildren = self.m_nOriginalChildren - 1
					continue
				self.m_OriginalNameMap[Child.GetName()] = iOriginalChild
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def has_children(self):
		return True
				
	def num_children(self):
		try:
			if self.m_Count == None:
				if not self.m_bValid:
					self.m_Count = 0
				else:
					try:
						self.m_Count = self.fp_NumChildren()
					except Exception as error:
						print '(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
						self.m_Count = 0
			
			return int(self.m_Count + self.m_nOriginalChildren)
		except Exception as error:
			print '(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return 0

	def get_child_index(self, _Name):
		try:
			if self.m_OriginalNameMap == None:
				return -1
			OriginalIndex = self.m_OriginalNameMap.get(_Name)
			if OriginalIndex != None:
				if self.m_Count == None:
					self.num_children()
				return int(self.m_Count + OriginalIndex)
			if self.m_bValid:
				Return = self.fp_GetChildIndex(_Name)
				if Return != None:
					return int(Return)
			return -1
		except Exception as error:
			print '(' + self.__class__.__name__ + ') get_child_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return -1

	def fp_GetChildIndex(self, _Name):
		Stripped = _Name.lstrip('[').rstrip(']')
		if Stripped.isdigit():
			return int(Stripped)
		return -1

	def get_child_at_index(self, _iChild):
		try:
			nChildren = self.num_children()
			if nChildren < 0:
				return None
			if _iChild >= nChildren:
				return None
			if _iChild >= self.m_Count:
				return self.m_ValueObject.GetChildAtIndex(_iChild - self.m_Count)
			if self.m_bValid:
				try:
					return self.fp_GetChildAtIndex(_iChild)
				except Exception as error:
					print '(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
					return None
			return None
		except Exception as error:
			print '(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return None

	def fp_GetChildAtIndex(self, _iChild):
		return None
	
	def fp_NumChildren(self):
		return 0


class CSynthProvider_Container(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_nElements = None
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			if self.m_nElements == None:
				return None;
			return self.m_ValueObject.CreateValueFromExpression("[Length]", str(self.m_nElements))
		return self.fp_ContainerGetChildAtIndex(_iChild - 1);

	def fp_ContainerChildAtIndex(self, _iChild):
		return 0;

	def fp_GetChildIndex(self, _Name):
		iChild = self.fp_ContainerGetChildIndex(_Name)
		if iChild >= 0:
			return iChild
		if _Name == '[Length]':
			return 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name) + 1

	def fp_ContainerGetChildIndex(self, _Name):
		return -1

	def fp_NumChildren(self):
		global g_MaxSynthChildren
		self.m_nElements = self.fp_ContainerNumChildren()
		Ret = self.m_nElements
		if Ret > g_MaxSynthChildren:
			Ret = g_MaxSynthChildren;
		return Ret + 1

	def fp_ContainerNumChildren(self):
		return 0


def fg_MibLLDBInit_Common(_Debugger):
	return