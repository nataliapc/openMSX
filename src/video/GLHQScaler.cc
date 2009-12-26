// $Id$

#include "GLHQScaler.hh"
#include "GLUtil.hh"
#include "HQCommon.hh"
#include "FrameSource.hh"
#include "FileContext.hh"
#include "File.hh"
#include "StringOp.hh"
#include "openmsx.hh"
#include <cstring>

using std::string;

namespace openmsx {

// TODO apply this transformation on the data file, or even better
// generate the data algorithmically (including this transformation)
static void transform(const byte* in, byte* out, int n, int s)
{
	for (int z = 0; z < 4096; ++z) {
		int z1Offset = s * n * n * z;
		int z2Offset = s * (n * (z % 64) +
		                    n * n * 64 * (z / 64));
		for (int y = 0; y < n; ++y) {
			int y1Offset = s * n      * y;
			int y2Offset = s * n * 64 * y;
			for (int x = 0; x < n; ++x) {
				int offset1 = z1Offset + y1Offset + s * x;
				int offset2 = z2Offset + y2Offset + s * x;
				for (int t = 0; t < s; ++t) {
					out[offset2 + t] = in[offset1 + t];
				}
			}
		}
	}
}

GLHQScaler::GLHQScaler()
{
	for (int i = 0; i < 2; ++i) {
		string header = string("#define SUPERIMPOSE ")
		              + char('0' + i) + '\n';
		VertexShader   vertexShader  (header, "hq.vert");
		FragmentShader fragmentShader(header, "hq.frag");
		scalerProgram[i].reset(new ShaderProgram());
		scalerProgram[i]->attach(vertexShader);
		scalerProgram[i]->attach(fragmentShader);
		scalerProgram[i]->link();
#ifdef GL_VERSION_2_0
		if (GLEW_VERSION_2_0) {
			scalerProgram[i]->activate();
			glUniform1i(scalerProgram[i]->getUniformLocation("colorTex"),  0);
			if (i == 1) {
				glUniform1i(scalerProgram[i]->getUniformLocation("videoTex"),   1);
			}
			glUniform1i(scalerProgram[i]->getUniformLocation("edgeTex"),   2);
			glUniform1i(scalerProgram[i]->getUniformLocation("offsetTex"), 3);
			glUniform1i(scalerProgram[i]->getUniformLocation("weightTex"), 4);
			glUniform2f(scalerProgram[i]->getUniformLocation("texSize"),
				    320.0f, 2 * 240.0f);
		}
#endif
	}

	edgeTexture.reset(new Texture());
	edgeTexture->bind();
	edgeTexture->setWrapMode(false);
	glTexImage2D(GL_TEXTURE_2D,    // target
	             0,                // level
	             GL_LUMINANCE16,   // internal format
	             320,              // width
	             240,              // height
	             0,                // border
	             GL_LUMINANCE,     // format
	             GL_UNSIGNED_SHORT,// type
	             NULL);            // data
	edgeBuffer.reset(new PixelBuffer<unsigned short>());
	edgeBuffer->setImage(320, 240);

	SystemFileContext context;
	CommandController* controller = NULL; // ok for SystemFileContext
	glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
	byte buffer[4 * 4 * 4 * 4096];
	for (int i = 0; i < 3; ++i) {
		int n = i + 2;
		string offsetsName = StringOp::Builder() <<
			"shaders/HQ" << n << "xOffsets.dat";
		File offsetsFile(context.resolve(*controller, offsetsName));
		offsetTexture[i].reset(new Texture());
		offsetTexture[i]->setWrapMode(false);
		offsetTexture[i]->bind();
		transform(offsetsFile.mmap(), buffer, n, 4);
		glTexImage2D(GL_TEXTURE_2D,      // target
			     0,                  // level
			     GL_RGBA8,           // internal format
			     n * 64,             // width
			     n * 64,             // height
			     0,                  // border
			     GL_RGBA,            // format
			     GL_UNSIGNED_BYTE,   // type
			     buffer);            // data

		string weightsName = StringOp::Builder() <<
			"shaders/HQ" << n << "xWeights.dat";
		File weightsFile(context.resolve(*controller, weightsName));
		weightTexture[i].reset(new Texture());
		weightTexture[i]->setWrapMode(false);
		weightTexture[i]->bind();
		transform(weightsFile.mmap(), buffer, n, 3);
		glTexImage2D(GL_TEXTURE_2D,      // target
			     0,                  // level
			     GL_RGB8,            // internal format
			     n * 64,             // width
			     n * 64,             // height
			     0,                  // border
			     GL_RGB,             // format
			     GL_UNSIGNED_BYTE,   // type
			     buffer);            // data
	}
	glPixelStorei(GL_UNPACK_ALIGNMENT, 4); // restore to default
}

void GLHQScaler::scaleImage(
	ColorTexture& src, ColorTexture* superImpose,
	unsigned srcStartY, unsigned srcEndY, unsigned srcWidth,
	unsigned dstStartY, unsigned dstEndY, unsigned dstWidth,
	unsigned logSrcHeight)
{
	unsigned factorX = dstWidth / srcWidth; // 1 - 4
	unsigned factorY = (dstEndY - dstStartY) / (srcEndY - srcStartY);

	ShaderProgram& prog = *scalerProgram[superImpose ? 1 : 0];
	if ((srcWidth == 320) && (factorX > 1) && (factorX == factorY)) {
		assert(src.getHeight() == 2 * 240);
		glActiveTexture(GL_TEXTURE4);
		weightTexture[factorX - 2]->bind();
		glActiveTexture(GL_TEXTURE3);
		offsetTexture[factorX - 2]->bind();
		glActiveTexture(GL_TEXTURE2);
		edgeTexture->bind();
		if (superImpose) {
			glActiveTexture(GL_TEXTURE1);
			superImpose->bind();
		}
		glActiveTexture(GL_TEXTURE0);
		prog.activate();
	} else {
		prog.deactivate();
	}

	drawMultiTex(src, srcStartY, srcEndY, src.getHeight(), logSrcHeight,
	             dstStartY, dstEndY, dstWidth);
}

typedef unsigned Pixel;
void GLHQScaler::uploadBlock(
	unsigned srcStartY, unsigned srcEndY, unsigned lineWidth,
	FrameSource& paintFrame)
{
	if (lineWidth != 320) return;

	unsigned tmpBuf2[320 / 2];
	#ifndef NDEBUG
	// Avoid UMR. In optimized mode we don't care.
	memset(tmpBuf2, 0, (320 / 2) * sizeof(unsigned));
	#endif

	const Pixel* curr = paintFrame.getLinePtr<Pixel>(srcStartY - 1, lineWidth);
	const Pixel* next = paintFrame.getLinePtr<Pixel>(srcStartY + 0, lineWidth);
	calcEdgesGL(curr, next, tmpBuf2, EdgeHQ());

	edgeBuffer->bind();
	unsigned short* mapped = edgeBuffer->mapWrite();
	if (mapped) {
		for (unsigned y = srcStartY; y < srcEndY; ++y) {
			curr = next;
			next = paintFrame.getLinePtr<Pixel>(y + 1, lineWidth);
			calcEdgesGL(curr, next, tmpBuf2, EdgeHQ());
			memcpy(mapped + 320 * y, tmpBuf2, 320 * sizeof(unsigned short));
		}
		edgeBuffer->unmap();

		edgeTexture->bind();
		glTexSubImage2D(GL_TEXTURE_2D,       // target
		                0,                   // level
		                0,                   // offset x
		                srcStartY,           // offset y
		                lineWidth,           // width
		                srcEndY - srcStartY, // height
		                GL_LUMINANCE,        // format
		                GL_UNSIGNED_SHORT,   // type
		                edgeBuffer->getOffset(0, srcStartY)); // data
	}
	edgeBuffer->unbind();
}

} // namespace openmsx
