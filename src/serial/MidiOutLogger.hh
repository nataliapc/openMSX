// $Id$ 

#ifndef __MIDIOUTLOGGER_HH__
#define __MIDIOUTLOGGER_HH__

#include <fstream>
#include "MidiOutDevice.hh"

using std::ofstream;

class MidiOutLogger : public MidiOutDevice
{
	public:
		MidiOutLogger();
		virtual ~MidiOutLogger();

		// Pluggable
		virtual void plug(Connector* connector, const EmuTime& time);
		virtual void unplug(const EmuTime& time);
		virtual const string &getName() const;

		// SerialDataInterface (part)
		virtual void recvByte(byte value, const EmuTime& time);
	
	private:
		ofstream file;
};

#endif

