#include "RawTrack.hh"
#include "CRC16.hh"
#include "serialize.hh"
#include "serialize_stl.hh"
#include <algorithm>
#include <cassert>

using std::vector;

namespace openmsx {

#ifndef _MSC_VER
// Workaround vc++ bug???
//  I'm reasonably sure the following line is required. If it's left out I get
//  a link error when compiling with gcc (though only in a debug build). This
//  page also says it's required:
//    http://www.parashift.com/c++-faq-lite/ctors.html#faq-10.13
//  Though with this line Vampier got a link error in vc++, removing the line
//  fixed the problem.
const unsigned RawTrack::STANDARD_SIZE;
#endif

RawTrack::RawTrack(unsigned size)
{
	clear(size);
}

void RawTrack::clear(unsigned size)
{
	idam.clear();
	data.assign(size, 0x4e);
}

void RawTrack::addIdam(unsigned idx)
{
	assert(idx < data.size());
	assert(idam.empty() || (idx > idam.back()));
	idam.push_back(idx);
}

void RawTrack::write(int idx, byte val, bool setIdam)
{
	unsigned i2 = wrapIndex(idx);
	auto it = lower_bound(begin(idam), end(idam), i2);
	if (setIdam) {
		// add idam (if not already present)
		if ((it == end(idam)) || (*it != i2)) {
			idam.insert(it, i2);
		}
	} else {
		// remove idam (if present)
		if ((it != end(idam)) && (*it == i2)) {
			idam.erase(it);
		}
	}
	data[i2] = val;
}

bool RawTrack::decodeSectorImpl(int idx, Sector& sector) const
{
	// read (and check) address mark
	// assume addr mark starts with three A1 bytes (should be
	// located right before the current 'idx' position)
	if (read(idx) != 0xFE) return false; // 'sector'-data not filled in

	++idx;
	sector.addrIdx = idx;
	CRC16 addrCrc;
	addrCrc.init<0xA1, 0xA1, 0xA1, 0xFE>();
	updateCrc(addrCrc, sector.addrIdx, 4);
	sector.track    = read(idx++);
	sector.head     = read(idx++);
	sector.sector   = read(idx++);
	sector.sizeCode = read(idx++);
	byte addrCrc1 = read(idx++);
	byte addrCrc2 = read(idx++);
	sector.addrCrcErr = (256 * addrCrc1 + addrCrc2) != addrCrc.getValue();

	sector.dataIdx = -1; // (for now) no data block found
	sector.deleted = false;   // dummy
	sector.dataCrcErr = true; // dummy

	if (!sector.addrCrcErr) {
		// Locate data mark, should starts within 43 bytes from current
		// position (that's what the WD2793 does).
		for (int i = 0; i < 43; ++i) {
			int idx2 = idx + i;
			int j = 0;
			for (; j < 3; ++j) {
				if (read(idx2 + j) != 0xA1) break;
			}
			if (j != 3) continue; // didn't find 3 x 0xA1

			byte type = read(idx2 + 3);
			if (!((type == 0xfb) || (type == 0xf8))) continue;

			CRC16 dataCrc;
			dataCrc.init<0xA1, 0xA1, 0xA1>();
			dataCrc.update(type);

			// OK, found start of data, calculate CRC.
			int dataIdx = idx2 + 4;
			unsigned sectorSize = 128 << (sector.sizeCode & 7);
			updateCrc(dataCrc, dataIdx, sectorSize);
			byte dataCrc1 = read(dataIdx + sectorSize + 0);
			byte dataCrc2 = read(dataIdx + sectorSize + 1);
			bool dataCrcErr = (256 * dataCrc1 + dataCrc2) != dataCrc.getValue();

			// store result
			sector.dataIdx    = dataIdx;
			sector.deleted    = type == 0xf8;
			sector.dataCrcErr = dataCrcErr;
			break;
		}
	}
	return true;
}

vector<RawTrack::Sector> RawTrack::decodeAll() const
{
	// only complete sectors (header + data block)
	vector<Sector> result;
	for (auto& i : idam) {
		Sector sector;
		if (decodeSectorImpl(i, sector) &&
		    (sector.dataIdx != -1)) {
			result.push_back(sector);
		}
	}
	return result;
}

static vector<unsigned> rotateIdam(vector<unsigned> idam, unsigned startIdx)
{
	// find first element that is equal or bigger
	auto it = lower_bound(begin(idam), end(idam), startIdx);
	// rotate range so that we start at that element
	rotate(begin(idam), it, end(idam));
	return idam;
}

bool RawTrack::decodeNextSector(unsigned startIdx, Sector& sector) const
{
	// get first valid sector-header
	for (auto& i : rotateIdam(idam, startIdx)) {
		if (decodeSectorImpl(i, sector)) {
			return true;
		}
	}
	return false;
}

bool RawTrack::decodeSector(byte sectorNum, Sector& sector) const
{
	// only complete sectors (header + data block)
	for (auto& i : idam) {
		if (decodeSectorImpl(i, sector) &&
		    (sector.sector == sectorNum) &&
		    (sector.dataIdx != -1)) {
			return true;
		}
	}
	return false;
}

void RawTrack::readBlock(int idx, unsigned size, byte* destination) const
{
	for (unsigned i = 0; i < size; ++i) {
		destination[i] = read(idx + i);
	}
}
void RawTrack::writeBlock(int idx, unsigned size, const byte* source)
{
	for (unsigned i = 0; i < size; ++i) {
		write(idx + i, source[i]);
	}
}

void RawTrack::updateCrc(CRC16& crc, int idx, int size) const
{
	unsigned start = wrapIndex(idx);
	unsigned end = start + size;
	if (end <= data.size()) {
		crc.update(&data[start], size);
	} else {
		unsigned part = unsigned(data.size()) - start;
		crc.update(&data[start], part);
		crc.update(&data[    0], size - part);
	}
}

word RawTrack::calcCrc(int idx, int size) const
{
	CRC16 crc;
	updateCrc(crc, idx, size);
	return crc.getValue();
}

void RawTrack::applyWd2793ReadTrackQuirk()
{
	// Tests on a real WD2793 have shown that the first 'A1' byte in a
	// sequence of 3 'special' A1 bytes gets systematically read as a
	// different value by the read-track command.
	//
	// Very roughly in my tests I got:
	//  - about 1/2 of the times the value 0x14 is returned
	//  - about 1/3 of the times the value 0xC2 is returned
	//  - about 1/6 of the times a different value is returned (I've seen
	//    00, 02, F8, FC)
	// When re-reading the same track again, the values 14 and C2 remain,
	// but often the values 00 or 02 change to 14, and F8 or FC change to
	// C2. I've never seen the 'real' value 'A1'. Note again that this
	// transformation only applies to the 1st of the three A1 bytes, the
	// 2nd and 3rd are correctly read as A1.
	//
	// I've no good explanation for why this is happening, except for the
	// following observation which might be the start of a partial
	// explanation, or it might just be a coincidence:
	//
	// The 'special' value A1 is encoded as: 0x4489, or in binary
	//     01 00 01 00 10 00 10 01
	// If you only look at the even bits (the data bits) you get the value
	// A1 back. The odd bits (the clock bits) are generated by the MFM
	// encoding rules and ensure that there are never 2 consecutive 1-bits
	// and never more than 3 consecutive 0-bits. Though this is a 'special'
	// sequence and the clock bit of the 6th bit (counting from left to
	// right starting at 1) is 0, it should be 1 according to the MFM
	// rules. The normal encoding for A1 is 0x44A9. An FDC uses this
	// special bit-pattern to synchronize the bitstream on, e.g. to know
	// where the byte-boundaries are located in the stream.
	//
	// Now if you shift the pattern 0x4489 1 bit to the left, you get
	// 0x8912. If you then decode the data bits you get the value 0x14. And
	// this _might_ be a partial explanation for why read-track often
	// returns 0x14 instead of 0xA1.
	//
	// The implementation below always changes the first 0xA1 byte to 0x14.
	// It does not also return the value 0xC2, because I've no clue yet
	// when which value should be returned.
	//
	// The motivation for this (crude) implementation is the following:
	// There's a cracked disk version of Nemesis that comes with a
	// copy-protection. The disk has a track which contains sector-headers
	// with CRC errors. The software verifies the protection via the
	// read-track command. In the resulting data block it scans for the
	// first A1 byte and then sums the next 8 bytes. Initially openMSX
	// returned A1 'too early', and then the sum of the 8 following bytes
	// doesn't match. But if the first A1 is turned into something
	// (anything) else, so the sum starts one byte later, it does work
	// fine.

	for (int i : idam) {
		if ((read(i - 3) != 0xA1) ||
		    (read(i - 2) != 0xA1) ||
		    (read(i - 1) != 0xA1) ||
		    (read(i - 0) != 0xFE)) continue;
		write(i - 3, 0x14);

		Sector sector;
		if (decodeSectorImpl(i, sector) &&
		    (sector.dataIdx != -1)) {
			int d = sector.dataIdx;
			if ((read(d - 4) != 0xA1) ||
			    (read(d - 3) != 0xA1) ||
			    (read(d - 2) != 0xA1)) continue;
			write(d - 4, 0x14);
		}
	}
}

// version 1: initial version (fixed track length of 6250)
// version 2: variable track length
template<typename Archive>
void RawTrack::serialize(Archive& ar, unsigned version)
{
	ar.serialize("idam", idam);
	auto len = unsigned(data.size());
	if (ar.versionAtLeast(version, 2)) {
		ar.serialize("trackLength", len);
	} else {
		assert(ar.isLoader());
		len = 6250;
	}
	if (ar.isLoader()) {
		data.resize(len);
	}
	ar.serialize_blob("data", data.data(), data.size());
}
INSTANTIATE_SERIALIZE_METHODS(RawTrack);

template<typename Archive>
void RawTrack::Sector::serialize(Archive& ar, unsigned /*version*/)
{
	ar.serialize("addrIdx", addrIdx);
	ar.serialize("dataIdx", dataIdx);
	ar.serialize("track", track);
	ar.serialize("head", head);
	ar.serialize("sector", sector);
	ar.serialize("sizeCode", sizeCode);
	ar.serialize("deleted", deleted);
	ar.serialize("addrCrcErr", addrCrcErr);
	ar.serialize("dataCrcErr", dataCrcErr);
}
INSTANTIATE_SERIALIZE_METHODS(RawTrack::Sector);

} // namespace openmsx
