// $Id: KeyboardSettings.cc 7234 2007-11-04 20:52:41Z awulms $

#include "KeyboardSettings.hh"
#include "Setting.hh"
#include "EnumSetting.hh"
#include "FilenameSetting.hh"
#include "BooleanSetting.hh"
#include "MSXCommandController.hh"

namespace openmsx {

KeyboardSettings::KeyboardSettings(MSXCommandController& msxCommandController)
	: keymapFile(new FilenameSetting(msxCommandController,
		"kbd_keymap_filename",
		"File with mapping from Host key codes to MSX key codes",
		""))
	, alwaysEnableKeypad(new BooleanSetting(msxCommandController,
		"kbd_numkeypad_always_enabled",
		"Numeric keypad is always enabled, even on an MSX that does not have one",
		false))
	, traceKeyPresses(new BooleanSetting(msxCommandController,
		"kbd_trace_key_presses",
		"Trace key presses (show SDL key code, SDL modifiers and Unicode code-point value)",
		false, Setting::DONT_SAVE))
	, autoToggleCodeKanaLock(new BooleanSetting(msxCommandController,
		"kbd_auto_toggle_code_kana_lock",
		"Automatically toggle the CODE/KANA lock, based on the characters entered on the host keyboard",
		true))
{
	EnumSetting<Keys::KeyCode>::Map allowedKeys;
	allowedKeys["RALT"]        = Keys::K_RALT;
	allowedKeys["MENU"]        = Keys::K_MENU;
	allowedKeys["HENKAN_MODE"] = Keys::K_HENKAN_MODE;
	allowedKeys["RSHIFT"]      = Keys::K_RSHIFT;
	allowedKeys["RMETA"]       = Keys::K_RMETA;
	allowedKeys["LMETA"]       = Keys::K_LMETA;
	allowedKeys["LSUPER"]      = Keys::K_LSUPER;
	allowedKeys["RSUPER"]      = Keys::K_RSUPER;
	allowedKeys["HELP"]        = Keys::K_HELP;
	allowedKeys["UNDO"]        = Keys::K_UNDO;
	codeKanaHostKey.reset(new EnumSetting<Keys::KeyCode>(
		msxCommandController, "kbd_code_kana_host_key",
		"Host key that maps to the MSX CODE/KANA key. Please note that the HENKAN_MODE key only exists on Japanese host keyboards)",
		Keys::K_RALT, allowedKeys));

	EnumSetting<KpEnterMode>::Map kpEnterModeMap;
	kpEnterModeMap["KEYPAD_COMMA"] = MSX_KP_COMMA;
	kpEnterModeMap["ENTER"] = MSX_ENTER;
	kpEnterMode.reset(new EnumSetting<KpEnterMode>(
		msxCommandController, "kbd_numkeypad_enter_key",
		"MSX key that the enter key on the host numeric keypad must map to",
		MSX_KP_COMMA, kpEnterModeMap));

	EnumSetting<MappingMode>::Map mappingModeMap;
	mappingModeMap["KEY"] = KEY_MAPPING;
	mappingModeMap["CHARACTER"] = CHARACTER_MAPPING;
	mappingMode.reset(new EnumSetting<MappingMode>(
		msxCommandController, "kbd_mapping_mode",
		"Keyboard mapping mode",
		CHARACTER_MAPPING, mappingModeMap));
}

KeyboardSettings::~KeyboardSettings()
{
}

EnumSetting<Keys::KeyCode>& KeyboardSettings::getCodeKanaHostKey()
{
	return *codeKanaHostKey;
}

EnumSetting<KeyboardSettings::KpEnterMode>& KeyboardSettings::getKpEnterMode()
{
	return *kpEnterMode;
}

EnumSetting<KeyboardSettings::MappingMode>& KeyboardSettings::getMappingMode()
{
	return *mappingMode;
}

FilenameSetting& KeyboardSettings::getKeymapFile()
{
	return *keymapFile;
}

BooleanSetting& KeyboardSettings::getAlwaysEnableKeypad()
{
	return *alwaysEnableKeypad;
}

BooleanSetting& KeyboardSettings::getTraceKeyPresses()
{
	return *traceKeyPresses;
}

BooleanSetting& KeyboardSettings::getAutoToggleCodeKanaLock()
{
	return *autoToggleCodeKanaLock;
}

} // namespace openmsx
