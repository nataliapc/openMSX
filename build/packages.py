# $Id$

from urlparse import urljoin

class Package(object):
	'''Abstract base class for packages.
	'''
	downloadURL = None
	name = None
	version = None
	dependsOn = ()

	@classmethod
	def getTarballName(cls):
		return '%s-%s.tar.gz' % (cls.name, cls.version)

	@classmethod
	def getURL(cls):
		return urljoin(cls.downloadURL + '/', cls.getTarballName())

class DirectX(Package):
	downloadURL = 'http://alleg.sourceforge.net/files'
	name = 'dx'
	version = '70'

	@classmethod
	def getTarballName(cls):
		return '%s%s_mgw.tar.gz' % (cls.name, cls.version)

class FreeType(Package):
	downloadURL = 'http://nongnu.askapache.com/freetype'
	name = 'freetype'
	version = '2.3.7'
	dependsOn = ('zlib', )

class GLEW(Package):
	downloadURL = 'http://downloads.sourceforge.net/glew'
	name = 'glew'
	version = '1.5.1'

	@classmethod
	def getTarballName(cls):
		return '%s-%s-src.tgz' % (cls.name, cls.version)

class LibPNG(Package):
	downloadURL = 'http://downloads.sourceforge.net/libpng'
	name = 'libpng'
	version = '1.2.34'
	dependsOn = ('zlib', )

class LibXML2(Package):
	downloadURL = 'http://xmlsoft.org/sources'
	name = 'libxml2'
	version = '2.7.2'
	dependsOn = ('zlib', )

class SDL(Package):
	downloadURL = 'http://www.libsdl.org/release'
	name = 'SDL'
	version = '1.2.13'

class SDL_image(Package):
	downloadURL = 'http://www.libsdl.org/projects/SDL_image/release'
	name = 'SDL_image'
	version = '1.2.7'
	dependsOn = ('SDL', 'libpng')

class SDL_ttf(Package):
	downloadURL = 'http://www.libsdl.org/projects/SDL_ttf/release'
	name = 'SDL_ttf'
	version = '2.0.9'
	dependsOn = ('SDL', 'freetype')

class TCL(Package):
	downloadURL = 'http://downloads.sourceforge.net/tcl'
	name = 'tcl'
	version = '8.5.6'

	@classmethod
	def getTarballName(cls):
		return '%s%s-src.tar.gz' % (cls.name, cls.version)

class ZLib(Package):
	downloadURL = 'http://downloads.sourceforge.net/libpng'
	name = 'zlib'
	version = '1.2.3'
