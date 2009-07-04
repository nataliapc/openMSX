// $Id$

#ifndef MSXMOTHERBOARD_HH
#define MSXMOTHERBOARD_HH

#include "EmuTime.hh"
#include "openmsx.hh"
#include "noncopyable.hh"
#include <memory>
#include <string>

namespace openmsx {

class Reactor;
class MSXDevice;
class HardwareConfig;
class CliComm;
class MSXCommandController;
class Scheduler;
class CartridgeSlotManager;
class EventDistributor;
class MSXEventDistributor;
class EventDelay;
class RealTime;
class Debugger;
class MSXMixer;
class PluggingController;
class DummyDevice;
class MSXCPU;
class MSXCPUInterface;
class PanasonicMemory;
class MSXDeviceSwitch;
class CassettePortInterface;
class RenShaTurbo;
class LedStatus;
class Display;
class DiskManipulator;
class FilePool;
class GlobalSettings;
class CommandController;
class InfoCommand;
class MSXMotherBoardImpl;
class MSXMapperIO;

class MSXMotherBoard : private noncopyable
{
public:
	explicit MSXMotherBoard(Reactor& reactor, FilePool& filePool);
	~MSXMotherBoard();

	const std::string& getMachineID();

	/**
	 * Run emulation.
	 * @return True if emulation steps were done,
	 *   false if emulation is suspended.
	 */
	bool execute();

	/** See CPU::exitCPULoopAsync(). */
	void exitCPULoopAsync();

	/**
	 * Pause MSX machine. Only CPU is paused, other devices continue
	 * running. Used by turbor hardware pause.
	 */
	void pause();
	void unpause();

	void powerUp();

	void activate(bool active);
	bool isActive() const;

	byte readIRQVector();

	const HardwareConfig* getMachineConfig() const;
	void setMachineConfig(HardwareConfig* machineConfig);
	bool isTurboR() const;

	void loadMachine(const std::string& machine);

	HardwareConfig* findExtension(const std::string& extensionName);
	std::string loadExtension(const std::string& extensionName);
	std::string insertExtension(const std::string& name,
	                            std::auto_ptr<HardwareConfig> extension);
	void removeExtension(const HardwareConfig& extension);

	// The following classes are unique per MSX machine
	CliComm& getMSXCliComm();
	CliComm* getMSXCliCommIfAvailable();
	MSXCommandController& getMSXCommandController();
	Scheduler& getScheduler();
	MSXEventDistributor& getMSXEventDistributor();
	CartridgeSlotManager& getSlotManager();
	EventDelay& getEventDelay();
	RealTime& getRealTime();
	Debugger& getDebugger();
	MSXMixer& getMSXMixer();
	PluggingController& getPluggingController();
	DummyDevice& getDummyDevice();
	MSXCPU& getCPU();
	MSXCPUInterface& getCPUInterface();
	PanasonicMemory& getPanasonicMemory();
	MSXDeviceSwitch& getDeviceSwitch();
	CassettePortInterface& getCassettePort();
	RenShaTurbo& getRenShaTurbo();
	LedStatus& getLedStatus();
	Reactor& getReactor();

	// These are only convenience methods, Reactor keeps these objects
	FilePool& getFilePool();
	GlobalSettings& getGlobalSettings();
	CliComm& getGlobalCliComm();

	// convenience methods
	CommandController& getCommandController();
	InfoCommand& getMachineInfoCommand();

	/** Convenience method:
	  * This is the same as getScheduler().getCurrentTime(). */
	EmuTime::param getCurrentTime();

	/**
	 * All MSXDevices should be registered by the MotherBoard.
	 */
	void addDevice(MSXDevice& device);
	void removeDevice(MSXDevice& device);

	/** Find a MSXDevice by name
	  * @param name The name of the device as returned by
	  *             MSXDevice::getName()
	  * @return A pointer to the device or NULL if the device could not
	  *         be found.
	  */
	MSXDevice* findDevice(const std::string& name);

	/** Some MSX device parts are shared between several MSX devices
	  * (e.g. all memory mappers share IO ports 0xFC-0xFF). But this
	  * sharing is limited to one MSX machine. This method offers the
	  * storage to implement per-machine reference counted objects.
	  * TODO This doesn't play nicely with savestates. For example memory
	  *      mappers don't use this mechanism anymore because of this.
	  *      Maybe this method can be removed when savestates are finished.
	  */
	struct SharedStuff {
		SharedStuff() : stuff(NULL), counter(0) {}
		void* stuff;
		unsigned counter;
	};
	SharedStuff& getSharedStuff(const std::string& name);

	/** All memory mappers in one MSX machine share the same four (logical)
	  * memory mapper registers. These two methods handle this sharing.
	  */
	MSXMapperIO* createMapperIO();
	void destroyMapperIO();

	/** Keep track of which 'usernames' are in use.
	 * For example to be able to use several fmpac extensions at once, each
	 * with its own SRAM file, we need to generate unique filenames. We
	 * also want to reuse existing filenames as much as possible.
	 * ATM the usernames always have the format 'untitled[N]'. In the future
	 * we might allow really user specified names.
	 */
	std::string getUserName(const std::string& hwName);
	void freeUserName(const std::string& hwName,
	                  const std::string& userName);

	template<typename Archive>
	void serialize(Archive& ar, unsigned version);

private:
	std::auto_ptr<MSXMotherBoardImpl> pimple;
	friend class MSXMotherBoardImpl;
};

} // namespace openmsx

#endif
