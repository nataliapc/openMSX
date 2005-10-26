// $Id$

#ifndef RGBTRIPLET3XSCALER_HH
#define RGBTRIPLET3XSCALER_HH

#include "Scaler3.hh"
#include "Scanline.hh"

namespace openmsx {

class RenderSettings;

/** TODO
  */
template <class Pixel>
class RGBTriplet3xScaler : public Scaler3<Pixel>
{
public:
	RGBTriplet3xScaler(SDL_PixelFormat* format,
	                   const RenderSettings& renderSettings);

	virtual void scaleBlank(
		Pixel color, SDL_Surface* dst,
		unsigned startY, unsigned endY);
	virtual void scale256(
		FrameSource& src, unsigned srcStartY, unsigned srcEndY,
		SDL_Surface* dst, unsigned dstStartY, unsigned dstEndY);
	virtual void scale512(
		FrameSource& src, unsigned srcStartY, unsigned srcEndY,
		SDL_Surface* dst, unsigned dstStartY, unsigned dstEndY);
	// TODO implement other methods:
	//   scale to 320 wide local buffer and RGBify that

private:
	inline void calcSpil(unsigned x, unsigned& r, unsigned& s);
	/**
	 * Calculates the RGB triplets.
	 * @param in Buffer of input pixels
	 * @param out Buffer of output pixels, should be 3x as long as input
	 * @param inwidth Width of the input buffer (in pixels)
	 */
	void rgbify(const Pixel* in, Pixel* out, unsigned inwidth);

	int c1, c2;
	Scanline<Pixel> scanline;
	const RenderSettings& settings;
};

} // namespace openmsx

#endif
