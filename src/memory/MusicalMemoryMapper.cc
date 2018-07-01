#include "MusicalMemoryMapper.hh"
#include "SN76489.hh"
#include "serialize.hh"

namespace openmsx {

static const byte MEM_ACCESS_ENABLED = 1 << 7;
static const byte SOUND_PORT_ENABLED = 1 << 6;
static const byte PORT_ACCESS_DISABLED = 1 << 5;
static const byte UNUSED = 1 << 4;
static const byte WRITE_PROTECT = 0x0F;

MusicalMemoryMapper::MusicalMemoryMapper(const DeviceConfig& config)
	: MSXMemoryMapper(config)
	, sn76489(make_unique<SN76489>(config))
	, controlReg(0x00)
{
}

MusicalMemoryMapper::~MusicalMemoryMapper() = default;

void MusicalMemoryMapper::reset(EmuTime::param time)
{
	controlReg = 0x00;

	// MMM inits the page registers to 3, 2, 1, 0 instead of zeroes, so we
	// don't call the superclass implementation.
	for (unsigned page = 0; page < 4; page++) {
		registers[page] = 3 - page;
	}

	// Note: The actual SN76489AN chip does not have a reset pin. I assume
	//       MMM either powers off the chip on reset or suppresses its audio
	//       output. We instead keep the chip in a silent state until it is
	//       activated.
	sn76489->reset(time);
}

byte MusicalMemoryMapper::readIO(word port, EmuTime::param time)
{
	if (controlReg & PORT_ACCESS_DISABLED) {
		return 0xFF;
	} else {
		return MSXMemoryMapper::readIO(port, time);
	}
}

byte MusicalMemoryMapper::peekIO(word port, EmuTime::param time) const
{
	if (controlReg & PORT_ACCESS_DISABLED) {
		return 0xFF;
	} else {
		return MSXMemoryMapper::peekIO(port, time);
	}
}

void MusicalMemoryMapper::writeIO(word port, byte value, EmuTime::param time)
{
	if ((port & 0xFC) == 0xFC) {
		// Mapper port.
		if (!(controlReg & PORT_ACCESS_DISABLED)) {
			MSXMemoryMapper::writeIO(port, value, time);
		}
	} else if (port & 1) {
		// Sound chip.
		if (controlReg & SOUND_PORT_ENABLED) {
			sn76489->write(value, time);
		}
	} else {
		// Control port.
		// Only bit 7 of the control register is accessible through this port.
		// The documentation explicitly states that the sound chip port is still
		// accessible when port access is disabled, but this control port must
		// also remain accessible or the ROM2MMM loader won't work.
		updateControlReg((value & MEM_ACCESS_ENABLED) |
		                 (controlReg & ~MEM_ACCESS_ENABLED));
	}
}

bool MusicalMemoryMapper::registerAccessAt(word address) const
{
	if (controlReg & MEM_ACCESS_ENABLED) {
		if (controlReg & PORT_ACCESS_DISABLED) {
			// Note: I'm assuming the mirroring is still active when the
			//       address range is restricted, but this is unclear in
			//       the documentation and not tested on real hardware.
			if (controlReg & 0x08) {
				return 0x4000 <= address && address < 0x8000;
			} else {
				return 0x8000 <= address && address < 0xC000;
			}
		} else {
			return 0x4000 <= address && address < 0xC000;
		}
	} else {
		return false;
	}
}

int MusicalMemoryMapper::readReg(word address) const
{
	if (registerAccessAt(address)) {
		switch (address & 0xFF) {
		case 0x3C:
			return controlReg;
		case 0xFC:
		case 0xFD:
		case 0xFE:
		case 0xFF:
			return 0xC0 | getSelectedSegment(address & 0x03);
		}
	}
	return -1;
}

void MusicalMemoryMapper::updateControlReg(byte value)
{
	// Note: Bit 4 is unused, but I don't know its value when read.
	//       For now, I'll force it to 0.
	value &= ~UNUSED;

	byte change = value ^ controlReg;
	if (change) {
		// Pages for which write protect is toggled must be invalidated.
		byte invalidate = change & WRITE_PROTECT;

		// Invalidate pages for which register access changes.
		byte regAccessBefore = 0;
		for (unsigned page = 0; page < 4; page++) {
			regAccessBefore |= registerAccessAt(0x4000 * page) << page;
		}
		controlReg = value;
		byte regAccessAfter = 0;
		for (unsigned page = 0; page < 4; page++) {
			regAccessAfter |= registerAccessAt(0x4000 * page) << page;
		}
		invalidate |= regAccessBefore ^ regAccessAfter;

		for (unsigned page = 0; page < 4; page++) {
			if ((invalidate >> page) & 1) {
				invalidateMemCache(0x4000 * page, 0x4000);
			}
		}
	}
}

byte MusicalMemoryMapper::peekMem(word address, EmuTime::param time) const
{
	int reg = readReg(address);
	return reg >= 0 ? reg : MSXMemoryMapper::peekMem(address, time);
}

byte MusicalMemoryMapper::readMem(word address, EmuTime::param time)
{
	int reg = readReg(address);
	return reg >= 0 ? reg : MSXMemoryMapper::readMem(address, time);
}

void MusicalMemoryMapper::writeMem(word address, byte value, EmuTime::param time)
{
	if (registerAccessAt(address)) {
		switch (address & 0xFF) {
		case 0x3C:
			// When port access is disabled, memory access is automatically
			// enabled, according to the manual.
			if (value & PORT_ACCESS_DISABLED) {
				value |= MEM_ACCESS_ENABLED;
			}
			updateControlReg(value);
			return;
		case 0xFC:
		case 0xFD:
		case 0xFE:
		case 0xFF:
			MSXMemoryMapper::writeIO(address & 0xFF, value, time);
			return;
		}
	}
	if (!writeProtected(address)) {
		MSXMemoryMapper::writeMem(address, value, time);
	}
}

const byte* MusicalMemoryMapper::getReadCacheLine(word start) const
{
	if (controlReg & MEM_ACCESS_ENABLED) {
		if (0x4000 <= start && start < 0xC000) {
			return nullptr;
		}
	}
	return MSXMemoryMapper::getReadCacheLine(start);
}

byte* MusicalMemoryMapper::getWriteCacheLine(word start) const
{
	if (controlReg & MEM_ACCESS_ENABLED) {
		if (0x4000 <= start && start < 0xC000) {
			return nullptr;
		}
	}
	if (writeProtected(start)) {
		return unmappedWrite;
	} else {
		return MSXMemoryMapper::getWriteCacheLine(start);
	}
}

template<typename Archive>
void MusicalMemoryMapper::serialize(Archive& ar, unsigned /*version*/)
{
	ar.template serializeBase<MSXMemoryMapper>(*this);
	ar.serialize("ctrl", controlReg);
	ar.serialize("sn76489", *sn76489);
}
INSTANTIATE_SERIALIZE_METHODS(MusicalMemoryMapper);
REGISTER_MSXDEVICE(MusicalMemoryMapper, "MusicalMemoryMapper");

} // namespace openmsx